# Copyright 2004-2006 Canonical Ltd. All rights reserved.

__all__ = [
    'validate_url',
    'valid_http_url',
    'valid_ftp_url',
    'valid_rsync_url',
    'valid_webref',
    'non_duplicate_bug',
    'non_duplicate_branch',
    'valid_bug_number',
    'valid_cve_sequence',
    'valid_emblem',
    'valid_hackergotchi',
    'valid_unregistered_email',
    'validate_distribution_mirror_schema',
    'valid_distributionmirror_file_list',
    'valid_distrotask',
    'valid_upstreamtask'
    ]

import urllib
from textwrap import dedent
from StringIO import StringIO

from zope.component import getUtility
from zope.exceptions import NotFoundError
from zope.app.content_types import guess_content_type
from zope.app.form.interfaces import WidgetsError

from canonical.launchpad import _
from canonical.launchpad.searchbuilder import NULL
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.interfaces.bugtask import BugTaskSearchParams
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.validators.cve import valid_cve
from canonical.launchpad.validators.url import valid_absolute_url
from canonical.lp.dbschema import MirrorPulseType

#XXX matsubara 2006-03-15: The validations functions that deals with URLs
# should be in validators/ and we should have them as separete constraints in
# trusted.sql.  
# https://launchpad.net/products/launchpad/+bug/35077
def validate_url(url, valid_schemes):
    """Returns a boolean stating whether 'url' is a valid URL.

       A URL is valid if:
           - its URL scheme is in the provided 'valid_schemes' list, and
           - it has a non-empty host name.

       None and an empty string are not valid URLs::

           >>> validate_url(None, [])
           False
           >>> validate_url('', [])
           False

       The valid_schemes list is checked::

           >>> validate_url('http://example.com', ['http'])
           True
           >>> validate_url('http://example.com', ['https', 'ftp'])
           False

       A URL without a host name is not valid:

           >>> validate_url('http://', ['http'])
           False

      """
    if not url:
        return False
    scheme, host = urllib.splittype(url)
    if not scheme in valid_schemes:
        return False
    if not valid_absolute_url(url):
        return False
    return True


def valid_webref(web_ref):
    """Returns True if web_ref is not a valid download URL, or raises a
    LaunchpadValidationError.

    >>> valid_webref('http://example.com')
    True
    >>> valid_webref('https://example.com/foo/bar')
    True
    >>> valid_webref('ftp://example.com/~ming')
    True
    >>> valid_webref('sftp://example.com//absolute/path/maybe')
    True
    >>> valid_webref('other://example.com/moo')
    Traceback (most recent call last):
    ...
    LaunchpadValidationError: ...
    """
    if validate_url(web_ref, ['http', 'https', 'ftp', 'sftp']):
        # Allow ftp so valid_webref can be used for download_url, and so
        # it doesn't lock out weird projects where the site or
        # screenshots are kept on ftp.
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid URL. Please enter the full URL, including the
            scheme (for instance, http:// for a web URL), and ensure the
            URL uses either http, https or ftp.""")))

def valid_ftp_url(url):
    if validate_url(url, ['ftp']):
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid FTP URL. Please enter the full URL, including the
            ftp:// part.""")))

def valid_rsync_url(url):
    if validate_url(url, ['rsync']):
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid Rsync URL. Please enter the full URL, including the
            rsync:// part.""")))

def valid_http_url(url):
    if validate_url(url, ['http']):
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid HTTP URL. Please enter the full URL, including the
            http:// part.""")))

def non_duplicate_bug(value):
    """Prevent dups of dups.

    Returns True if the dup target is not a duplicate /and/ if the
    current bug doesn't have any duplicates referencing it /and/ if the
    bug isn't a duplicate of itself, otherwise
    return False.
    """

    from canonical.launchpad.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    current_bug = getUtility(ILaunchBag).bug
    dup_target = value
    current_bug_has_dup_refs = bool(bugset.searchAsUser(
        user=getUtility(ILaunchBag).user,
        duplicateof=current_bug))
    if current_bug == dup_target:
        raise LaunchpadValidationError(_(dedent("""
            You can't mark a bug as a duplicate of itself.""")))
    elif dup_target.duplicateof is not None:
        raise LaunchpadValidationError(_(dedent("""
            Bug %i is already a duplicate of bug %i. You can only
            duplicate to bugs that are not duplicates themselves.
            """% (dup_target.id, dup_target.duplicateof.id))))
    elif current_bug_has_dup_refs: 
        raise LaunchpadValidationError(_(dedent("""
            There are other bugs already marked as duplicates of Bug %i.
            These bugs should be changed to be duplicates of another bug
            if you are certain you would like to perform this change."""
            % current_bug.id))) 
    else:
        return True


def non_duplicate_branch(value):
    """Ensure that this branch hasn't already been linked to this bug."""
    current_bug = getUtility(ILaunchBag).bug
    if current_bug.hasBranch(value):
        raise LaunchpadValidationError(_(dedent("""
            This branch is already registered on this bug.
            """)))

    return True


def valid_bug_number(value):
    from canonical.launchpad.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    try:
        bugset.get(value)
    except NotFoundError:
        raise LaunchpadValidationError(_(
            "Bug %i doesn't exist." % value))
    return True


def valid_cve_sequence(value):
    """Check if the given value is a valid CVE otherwise raise an exception."""
    if valid_cve(value):
        return True
    else:
        raise LaunchpadValidationError(_(
            "%s is not a valid CVE number" % value))


def _valid_image(image, max_size, max_dimensions):
    """Check that the given image is under the given constraints.

    :length: is the maximum size of the image, in bytes.
    :dimensions: is a tuple of the form (width, height).
    """
    # No global import to avoid hard dependency on PIL being installed
    import PIL.Image
    if len(image) > max_size:
        raise LaunchpadValidationError(_(dedent("""
            This file exceeds the maximum allowed size in bytes.""")))
    try:
        image = PIL.Image.open(StringIO(image))
    except IOError:
        # cannot identify image type
        raise LaunchpadValidationError(_(dedent("""
            The file uploaded was not recognized as an image; please
            check the file and retry.""")))
    if image.size > max_dimensions:
        raise LaunchpadValidationError(_(dedent("""
            This image exceeds the maximum allowed width or height in
            pixels.""")))
    return True

def valid_emblem(emblem):
    return _valid_image(emblem, 9000, (16,16))

def valid_hackergotchi(hackergotchi):
    return _valid_image(hackergotchi, 54000, (150,150))

# XXX: matsubara 2005-12-08 This validator shouldn't be used in an editform, 
# because editing an already registered e-mail would fail if this constraint
# is used.
def valid_unregistered_email(email):
    """Check that the given email is valid and that isn't registered to
    another user."""

    from canonical.launchpad.interfaces import IEmailAddressSet
    if valid_email(email):
        emailset = getUtility(IEmailAddressSet)
        if emailset.getByEmail(email) is not None:
            raise LaunchpadValidationError(_(dedent("""
                %s is already taken.""" % email)))
        else:
            return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            %s isn't a valid email address.""" % email)))

def valid_distributionmirror_file_list(file_list=None):
    if file_list is not None:
        content_type, dummy = guess_content_type(body=file_list)
        if content_type != 'text/plain':
            raise LaunchpadValidationError(
                "The given file is not in plain text format.")
    return True

def validate_distribution_mirror_schema(form_values):
    """Perform schema validation according to IDistributionMirror constraints.

    This validation will take place after the values of individual widgets
    are validated. It's necessary because we have some constraints where we
    need to take into account the value of multiple widgets.

    :form_values: A dictionary mapping IDistributionMirror attributes to the
                  values suplied by the user.
    """
    errors = []
    if (form_values['pulse_type'] == MirrorPulseType.PULL 
        and not form_values['pulse_source']):
        errors.append(LaunchpadValidationError(_(
            "You have choosen 'Pull' as the pulse type but have not "
            "supplied a pulse source.")))

    if not (form_values['http_base_url'] or form_values['ftp_base_url']
            or form_values['rsync_base_url']):
        errors.append(LaunchpadValidationError(_(
            "All mirrors require at least one URL (HTTP, FTP or "
            "Rsync) to be specified.")))

    if errors:
        raise WidgetsError(errors)


def valid_distrotask(bug, distribution, sourcepackagename=None):
    """Check if a distribution bugtask already exists for a given bug.
    
    If it exists, WidgetsError will be raised.
    """
    from canonical.launchpad.helpers import shortlist
    errors = []
    if sourcepackagename is not None:
        msg = LaunchpadValidationError(_(
            'A fix for this bug has already been requested for %s (%s)' %
            (sourcepackagename.name, distribution.displayname)))
    else:
        msg = LaunchpadValidationError(_(
            'A fix for this bug has already been requested for %s' % 
            distribution.displayname))
        sourcepackagename = NULL
    user = getUtility(ILaunchBag).user
    params = BugTaskSearchParams(
        user, bug=bug, sourcepackagename=sourcepackagename)
    bugtasks = shortlist(distribution.searchTasks(params), longest_expected=1)
    if bugtasks: 
        # We have to raise WidgetsError if a bugtask is found, the only case we
        # should skip it is when we're removing a sourcepackagename from a
        # existing bugtask
        assert len(bugtasks) == 1
        if bugtasks[0].sourcepackagename is not None and (
            sourcepackagename is None):
            return
        errors.append(msg)
            
    if errors:
        raise WidgetsError(errors)


def valid_upstreamtask(bug, product):
    """Check if a product bugtask already exists for a given bug.

    If it exists, WidgetsError will be raised.
    """
    errors = []
    user = getUtility(ILaunchBag).user
    params = BugTaskSearchParams(user, bug=bug)
    if product.searchTasks(params):
        errors.append(LaunchpadValidationError(_(
            'A fix for this bug has already been requested for %s' % 
            product.displayname)))

    if errors:
        raise WidgetsError(errors)


# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213

__metaclass__ = type

__all__ = [
    'can_be_nominated_for_series',
    'validate_url',
    'valid_webref',
    'valid_branch_url',
    'non_duplicate_branch',
    'valid_bug_number',
    'valid_cve_sequence',
    'validate_new_team_email',
    'validate_new_person_email',
    'validate_distrotask',
    'validate_new_distrotask',
    'valid_upstreamtask',
    'valid_password',
    'validate_date_interval',
    ]

from cgi import escape
from textwrap import dedent
import urllib

from zope.app.form.interfaces import WidgetsError
from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.interfaces.account import IAccount
from canonical.launchpad.interfaces.emailaddress import (
    IEmailAddress,
    IEmailAddressSet,
    )
from lp.services.validators import LaunchpadValidationError
from lp.services.validators.cve import valid_cve
from lp.services.validators.email import valid_email
from lp.services.validators.url import valid_absolute_url
from canonical.launchpad.webapp import canonical_url
from canonical.launchpad.webapp.menu import structured
from lp.app.errors import NotFoundError


def can_be_nominated_for_series(series):
    """Can the bug be nominated for these series?"""
    current_bug = getUtility(ILaunchBag).bug
    unnominatable_series = []
    for s in series:
        if not current_bug.canBeNominatedFor(s):
            unnominatable_series.append(s.name.capitalize())

    if unnominatable_series:
        series_str = ", ".join(unnominatable_series)
        raise LaunchpadValidationError(_(
            "This bug has already been nominated for these "
            "series: ${series}", mapping={'series': series_str}))

    return True


# XXX matsubara 2006-03-15 bug=35077:
# The validations functions that deals with URLs should be in
# validators/ and we should have them as separete constraints in trusted.sql.
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
    """Returns True if web_ref is a valid download URL, or raises a
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


def valid_branch_url(branch_url):
    """Returns True if web_ref is a valid download URL, or raises a
    LaunchpadValidationError.

    >>> valid_branch_url('http://example.com')
    True
    >>> valid_branch_url('https://example.com/foo/bar')
    True
    >>> valid_branch_url('ftp://example.com/~ming')
    True
    >>> valid_branch_url('sftp://example.com//absolute/path/maybe')
    True
    >>> valid_branch_url('other://example.com/moo')
    Traceback (most recent call last):
    ...
    LaunchpadValidationError: ...
    """
    if validate_url(branch_url, ['http', 'https', 'ftp', 'sftp', 'bzr+ssh']):
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid URL. Please enter the full URL, including the
            scheme (for instance, http:// for a web URL), and ensure the
            URL uses http, https, ftp, sftp, or bzr+ssh.""")))


def non_duplicate_branch(value):
    """Ensure that this branch hasn't already been linked to this bug."""
    current_bug = getUtility(ILaunchBag).bug
    if current_bug.hasBranch(value):
        raise LaunchpadValidationError(_(dedent("""
            This branch is already registered on this bug.
            """)))

    return True


def valid_bug_number(value):
    from lp.bugs.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    try:
        bugset.get(value)
    except NotFoundError:
        raise LaunchpadValidationError(_(
            "Bug ${bugid} doesn't exist.", mapping={'bugid': value}))
    return True


def valid_cve_sequence(value):
    """Check if the given value is a valid CVE otherwise raise an exception.
    """
    if valid_cve(value):
        return True
    else:
        raise LaunchpadValidationError(_(
            "${cve} is not a valid CVE number", mapping={'cve': value}))


def _validate_email(email):
    if not valid_email(email):
        raise LaunchpadValidationError(_(
            "${email} isn't a valid email address.",
            mapping={'email': email}))

def _check_email_availability(email):
    email_address = getUtility(IEmailAddressSet).getByEmail(email)
    if email_address is not None:
        # The email already exists; determine what has it.
        if email_address.person is not None:
            person = email_address.person
            message = _('${email} is already registered in Launchpad and is '
                        'associated with <a href="${url}">${person}</a>.',
                        mapping={'email': escape(email),
                                'url': canonical_url(person),
                                'person': escape(person.displayname)})
        elif email_address.account is not None:
            account = email_address.account
            message = _('${email} is already registered in Launchpad and is '
                        'associated with the ${account} account.',
                        mapping={'email': escape(email),
                                'account': escape(account.displayname)})
        else:
            message = _('${email} is already registered in Launchpad.',
                        mapping={'email': escape(email)})
        raise LaunchpadValidationError(structured(message))


def validate_new_team_email(email):
    """Check that the given email is valid and not registered to
    another launchpad account.
    """
    from canonical.launchpad.webapp.publisher import canonical_url
    from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet

    _validate_email(email)
    _check_email_availability(email)
    return True


def validate_new_person_email(email):
    """Check that the given email is valid and not registered to
    another launchpad account.

    This validator is supposed to be used only when creating a new profile
    using the /people/+newperson page, as the message will say clearly to the
    user that the profile he's trying to create already exists, so there's no
    need to create another one.
    """
    from canonical.launchpad.webapp.publisher import canonical_url
    from lp.registry.interfaces.person import IPersonSet
    _validate_email(email)
    owner = getUtility(IPersonSet).getByEmail(email)
    if owner is not None:
        message = _("The profile you're trying to create already exists: "
                    '<a href="${url}">${owner}</a>.',
                    mapping={'url': canonical_url(owner),
                             'owner': escape(owner.displayname)})
        raise LaunchpadValidationError(structured(message))
    return True


def validate_new_distrotask(bug, distribution, sourcepackagename=None):
    """Validate a distribution bugtask to be added.

    Make sure that the isn't already a distribution task without a
    source package, or that such task is added only when the bug doesn't
    already have any tasks for the distribution.

    The same checks as `validate_distrotask` does are also done.
    """
    from canonical.launchpad.helpers import shortlist

    if sourcepackagename:
        # Ensure that there isn't already a generic task open on the
        # distribution for this bug, because if there were, that task
        # should be reassigned to the sourcepackage, rather than a new
        # task opened.
        if bug.getBugTask(distribution) is not None:
            raise LaunchpadValidationError(_(
                    'This bug is already open on ${distribution} with no '
                    'package specified. You should fill in a package '
                    'name for the existing bug.',
                    mapping={'distribution': distribution.displayname}))
    else:
        # Prevent having a task on only the distribution if there's at
        # least one task already on the distribution, whether or not
        # that task also has a source package.
        distribution_tasks_for_bug = [
            bugtask for bugtask
            in shortlist(bug.bugtasks, longest_expected=50)
            if bugtask.distribution == distribution]

        if len(distribution_tasks_for_bug) > 0:
            raise LaunchpadValidationError(_(
                    'This bug is already on ${distribution}. Please '
                    'specify an affected package in which the bug '
                    'has not yet been reported.',
                    mapping={'distribution': distribution.displayname}))
    validate_distrotask(bug, distribution, sourcepackagename)


def validate_distrotask(bug, distribution, sourcepackagename=None):
    """Check if a distribution bugtask already exists for a given bug.

    If validation fails, a LaunchpadValidationError will be raised.
    """
    if sourcepackagename is not None and len(distribution.series) > 0:
        # If the distribution has at least one series, check that the
        # source package has been published in the distribution.
        try:
            distribution.guessPackageNames(sourcepackagename.name)
        except NotFoundError, e:
            raise LaunchpadValidationError(e)
    new_source_package = distribution.getSourcePackage(sourcepackagename)
    if sourcepackagename is not None and (
        bug.getBugTask(new_source_package) is not None):
        # Ensure this distribution/sourcepackage task is unique.
        raise LaunchpadValidationError(_(
                'This bug has already been reported on ${source} '
                '(${distribution}).',
                mapping={'source': sourcepackagename.name,
                         'distribution': distribution.name}))
    elif (sourcepackagename is None and
          bug.getBugTask(distribution) is not None):
        # Don't allow two distribution tasks with no source package.
        raise LaunchpadValidationError(_(
                'This bug has already been reported on ${distribution}.',
                 mapping={'distribution': distribution.name}))
    else:
        # The bugtask is valid.
        pass


def valid_upstreamtask(bug, product):
    """Check if a product bugtask already exists for a given bug.

    If it exists, WidgetsError will be raised.
    """
    # Local import to avoid circular imports.
    from lp.bugs.interfaces.bugtask import BugTaskSearchParams
    errors = []
    user = getUtility(ILaunchBag).user
    params = BugTaskSearchParams(user, bug=bug)
    if not product.searchTasks(params).is_empty():
        errors.append(LaunchpadValidationError(_(
            'A fix for this bug has already been requested for ${product}',
            mapping={'product': product.displayname})))

    if errors:
        raise WidgetsError(errors)


def valid_password(password):
    """Return True if the argument is a valid password.

    A valid password contains only ASCII characters in range(32,127).
    No ASCII control characters are allowed.

    password that contains only valid ASCII characters
    >>> valid_password(u"All ascii password with spaces.:\\&/")
    True

    password that contains some non-ASCII character (value > 127)
    >>> valid_password(u"password with some non-ascii" + unichr(195))
    False

    password that contains ASCII control characters (0 >= value >= 31)
    >>> valid_password(u"password with control chars" + chr(20))
    False

    empty password.
    >>> valid_password(u"")
    True

    """
    assert isinstance(password, unicode)
    valid_chars = [chr(x) for x in range(32, 127)]
    invalid = set(password) - set(valid_chars)
    if invalid:
        return False
    else:
        return True


def validate_date_interval(start_date, end_date, error_msg=None):
    """Check if start_date precedes end_date.

    >>> from datetime import datetime
    >>> start = datetime(2006, 7, 18)
    >>> end = datetime(2006, 8, 18)
    >>> validate_date_interval(start, end)
    >>> validate_date_interval(end, start)
    Traceback (most recent call last):
    ...
    WidgetsError: LaunchpadValidationError: This event can't start after it
    ends.
    >>> validate_date_interval(end, start, error_msg="A custom error msg")
    Traceback (most recent call last):
    ...
    WidgetsError: LaunchpadValidationError: A custom error msg

    """
    if error_msg is None:
        error_msg = _("This event can't start after it ends.")
    if start_date >= end_date:
        raise WidgetsError([LaunchpadValidationError(error_msg)])

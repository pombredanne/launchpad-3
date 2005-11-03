
__all__ = [
    'validate_url',
    'valid_webref',
    'non_duplicate_bug',
    'valid_bug_number',
    'valid_emblem',
    'valid_hackergotchi',
    ]

import urllib
from textwrap import dedent
from StringIO import StringIO

from zope.component import getUtility
from zope.exceptions import NotFoundError

from canonical.launchpad import _
from canonical.launchpad.interfaces.launchpad import ILaunchBag
from canonical.launchpad.validators import LaunchpadValidationError

def validate_url(url, valid_schemes):
    """Returns a boolean stating whether 'url' is a valid URL.

       A URL is valid if:
           - its URL scheme is in the provided 'valid_schemes' list, and
           - it has a non-empty host name.

       None and an empty string are not valid URLs::

           >>> _validate_url(None, [])
           False
           >>> _validate_url('', [])
           False

       The valid_schemes list is checked::

           >>> _validate_url('http://example.com', ['http'])
           True
           >>> _validate_url('http://example.com', ['https', 'ftp'])
           False

       A URL without a host name is not valid:

           >>> _validate_url('http://', ['http'])
           False

      """
    if not url:
        return False
    scheme, host = urllib.splittype(url)
    if not scheme in valid_schemes:
        return False
    host, path = urllib.splithost(host)
    if not host:
        return False
    return True


def valid_webref(web_ref):
    if validate_url(web_ref, ['http', 'https', 'ftp']):
        # Allow ftp so valid_webref can be used for download_url, and so
        # it doesn't lock out weird projects where the site or
        # screenshots are kept on ftp.
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Not a valid URL. Please enter the full URL, including the
            scheme (for instance, http:// for a web URL), and ensure the
            URL uses either http, https or ftp.""")))

def non_duplicate_bug(value):
    """Prevent dups of dups.

    Returns True if the dup target is not a duplicate /and/ if the
    current bug doesn't have any duplicates referencing it /and/ if the
    bug isn't a duplicate of itself, otherwise
    return False.
    """

    from canonical.launchpad.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    duplicate = getUtility(ILaunchBag).bug
    dup_target = value
    current_bug_has_dup_refs = bugset.searchAsUser(
        user=getUtility(ILaunchBag).user,
        duplicateof=duplicate).count()
    target_is_dup = dup_target.duplicateof
    if duplicate == dup_target:
        raise LaunchpadValidationError(_(dedent("""
            You can't mark a bug as a duplicate of itself.""")))

    if (not target_is_dup) and (not current_bug_has_dup_refs):
        return True
    else:
        raise LaunchpadValidationError(_(dedent("""
            Bug %i is already a duplicate of bug %i. You can only
            duplicate to bugs that are not duplicates themselves.
            """% (dup_target.id, (dup_target.duplicateof).id))))


def valid_bug_number(value):
    from canonical.launchpad.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    try:
        bugset.get(value)
    except NotFoundError:
        return False
    return True


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


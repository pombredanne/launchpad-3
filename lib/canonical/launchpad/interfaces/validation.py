
__all__ = [
    'validate_url',
    'valid_webref',
    'non_duplicate_bug',
    ]

import urllib
from zope.component import getUtility
from sqlobject import SQLObjectNotFound
from canonical.launchpad.interfaces.launchpad import ILaunchBag


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
    return validate_url(web_ref, ['http', 'https'])


def non_duplicate_bug(value):
    """Prevent dups of dups.

    Returns True if the dup target is not a duplicate /and/ if the
    current bug doesn't have any duplicates referencing it, otherwise
    return False.
    """

    from canonical.launchpad.interfaces.bug import IBugSet
    bugset = getUtility(IBugSet)
    duplicate = getUtility(ILaunchBag).bug
    dup_target = bugset.get(value)
    current_bug_has_dup_refs = bugset.search(duplicateof = duplicate).count()
    target_is_dup = dup_target.duplicateof

    if (not target_is_dup) and (not current_bug_has_dup_refs):
        return True
    else:
        return False


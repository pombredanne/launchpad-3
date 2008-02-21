# Copyright 2006 Canonical Ltd.  All rights reserved.
"""Give access to bzr version info, if available.

The bzr version info file is expected to be in the Launchpad root in the
file bzr-version-info.py.

From this module, you can get:

  versioninfo: the version_info dict
  revno: the revision number
  date: the date of the last revision
  branch_nick: the branch nickname

If the bzr-version-info.py file does not exist, then revno, date and
branch_nick will all be None.

If that file exists, and contains valid python, revno, date and branch_nick
will have appropriate values from version_info.

If that file exists, and contains invalid python, there will be an error when
this module is loaded.  This module is imported into
canonical/launchpad/__init__.py so that such errors are caught at start-up.

"""

import imp

__all__ = ['versioninfo', 'revno', 'date', 'branch_nick']


def read_version_info():
    try:
        infomodule = imp.load_source(
            'launchpadversioninfo', 'bzr-version-info.py')
    except IOError:
        return None
    else:
        return getattr(infomodule, 'version_info', None)


versioninfo = read_version_info()


if versioninfo is None:
    revno = None
    date = None
    branch_nick = None
else:
    revno = versioninfo.get('revno')
    date = versioninfo.get('date')
    branch_nick = versioninfo.get('branch_nick')


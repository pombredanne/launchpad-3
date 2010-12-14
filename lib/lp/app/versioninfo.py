# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Give access to bzr and other version info, if available.

The bzr version info file is expected to be in the Launchpad root in the
file bzr-version-info.py.

From this module, you can get:

  versioninfo: the version_info dict
  revno: the revision number
  date: the date of the last revision
  branch_nick: the branch nickname

If the bzr-version-info.py file does not exist, then revno, date and
branch_nick will all be None.

If that file exists, and contains valid Python, revno, date and branch_nick
will have appropriate values from version_info.

If that file exists, and contains invalid Python, there will be an error when
this module is loaded.  This module is imported into
canonical/launchpad/__init__.py so that such errors are caught at start-up.

This module also reads version.txt at the top of the tree (i.e. a sibling of
bzr-version-info.py), which contains the Launchpad release number.  If that
file does not exist, we make something up.
"""

__all__ = [
    'branch_nick',
    'date',
    'revno',
    'versioninfo',
    ]


def read_version_info():
    try:
        import launchpadversioninfo
    except ImportError:
        return None
    else:
        return getattr(launchpadversioninfo, 'version_info', None)


versioninfo = read_version_info()


if versioninfo is None:
    revno = None
    date = None
    branch_nick = None
else:
    revno = versioninfo.get('revno')
    date = versioninfo.get('date')
    branch_nick = versioninfo.get('branch_nick')


try:
    version_file = open('version.txt')
except IOError:
    release = 'x.y.z'
else:
    try:
        version_data = version_file.read()
        release = version_data.strip()
    finally:
        version_file.close()

# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Give access to version info, if available.

The version info file is expected to be in the Launchpad root in the
file version-info.py.

From this module, you can get:

  versioninfo: the version_info dict
  revision: the commit ID (Git) or revision number (Bazaar)
  display_revision: `revision` formatted for display
  date: the date of the last revision
  branch_nick: the branch nickname

If the version-info.py file does not exist, then revision, display_revision,
date, and branch_nick will all be None.

If that file exists, and contains valid Python, revision, display_revision,
date, and branch_nick will have appropriate values from version_info.

If that file exists, and contains invalid Python, there will be an error when
this module is loaded.  This module is imported into lp/app/__init__.py so
that such errors are caught at start-up.
"""

__all__ = [
    'branch_nick',
    'date',
    'display_revision',
    'revision',
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
    revision = None
    display_revision = None
    date = None
    branch_nick = None
else:
    if 'revno' in versioninfo:
        revision = versioninfo.get('revno')
        display_revision = revision
    else:
        revision = versioninfo.get('revision_id')
        display_revision = revision[:7]
    date = versioninfo.get('date')
    branch_nick = versioninfo.get('branch_nick')

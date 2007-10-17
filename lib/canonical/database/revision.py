# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Code dealing with the Launchpad database patch level."""

__metaclass__ = type
__all__ = ['confirm_dbrevision', 'InvalidDatabaseRevision']

from glob import glob
import os.path
import re

from canonical.config import config
from canonical.database.sqlbase import connect


class InvalidDatabaseRevision(Exception):
    """Exception raised by confirm_dbrevision."""


def confirm_dbrevision(cur):
    """Check that the database we are connected to is the same
    database patch level as expected by the code.

    Raises an InvalidDatabaseRevision exception if the database patch level
    is not what is expected.
    """
    # Get a list of patches the code expects to have been applied from the
    # filesystem.
    schema_dir = os.path.join(config.root, 'database', 'schema')
    patches_glob = os.path.join(schema_dir, 'patch-??-??-?.sql')
    fs_patches = []
    for patch_file in glob(patches_glob):
        match = re.search('patch-(\d\d)-(\d\d)-(\d).sql', patch_file)
        if match is None:
            raise InvalidDatabaseRevision("Bad patch name %r" % (patch_file,))
        fs_patches.append(
                (int(match.group(1)), int(match.group(2)), int(match.group(3)))
                )
    fs_patches.sort()

    # Get a list of patches that have been applied to the database.
    # We skip any patches from earlier 'major' revision levels, as they
    # are no longer stored on the filesystem.
    fs_major = fs_patches[0][0]
    cur.execute("""
        SELECT major, minor, patch FROM LaunchpadDatabaseRevision
        ORDER BY major, minor, patch
        """)
    db_patches = [
            (major, minor, patch) for major, minor, patch in cur.fetchall()
                if major >= fs_major
            ]

    # Raise an exception if we have a patch on the filesystem that has not
    # been applied to the database.
    for patch_tuple in fs_patches:
        if patch_tuple not in db_patches:
            raise InvalidDatabaseRevision(
                "patch-%02d-%02d-%d.sql has not been applied to the database"
                % patch_tuple
                )

    # Raise an exeption if we have a patch applied to the database that
    # cannot be found on the filesystem. We ignore patches with a non-zero
    # 'patch' part to its version number as these patches are used to apply
    # fixes to the live database that should be backported to the code trunk.
    # (This may be problematic with some systems such as the authserver and
    # librarian that we roll out infrequently. We may want a less strict
    # version of this function to check database revisions with these
    # services).
    for patch_tuple in db_patches:
        if patch_tuple[2] == 0 and patch_tuple not in fs_patches:
            raise InvalidDatabaseRevision(
                "patch-%02d-%02d-%d.sql has been applied to the database "
                "but does not exist in this source code tree"
                % patch_tuple
                )

def confirm_dbrevision_on_startup(*ignored):
    """Event handler that calls confirm_dbrevision"""
    con = connect(config.launchpad.dbuser)
    try:
        cur = con.cursor()
        confirm_dbrevision(cur)
    finally:
        con.close()


# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type
import unittest
import re
import os
import os.path
from glob import glob
from harness import LaunchpadTestCase

class DbRevisionTestCase(LaunchpadTestCase):
    def test_dbrevision(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            SELECT major, minor, patch FROM LaunchpadDatabaseRevision 
            ORDER BY major, minor, patch
            """)
        db_patches = [tuple(r) for r in cur.fetchall()]
        cur.close()
        con.close()

        schema_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            os.pardir, os.pardir, os.pardir, os.pardir,
            'database', 'schema',
            ))
        patches_glob = os.path.join(schema_dir, 'patch-??-??-?.sql')
        fs_patches = glob(patches_glob)
        fs_patches.sort()

        for patch in fs_patches:
            m = re.search('patch-(\d\d)-(\d\d)-(\d).sql', patch)
            self.failUnless(m, 'Bad patch name %r' % patch)
            fs_patchlevel = (int(m.group(1)), int(m.group(2)), int(m.group(3)))
            self.failUnless(fs_patchlevel in db_patches,
                    'Patch %s has not been applied to the database '
                    'or failed to update LaunchpadDatabaseRevision' 
                    % os.path.basename(patch))

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DbRevisionTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()


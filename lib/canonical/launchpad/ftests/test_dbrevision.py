import unittest, re, os
from glob import glob
from harness import LaunchpadTestCase

class DbRevisionTestCase(LaunchpadTestCase):
    def test_dbrevision(self):
        con = self.connect()
        cur = con.cursor()
        cur.execute("""
            select major, minor, patch from launchpaddatabaserevision 
            """)
        r = list(cur.fetchall())
        self.failUnlessEqual(
                len(r), 1,
                'Got %s rows from LaunchpadDatabaseRevision' % len(r)
                )
        db_patchlevel = r[0]

        schema_dir = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            os.pardir, os.pardir, os.pardir, os.pardir,
            'database', 'schema',
            ))
        patches_glob = os.path.join(schema_dir, 'patch-?-??-?.sql')
        patches = glob(patches_glob)
        patches.sort()

        highest_patch = patches[-1]
        m = re.search('patch-(\d)-(\d\d)-(\d).sql', highest_patch)
        self.failUnless(m, 'Bad patch name %r' % highest_patch)

        fs_patchlevel = (int(m.group(1)), int(m.group(2)), int(m.group(3)))

        self.failUnlessEqual(
                db_patchlevel, fs_patchlevel,
                'Database reports patchlevel %r, but found patch %r on fs. '
                'Database patch level is probably out of date' % (
                    db_patchlevel, fs_patchlevel
                    )
                )
        cur.close()
        con.close()

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(DbRevisionTestCase))
    return suite

if __name__ == '__main__':
    unittest.main()


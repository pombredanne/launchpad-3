# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest, subprocess, os.path, sys

from canonical.launchpad.ftests.harness import LaunchpadTestCase
from canonical.config import config

class UpdateStatsTest(LaunchpadTestCase):

    dbuser = 'statistician'

    def tearDown(self):
        con = self.connect()
        # Force a commit here so test harness optimizations know the database
        # has been messed with by a subprocess.
        con.commit()
        LaunchpadTestCase.tearDown(self)

    @property
    def script(self):
        script = os.path.join(config.root, 'cronscripts', 'update-stats.py')
        assert os.path.exists(script), '%s not found' % script
        return script

    def test_basic(self):
        # Nuke some stats so we know that they are updated
        con = self.connect()
        cur = con.cursor()

        # Destroy the LaunchpadStatistic entries so we can confirm they are
        # updated.
        cur.execute("DELETE FROM LaunchpadStatistic WHERE name='pofile_count'")
        cur.execute("""
            UPDATE LaunchpadStatistic
            SET value=-1, dateupdated=now()-'10 weeks'::interval
            """)

        # Destroy the messagecount caches on distrorelease so we can confirm
        # they are all updated.
        cur.execute("UPDATE DistroRelease SET messagecount=-1")

        # Delete half the entries in the DistroReleaseLanguage cache so we
        # can confirm they are created as required, and set the remainders
        # to invalid values so we can confirm they are updated.
        cur.execute("""
            DELETE FROM DistroReleaseLanguage 
            WHERE id > (SELECT max(id) FROM DistroReleaseLanguage)/2
            """)
        cur.execute("""
            UPDATE DistroReleaseLanguage
            SET
                currentcount=-1, updatescount=-1, rosettacount=-1,
                contributorcount=-1, dateupdated=now()-'10 weeks'::interval
            """)

        # Update stats should create missing distroreleaselanguage,
        # so remember how many there are before the run.
        cur.execute("SELECT COUNT(*) FROM DistroReleaseLanguage")
        num_distroreleaselanguage = cur.fetchone()[0]

        # Commit our changes so the subprocess can see them
        con.commit()

        # Run the update-stats.py script
        cmd = [sys.executable, self.script, '--quiet']
        process = subprocess.Popen(
                cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
                )
        (stdout, empty_stderr) = process.communicate()

        # Ensure it returned a success code
        self.failUnlessEqual(
                process.returncode, 0,
                'update-stats.py exited with return code %d. Output was %r' % (
                    process.returncode, stdout
                    )
                )
        # With the -q option, it should produce no output if things went
        # well.
        self.failUnlessEqual(
                stdout, '',
                'update-stats.py was noisy. Emitted:\n%s' % stdout
                )

        # Now confirm it did stuff it is supposed to
        cur = con.cursor()

        # Make sure all DistroRelease.messagecount entries are updated
        cur.execute("SELECT COUNT(*) FROM DistroRelease WHERE messagecount=-1")
        self.failUnlessEqual(cur.fetchone()[0], 0)

        # Make sure we have created missing DistroReleaseLanguage entries
        cur.execute("SELECT COUNT(*) FROM DistroReleaseLanguage")
        self.failUnless(cur.fetchone()[0] > num_distroreleaselanguage)

        # Make sure existing DistroReleaseLanauge entries have been updated.
        cur.execute("""
            SELECT COUNT(*) FROM DistroReleaseLanguage, Language
            WHERE DistroReleaseLanguage.language = Language.id AND
                  Language.visible = TRUE AND currentcount = -1
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        cur.execute("""
            SELECT COUNT(*) FROM DistroReleaseLanguage, Language
            WHERE DistroReleaseLanguage.language = Language.id AND
                  Language.visible = TRUE AND updatescount = -1
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        cur.execute("""
            SELECT COUNT(*) FROM DistroReleaseLanguage, Language
            WHERE DistroReleaseLanguage.language = Language.id AND
                  Language.visible = TRUE AND rosettacount = -1
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        cur.execute("""
            SELECT COUNT(*) FROM DistroReleaseLanguage, Language
            WHERE DistroReleaseLanguage.language = Language.id AND
                  Language.visible = TRUE AND contributorcount = -1
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        cur.execute("""
            SELECT COUNT(*) FROM DistroReleaseLanguage, Language
            WHERE DistroReleaseLanguage.language = Language.id AND
                  Language.visible = TRUE AND
                  dateupdated < now() - '2 days'::interval
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        # All LaunchpadStatistic rows should have been updated
        cur.execute("""
            SELECT COUNT(*) FROM LaunchpadStatistic
            WHERE value=-1
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)
        cur.execute("""
            SELECT COUNT(*) FROM LaunchpadStatistic
            WHERE dateupdated < now() - '2 days'::interval
            """)
        self.failUnlessEqual(cur.fetchone()[0], 0)

        keys = [
            'potemplate_count', 'pofile_count', 'pomsgid_count',
            'translator_count', 'language_count',
            'people_count', 'teams_count',
            ]

        for key in keys:
            cur.execute("""
                SELECT value from LaunchpadStatistic WHERE name=%(key)s
                """, vars())
            row = cur.fetchone()
            self.failIf(row is None, '%s not updated' % key)
            self.failUnless(row[0] > 0, '%s is invalid' % key)


def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpdateStatsTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest=test_suite)


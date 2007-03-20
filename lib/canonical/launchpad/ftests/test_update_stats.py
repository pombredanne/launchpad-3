# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import unittest, subprocess, os.path, sys

from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.ftests.harness import (
    LaunchpadTestCase, LaunchpadFunctionalTestCase)
from canonical.launchpad.interfaces import (
    IDistributionSet, IDistroReleaseSet, ILanguageSet, IPOTemplateSet,
    IPersonSet)
from canonical.config import config

def get_script():
    script = os.path.join(config.root, 'cronscripts', 'update-stats.py')
    assert os.path.exists(script), '%s not found' % script
    return script

class UpdateStatsTest(LaunchpadTestCase):

    dbuser = 'statistician'

    def tearDown(self):
        con = self.connect()
        # Force a commit here so test harness optimizations know the database
        # has been messed with by a subprocess.
        con.commit()
        LaunchpadTestCase.tearDown(self)

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
        cmd = [sys.executable, get_script(), '--quiet']
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
            'translator_count', 'language_count', 'bug_count', 'bugtask_count',
            'people_count', 'teams_count', 'rosetta_translator_count',
            'products_with_potemplates', 'projects_with_bugs',
            'products_using_malone', 'products_using_rosetta',
            ]

        for key in keys:
            cur.execute("""
                SELECT value from LaunchpadStatistic WHERE name=%(key)s
                """, vars())
            row = cur.fetchone()
            self.failIf(row is None, '%s not updated' % key)
            self.failUnless(row[0] >= 0, '%s is invalid' % key)


class UpdateTranslationStatsWithDisabledTemplateTest(
    LaunchpadFunctionalTestCase):

    def setUp(self):
        LaunchpadFunctionalTestCase.setUp(self)

        self.distribution = getUtility(IDistributionSet)
        self.distroreleaseset = getUtility(IDistroReleaseSet)
        self.languageset = getUtility(ILanguageSet)
        self.potemplateset = getUtility(IPOTemplateSet)
        self.personset = getUtility(IPersonSet)

        # This test needs to do some changes that require admin permissions.
        login('carlos@canonical.com')


    def test_basic(self):
        # First, we check current values of cached statistics.

        # We get some objects we will need for this test.
        ubuntu = self.distribution['ubuntu']
        hoary = self.distroreleaseset.queryByName(ubuntu, 'hoary')
        spanish = self.languageset['es']
        spanish_hoary = hoary.getDistroReleaseLanguage(spanish)
        # We need pmount's template.
        templates = self.potemplateset.getAllByName('pmount')
        pmount_template = None
        for template in templates:
            if template.distrorelease == hoary:
                pmount_template = template

        self.failIfEqual(pmount_template, None)

        # Let's calculate the statistics ourselves so we can check that cached
        # values are the right ones.
        messagecount = 0
        currentcount = 0
        for template in hoary.currentpotemplates:
            messagecount += template.messageCount()
            # Get the Spanish IPOFile.
            pofile = template.getPOFileByLang('es')
            if pofile is not None:
                # This method should not return any IPOFile with variant field
                # set.
                assert pofile.variant is None
                currentcount += pofile.currentCount()
        contributor_count = (
            self.personset.getPOFileContributorsByDistroRelease(
                hoary, spanish).count())

        # As noted in the for loop, we don't count IPOFile objects with
        # variants. Here we can see that, actually, there are translations
        # in a IPOFile with the variant field set so it's not just that we
        # count it with a '0' value.
        pofile_with_variant = pmount_template.getPOFileByLang('es', u'test')
        self.failIf(pofile_with_variant.currentCount() <= 0)


        # The amount of messages to translate in Hoary is the expected.
        self.failUnlessEqual(hoary.messagecount, messagecount)

        # And the same for translations and contributors.
        self.failUnlessEqual(spanish_hoary.currentCount(), currentcount)
        self.failUnlessEqual(spanish_hoary.contributor_count,
            contributor_count)

        # Let's set 'pmount' template as not current for Hoary.
        pmount_template.iscurrent = False
        # And store its statistics values to validate cached values later.
        pmount_messages = pmount_template.messageCount()
        pmount_spanish_pofile = pmount_template.getPOFileByLang('es')
        pmount_spanish_translated = pmount_spanish_pofile.currentCount()

        # Commit the current transaction because the script will run in
        # another transaction and thus it won't see the changes done on this
        # test unless we commit.
        # XXX CarlosPerelloMarin 20070122: Unecessary flush_database_updates
        # required. See bug #3989 for more info.
        from canonical.database.sqlbase import flush_database_updates
        flush_database_updates()
        import transaction
        transaction.commit()

        # Run update-stats.py script to see that we don't count the
        # information in that template anymore.
        cmd = [sys.executable, get_script(), '--quiet']
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

        # Now confirm it did stuff it is supposed to

        # We flush the caches, so that the above defined objects gets
        # their content from the modified DB.
        from canonical.database.sqlbase import flush_database_caches
        flush_database_caches()

        # The transaction changed, we need to refetch SQLObjects.
        ubuntu = self.distribution['ubuntu']
        hoary = self.distroreleaseset.queryByName(ubuntu, 'hoary')
        spanish = self.languageset['es']
        spanish_hoary = hoary.getDistroReleaseLanguage(spanish)

        # Let's recalculate the statistics ourselved to validate what the
        # script run recalculated.
        new_messagecount = 0
        new_currentcount = 0
        for template in hoary.currentpotemplates:
            new_messagecount += template.messageCount()
            pofile = template.getPOFileByLang('es')
            if pofile is not None:
                new_currentcount += pofile.currentCount()

        new_contributor_count = (
            self.personset.getPOFileContributorsByDistroRelease(
                hoary, spanish).count())

        # The amount of messages to translate in Hoary is now lower because we
        # don't count anymore pmount messages.
        self.failUnlessEqual(hoary.messagecount, new_messagecount)
        self.failIf(messagecount <= new_messagecount)
        self.failUnlessEqual(messagecount - pmount_messages, new_messagecount)

        # The amount of messages translate into Spanish is also lower now
        # because we don't count Spanish translations for pmount anymore.
        self.failUnlessEqual(spanish_hoary.currentCount(), new_currentcount)
        self.failIf(currentcount <= new_currentcount)
        self.failUnlessEqual(currentcount - pmount_spanish_translated,
            new_currentcount)

        # Also, there are two Spanish translators that only did contributions
        # to pmount, so they are gone now.
        self.failUnlessEqual(
            spanish_hoary.contributor_count, new_contributor_count)
        self.failIf(contributor_count <= new_contributor_count)

def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(UpdateStatsTest))
    suite.addTest(
        unittest.makeSuite(UpdateTranslationStatsWithDisabledTemplateTest))
    return suite


if __name__ == '__main__':
    unittest.main(defaultTest=test_suite)


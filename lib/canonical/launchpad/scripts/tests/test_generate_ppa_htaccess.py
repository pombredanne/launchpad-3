# Copyright 2009 Canonical Ltd.  All rights reserved.
"""Test the generate_ppa_htaccess.py script. """

import crypt
import os
import subprocess
import sys
import tempfile
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.config import config
from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet, TeamMembershipStatus)
from canonical.launchpad.scripts import QuietFakeLogger
from canonical.launchpad.scripts.generate_ppa_htaccess import (
    HtaccessTokenGenerator)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.testing.layers import LaunchpadZopelessLayer


class TestPPAHtaccessTokenGeneration(unittest.TestCase):
    """Test the generate_ppa_htaccess.py script."""

    layer = LaunchpadZopelessLayer
    dbuser = config.generateppahtaccess.dbuser

    def setUp(self):
        self.ppa = getUtility(IPersonSet).getByName('cprov').archive
        self.ppa.private = True
        self.ppa.buildd_secret = "secret"

        # "Ubuntu" doesn't have a proper publisher config but Ubuntutest
        # does, so override the PPA's distro here.
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.ppa.distribution = ubuntutest

    def getScript(self, test_args=None):
        """Return a HtaccessTokenGenerator instance."""
        if test_args is None:
            test_args = []
        script = HtaccessTokenGenerator("test tokens", test_args=test_args)
        script.logger = QuietFakeLogger()
        script.txn = self.layer.txn
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        return script

    def runScript(self):
        """Run the expiry script.
        
        :return: a tuple of return code, stdout and stderr.
        """
        script = os.path.join(
            config.root, "cronscripts", "generate-ppa-htaccess.py")
        args = [sys.executable, script, "-v"]
        process = subprocess.Popen(
            args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        return process.returncode, stdout, stderr

    def testEnsureHtaccess(self):
        """Ensure that the .htaccess file is generated correctly."""
        # The publisher Config object does not have an interface, so we
        # need to remove the security wrapper.
        pub_config = removeSecurityProxy(self.ppa.getPubConfig())

        filename = os.path.join(pub_config.htaccessroot, ".htaccess")
        if os.path.isfile(filename):
            os.remove(filename)
        script = self.getScript()
        script.ensureHtaccess(self.ppa)
        self.assertTrue(
            os.path.isfile(filename),
            "%s is not present when it should be" % filename)

        contents = [
            "",
            "AuthType           Basic",
            "AuthName           \"Token Required\"",
            "AuthUserFile       %s/.htpasswd" % pub_config.htaccessroot,
            "Require            valid-user",
            ]

        file = open(filename, "r")
        file_contents = file.read().splitlines()
        file.close()
        os.remove(filename)

        self.assertEqual(contents, file_contents)

    def testWriteHtpasswd(self):
        """Test that writing the .htpasswd file works properly."""
        fd, filename = tempfile.mkstemp()
        script = self.getScript()

        TEST_PASSWORD = "password"
        TEST_PASSWORD2 = "passwor2"

        # We provide a constant salt to the crypt function so that we
        # can test the encrypted result.
        SALT = "XX"

        user1 = ("user", TEST_PASSWORD, SALT)
        user2 = ("user2", TEST_PASSWORD2, SALT)
        list_of_users = [user1]
        list_of_users.append(user2)

        # Run the script
        script.writeHtpasswd(filename, list_of_users)

        expected_contents = [
            "user:XXq2wKiyI43A2",
            "user2:XXaQB8b5Gtwi."
            ]

        file = open(filename, "r")
        file_contents = file.read().splitlines()
        file.close()
        os.remove(filename)

        self.assertEqual(expected_contents, file_contents)

    def testGenerateHtpasswd(self):
        """Given some `ArchiveAuthToken`s, test generating htpasswd."""
        # Make some subscriptions and tokens.
        name12 = getUtility(IPersonSet).getByName("name12")
        name16 = getUtility(IPersonSet).getByName("name16")
        self.ppa.newSubscription(name12, self.ppa.owner)
        self.ppa.newSubscription(name16, self.ppa.owner)
        tokens = []
        tokens.append(self.ppa.newAuthToken(name12))
        tokens.append(self.ppa.newAuthToken(name16))

        # Generate the passwd file.
        script = self.getScript()
        filename = script.generateHtpasswd(self.ppa, tokens)

        # Read it back in.
        file = open(filename, "r")
        file_contents = file.read().splitlines()
        
        # The first line should be the buildd_secret.
        [user, password] = file_contents[0].split(":", 1)
        self.assertEqual(user, "buildd")
        # We can re-encrypt the buildd_secret and it should match the
        # one in the .htpasswd file.
        encrypted_secret = crypt.crypt(self.ppa.buildd_secret, password)
        self.assertEqual(encrypted_secret, password)

        # Finally, there should be two more lines in the file, one for
        # each of the tokens generated above.
        self.assertEqual(len(file_contents), 3)
        [user1, password1] = file_contents[1].split(":", 1)
        [user2, password2] = file_contents[2].split(":", 1)
        self.assertEqual(user1, "name12")
        self.assertEqual(user2, "name16")

        # For the names to appear in the order above, the dabatase IDs
        # for the tokens have to be in that order.  (To ensure a
        # consistent ordering)
        self.assertTrue(tokens[0].id < tokens[1].id) 

        os.remove(filename)

    def testReplaceUpdatedHtpasswd(self):
        """Test that the htpasswd file is only replaced if it changes."""
        FILE_CONTENT = "Kneel before Zod!"
        # The publisher Config object does not have an interface, so we
        # need to remove the security wrapper.
        pub_config = removeSecurityProxy(self.ppa.getPubConfig())
        filename = os.path.join(pub_config.htaccessroot, ".htpasswd")

        # Write out a dummy .htpasswd
        if not os.path.exists(pub_config.htaccessroot):
            os.makedirs(pub_config.htaccessroot)
        file = open(filename, "w")
        file.write(FILE_CONTENT)
        file.close()

        # Write the same contents in a temp file.
        fd, temp_filename = tempfile.mkstemp()
        file = open(temp_filename, "w")
        file.write(FILE_CONTENT)
        file.close()

        # Replacement should not happen.
        script = self.getScript()
        self.assertFalse(
            script.replaceUpdatedHtpasswd(self.ppa, temp_filename))

        # Writing a different .htpasswd should see it get replaced.
        file = open(filename, "w")
        file.write("Come to me, son of Jor-El!")
        file.close()

        self.assertTrue(
            script.replaceUpdatedHtpasswd(self.ppa, temp_filename))

        os.remove(filename)

    def assertDeactivated(self, token):
        """Helper function to test token deactivation state."""
        return self.assertNotEqual(token.date_deactivated, None)

    def assertNotDeactivated(self, token):
        """Helper function to test token deactivation state."""
        self.assertEqual(token.date_deactivated, None)

    def setupSubscriptionsAndTokens(self):
        """Set up a few subscriptions and test tokens and return them."""
        # Set up some teams.  We need to test a few scenarios:
        # - someone in one subscribed team and leaving that team loses
        #    their token.
        # - someone in two subscribed teams leaving one team does not
        #   lose their token.
        # - All members of a team lose their tokens when a team of a
        #   subscribed team leaves it.

        factory = LaunchpadObjectFactory()
        persons1 = []
        persons2 = []
        name12 = getUtility(IPersonSet).getByName("name12")
        team1 = factory.makeTeam(owner=name12)
        team2 = factory.makeTeam(owner=name12)
        for count in range(5):
            person = factory.makePerson()
            team1.addMember(person, name12)
            persons1.append(person)
            person = factory.makePerson()
            team2.addMember(person, name12)
            persons2.append(person)

        all_persons = persons1 + persons2

        parent_team = factory.makeTeam(owner=name12)
        # This needs to be forced or TeamParticipation is not updated.
        parent_team.addMember(team2, name12, force_team_add=True)

        promiscuous_person = factory.makePerson()
        team1.addMember(promiscuous_person, name12)
        team2.addMember(promiscuous_person, name12)
        all_persons.append(promiscuous_person)

        lonely_person = factory.makePerson()
        all_persons.append(lonely_person)

        # At this point we have team1, with 5 people in it, team2 with 5
        # people in it, team3 with only team2 in it, promiscuous_person
        # who is in team1 and team2, and lonely_person who is in no
        # teams.

        # Ok now do some subscriptions and ensure everyone has a token.
        self.ppa.newSubscription(team1, self.ppa.owner)
        self.ppa.newSubscription(parent_team, self.ppa.owner)
        self.ppa.newSubscription(lonely_person, self.ppa.owner)
        tokens = {}
        for person in all_persons:
            tokens[person] = self.ppa.newAuthToken(person)

        return (
            team1, team2, parent_team, lonely_person,
            promiscuous_person, all_persons, persons1, persons2, tokens)

    def testDeactivatingTokens(self):
        """Test that token deactivation happens properly."""
        data = self.setupSubscriptionsAndTokens()
        (team1, team2, parent_team, lonely_person, promiscuous_person,
            all_persons, persons1, persons2, tokens) = data
        team1_person = persons1[0]

        # Initially, nothing is eligible for deactivation.
        script = self.getScript()
        script.deactivateTokens(self.ppa)
        for person in tokens:
            self.assertNotDeactivated(tokens[person])

        # Now remove someone from team1, he will lose his token but
        # everyone else keeps theirs.
        self.layer.switchDbUser("launchpad")
        team1_person.leave(team1)
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.deactivateTokens(self.ppa)
        self.assertDeactivated(tokens[team1_person])
        del tokens[team1_person]
        for person in tokens:
            self.assertNotDeactivated(tokens[person])

        # Promiscuous_person now leaves team1, but does not lose his
        # token because he's also in team2. No other tokens are
        # affected.
        self.layer.switchDbUser("launchpad")
        promiscuous_person.leave(team1)
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.deactivateTokens(self.ppa)
        self.assertNotDeactivated(tokens[promiscuous_person])
        for person in tokens:
            self.assertNotDeactivated(tokens[person])

        # Team 2 now leaves parent_team, and all its members lose their
        # tokens.
        self.layer.switchDbUser("launchpad")
        name12 = getUtility(IPersonSet).getByName("name12")
        parent_team.setMembershipData(
            team2, TeamMembershipStatus.APPROVED, name12)
        parent_team.setMembershipData(
            team2, TeamMembershipStatus.DEACTIVATED, name12)
        self.assertFalse(team2.inTeam(parent_team))
        self.layer.txn.commit()
        self.layer.switchDbUser(self.dbuser)
        script.deactivateTokens(self.ppa)
        for person in persons2:
            self.assertDeactivated(tokens[person])

        # promiscuous_person also loses the token because he's not in
        # either team now.
        self.assertDeactivated(tokens[promiscuous_person])

        # lonely_person still has his token, he's not in any teams.
        self.assertNotDeactivated(tokens[lonely_person])

    def setupDummyTokens(self):
        """Helper function to set up some tokens."""
        name12 = getUtility(IPersonSet).getByName("name12")
        name16 = getUtility(IPersonSet).getByName("name16")
        sub1 = self.ppa.newSubscription(name12, self.ppa.owner)
        sub2 = self.ppa.newSubscription(name16, self.ppa.owner)
        token1 = self.ppa.newAuthToken(name12)
        token2 = self.ppa.newAuthToken(name16)
        self.layer.txn.commit()
        subs = [sub1]
        subs.append(sub2)
        tokens = [token1]
        tokens.append(token2)
        return subs, tokens

    def ensureNoFiles(self):
        """Ensure the .ht* files don't already exist."""
        pub_config = removeSecurityProxy(self.ppa.getPubConfig())
        htaccess = os.path.join(pub_config.htaccessroot, ".htaccess")
        htpasswd = os.path.join(pub_config.htaccessroot, ".htpasswd")
        if os.path.isfile(htaccess):
            os.remove(htaccess)
        if os.path.isfile(htpasswd):
            os.remove(htpasswd)
        return htaccess, htpasswd

    def testBasicOperation(self):
        """Invoke the actual script and make sure it generates some files."""
        self.setupDummyTokens()
        htaccess, htpasswd = self.ensureNoFiles()

        # Call the script and check that we have a .htaccess and a
        # .htpasswd.
        return_code, stdout, stderr = self.runScript()
        self.assertEqual(
            return_code, 0, "Got a bad return code of %s\nOutput:\n%s" % 
                (return_code, stderr))
        self.assertTrue(os.path.isfile(htaccess))
        self.assertTrue(os.path.isfile(htpasswd))
        os.remove(htaccess)
        os.remove(htpasswd)

    def _setupOptionsData(self):
        """Setup test data for option testing."""
        subs, tokens = self.setupDummyTokens()

        # Cancel the first subscription.
        subs[0].cancel(self.ppa.owner)
        self.assertNotDeactivated(tokens[0])
        return subs, tokens

    def testDryrunOption(self):
        """Test that the dryrun and no-deactivation option works."""
        subs, tokens = self._setupOptionsData()

        htaccess, htpasswd = self.ensureNoFiles()
        script = self.getScript(test_args=["--dry-run"])
        script.main()

        # Assert no files were written.
        self.assertFalse(os.path.isfile(htaccess))
        self.assertFalse(os.path.isfile(htpasswd))

        # Assert that the cancelled subscription did not cause the token
        # to get deactivated.
        self.assertNotDeactivated(tokens[0])

    def testNoDeactivationOption(self):
        """Test that the --no-deactivation option works."""
        subs, tokens = self._setupOptionsData()
        script = self.getScript(test_args=["--no-deactivation"])
        script.main()
        self.assertNotDeactivated(tokens[0])
        script = self.getScript()
        script.main()
        self.assertDeactivated(tokens[0])


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

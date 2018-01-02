# Copyright 2009-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test htaccess/htpasswd file generation. """

import os
import tempfile

from zope.component import getUtility

from lp.archivepublisher.htaccess import (
    htpasswd_credentials_for_archive,
    write_htaccess,
    write_htpasswd,
    )
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.person import IPersonSet
from lp.services.features.testing import FeatureFixture
from lp.soyuz.interfaces.archive import NAMED_AUTH_TOKEN_FEATURE_FLAG
from lp.testing import TestCaseWithFactory
from lp.testing.layers import LaunchpadZopelessLayer


class TestHtpasswdGeneration(TestCaseWithFactory):
    """Test htpasswd generation."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestHtpasswdGeneration, self).setUp()
        self.owner = self.factory.makePerson(
            name="joe", displayname="Joe Smith")
        self.ppa = self.factory.makeArchive(
            owner=self.owner, name="myppa", private=True)

        # "Ubuntu" doesn't have a proper publisher config but Ubuntutest
        # does, so override the PPA's distro here.
        ubuntutest = getUtility(IDistributionSet)['ubuntutest']
        self.ppa.distribution = ubuntutest

        # Enable named auth tokens.
        self.useFixture(FeatureFixture({NAMED_AUTH_TOKEN_FEATURE_FLAG: u"on"}))

    def test_write_htpasswd(self):
        """Test that writing the .htpasswd file works properly."""
        fd, filename = tempfile.mkstemp()
        os.close(fd)

        TEST_PASSWORD = "password"
        TEST_PASSWORD2 = "passwor2"

        # We provide a constant salt to the crypt function so that we
        # can test the encrypted result.
        SALT = "XX"

        user1 = ("user", TEST_PASSWORD, SALT)
        user2 = ("user2", TEST_PASSWORD2, SALT)
        list_of_users = [user1]
        list_of_users.append(user2)

        write_htpasswd(filename, list_of_users)

        expected_contents = [
            "user:XXq2wKiyI43A2",
            "user2:XXaQB8b5Gtwi.",
            ]

        file = open(filename, "r")
        file_contents = file.read().splitlines()
        file.close()
        os.remove(filename)

        self.assertEqual(expected_contents, file_contents)

    def test_write_htaccess(self):
        # write_access can write a correct htaccess file.
        fd, filename = tempfile.mkstemp()
        os.close(fd)

        write_htaccess(filename, "/some/distroot")
        self.assertTrue(
            os.path.isfile(filename),
            "%s is not present when it should be" % filename)
        self.addCleanup(os.remove, filename)

        contents = [
            "",
            "AuthType           Basic",
            "AuthName           \"Token Required\"",
            "AuthUserFile       /some/distroot/.htpasswd",
            "Require            valid-user",
            ]

        file = open(filename, "r")
        file_contents = file.read().splitlines()
        file.close()

        self.assertEqual(contents, file_contents)

    def test_credentials_for_archive_empty(self):
        # If there are no ArchiveAuthTokens for an archive just
        # the buildd secret is returned.
        self.ppa.buildd_secret = "sekr1t"
        self.assertEqual(
            [("buildd", "sekr1t", "bu")],
            list(htpasswd_credentials_for_archive(self.ppa)))

    def test_credentials_for_archive(self):
        # ArchiveAuthTokens for an archive are returned by
        # credentials_for_archive.
        self.ppa.buildd_secret = "geheim"
        name12 = getUtility(IPersonSet).getByName("name12")
        name16 = getUtility(IPersonSet).getByName("name16")
        hyphenated = self.factory.makePerson(name="a-b-c")
        self.ppa.newSubscription(name12, self.ppa.owner)
        self.ppa.newSubscription(name16, self.ppa.owner)
        self.ppa.newSubscription(hyphenated, self.ppa.owner)
        first_created_token = self.ppa.newAuthToken(name16)
        second_created_token = self.ppa.newAuthToken(name12)
        third_created_token = self.ppa.newAuthToken(hyphenated)
        named_token_20 = self.ppa.newNamedAuthToken(u"name20", as_dict=False)
        named_token_14 = self.ppa.newNamedAuthToken(u"name14", as_dict=False)
        named_token_99 = self.ppa.newNamedAuthToken(u"name99", as_dict=False)
        named_token_99.deactivate()

        expected_credentials = [
            ("buildd", "geheim", "bu"),
            ("+name14", named_token_14.token, "bm"),
            ("+name20", named_token_20.token, "bm"),
            ("a-b-c", third_created_token.token, "YS"),
            ("name12", second_created_token.token, "bm"),
            ("name16", first_created_token.token, "bm"),
            ]
        credentials = list(htpasswd_credentials_for_archive(self.ppa))

        # Use assertEqual instead of assertContentEqual to verify order.
        self.assertEqual(expected_credentials, credentials)

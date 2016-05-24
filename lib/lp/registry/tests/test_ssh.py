# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SSHKey."""

__metaclass__ = type

from testtools.matchers import StartsWith
from zope.component import getUtility

from lp.registry.interfaces.ssh import (
    ISSHKeySet,
    SSHKeyCompromisedError,
    SSHKeyType,
    )
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.mail_helpers import pop_notifications


VULNERABLE_RSA_KEY = (
    "ssh-rsa "
    "AAAAB3NzaC1yc2EAAAABIwAAAQEArPO3VWegIxlZsd9zAAKQ9x3TNXzU0AtM2QF3y92wIDgwX"
    "DuNcchze3SnTyGDO4l4cIqpvMV8XLZlRUbNDr5hoSGUNPqZxI8ycdfcGyKXLlkMsSKJddnDX7"
    "+n6Di2KPiluw9IVOmmOk1x80qV0Shrgqoespx+C1ra5omIK/RN2Raf7K5LgaoYOqGHmviacNP"
    "kFSXOKIOz4cAmWoorEdlHmoWzHN64qvj4Qfh666TuM5pkoxXjWwt1nEn9kxsTd8kB9+Hf7ouM"
    "54TqNDtlhdLI6xaO9aCXpXg7A+2B0iK1bFtOq8vaQY7NCDQvPnvxEFsNJ4lyogu4SbCDEJejX"
    "BxOgQ== "
    "Comment goes here")

VULNERABLE_DSA_KEY = (
    "ssh-dss "
    "AAAAB3NzaC1kc3MAAACBANy0bpKtBS+iTLKSMYGmQCxruTuThyn/RyNT/B3LoNNeQmS/LBoQK"
    "HzQmJDMKOr5TdvooOB3i5wZ0gA868U88WjHJmSQklodOEDeV3xPQmh0hdJm6pd+DrLCeqxhuJ"
    "LjDuNUahAqVPD8GJWuL88nX3fkjRTsNVUl6O7MbFHf8XyBAAAAFQDpRTNzw5oudxJtW3K8nvh"
    "COLvZ8wAAAIAVyC46KCN2f5HzMHQceuvNRo+tbGe/SWuX5qwFvyMYjIAuVeW75f+Xi24VgeYZ"
    "Wn2Da6ieDk0px8ossDx4Qb6AECTPfbVge/D/DtqYxJFaj6zFekCKJXs7TogxIdLHCwcL9M8a0"
    "X/FVgnPj/DKlHvMkzj4u3IfXKf7bOlBntm0rgAAAIBANST6hbRklJCGPZdC1j24LsDiDmWh+M"
    "wIhjGj0bjtqjs/B1a7NOqi3ZOjdU2aoyrY2oAo1nF4VDE9uPMj8+LUZV1sw9vfwUTGnzBxFgy"
    "rV32YhdWvV/mwEMCWiy6+rgCOZlswJ4nfuxF4llnYTsc6c7h1s7jYIMI+K6dZgATAEw== "
    "Comment goes here")


class TestSSHKey(TestCaseWithFactory):
    """Test `ISSHKey`."""

    layer = DatabaseFunctionalLayer

    def test_getFullKeyText_for_rsa_key(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            key = self.factory.makeSSHKey(person, SSHKeyType.RSA)
        expected = "ssh-rsa %s %s" % (key.keytext, key.comment)
        self.assertEqual(expected, key.getFullKeyText())

    def test_getFullKeyText_for_dsa_key(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            key = self.factory.makeSSHKey(person, SSHKeyType.DSA)
        expected = "ssh-dss %s %s" % (key.keytext, key.comment)
        self.assertEqual(expected, key.getFullKeyText())


class TestSSHKeySet(TestCaseWithFactory):

    """Test `ISSHKeySet`."""

    layer = DatabaseFunctionalLayer

    def test_sends_notification_by_default(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            keyset = getUtility(ISSHKeySet)
            keyset.new(person, "ssh-rsa keytext comment")
            [email] = pop_notifications()
        self.assertEqual(
            email['Subject'], "New SSH key added to your account.")
        self.assertThat(
            email.get_payload(),
            StartsWith("The SSH key 'comment' has been added to your account.")
        )

    def test_does_not_send_notifications(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            keyset = getUtility(ISSHKeySet)
            keyset.new(person, "ssh-rsa keytext comment",
                       send_notification=False)
            self.assertEqual([], pop_notifications())

    def test_raises_on_vulnerable_keys(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            keyset = getUtility(ISSHKeySet)
            for key in (VULNERABLE_DSA_KEY, VULNERABLE_RSA_KEY):
                self.assertRaises(SSHKeyCompromisedError,
                                  keyset.new, person, key,)

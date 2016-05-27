# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SSHKey."""

__metaclass__ = type

from testtools.matchers import StartsWith
from zope.component import getUtility

from lp.registry.interfaces.ssh import (
    ISSHKeySet,
    SSH_TEXT_TO_KEY_TYPE,
    SSHKeyAdditionError,
    SSHKeyCompromisedError,
    SSHKeyType,
    )
from lp.testing import (
    admin_logged_in,
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

    def test_getByPersonAndKeyText_retrieves_target_key(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            key = self.factory.makeSSHKey(person)
            keytext = key.getFullKeyText()

            results = getUtility(ISSHKeySet).getByPersonAndKeyText(
                person, keytext)
            self.assertEqual([key], list(results))

    def test_getByPersonAndKeyText_raises_on_invalid_key_type(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            invalid_keytext = 'foo bar baz'
            keyset = getUtility(ISSHKeySet)
            self.assertRaises(
                SSHKeyAdditionError,
                keyset.getByPersonAndKeyText,
                person, invalid_keytext
            )

    def test_getByPersonAndKeyText_raises_on_invalid_key_data(self):
        person = self.factory.makePerson()
        with person_logged_in(person):
            invalid_keytext = 'glorp!'
            keyset = getUtility(ISSHKeySet)
            self.assertRaises(
                SSHKeyAdditionError,
                keyset.getByPersonAndKeyText,
                person, invalid_keytext
            )

    def test_can_retrieve_keys_by_id(self):
        keyset = getUtility(ISSHKeySet)
        person = self.factory.makePerson()
        with person_logged_in(person):
            new_key = self.factory.makeSSHKey(person)

        retrieved_new_key = keyset.getByID(new_key.id)

        self.assertEqual(retrieved_new_key, new_key)

    def test_can_add_new_key(self):
        keyset = getUtility(ISSHKeySet)
        person = self.factory.makePerson()
        keytype = 'ssh-rsa'
        keytext = 'ThisIsAFakeSSHKey'
        comment = 'This is a key comment.'
        full_key = ' '.join((keytype, keytext, comment))
        with person_logged_in(person):
            key = keyset.new(person, full_key)
            self.assertEqual([key], list(person.sshkeys))
            self.assertEqual(SSH_TEXT_TO_KEY_TYPE[keytype], key.keytype)
            self.assertEqual(keytext, key.keytext)
            self.assertEqual(comment, key.comment)

    def test_new_raises_KeyAdditionError_on_bad_key_data(self):
        person = self.factory.makePerson()
        keyset = getUtility(ISSHKeySet)
        self.assertRaises(
            SSHKeyAdditionError,
            keyset.new,
            person, 'thiskeyhasnospaces'
        )
        self.assertRaises(
            SSHKeyAdditionError,
            keyset.new,
            person, 'bad_key_type keytext comment'
        )
        self.assertRaises(
            SSHKeyAdditionError,
            keyset.new,
            person, None
        )

    def test_can_retrieve_keys_for_multiple_people(self):
        with admin_logged_in():
            person1 = self.factory.makePerson()
            person1_key1 = self.factory.makeSSHKey(person1)
            person1_key2 = self.factory.makeSSHKey(person1)
            person2 = self.factory.makePerson()
            person2_key1 = self.factory.makeSSHKey(person2)

        keyset = getUtility(ISSHKeySet)
        keys = keyset.getByPeople([person1, person2])
        self.assertEqual(3, keys.count())
        self.assertContentEqual(
            [person1_key1, person1_key2, person2_key1], keys)

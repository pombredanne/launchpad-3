# Copyright 2016 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for SSHKey."""

__metaclass__ = type

from lp.registry.interfaces.ssh import SSHKeyType
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


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

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

from zope.component import getUtility

from canonical.launchpad.testing.pages import (
    extract_text,
    find_tags_by_class,
    )
from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.registry.interfaces.ssh import ISSHKeySet
from lp.testing import TestCaseWithFactory


class TestCanonicalUrl(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        # The canonical URL of a GPG key is ssh-keys
        person = self.factory.makePerson()
        sshkey = self.factory.makeSSHKey(person)
        self.assertEqual(
            '%s/+ssh-keys/%s' % (
                canonical_url(person, rootsite='api'), sshkey.id),
            canonical_url(sshkey))


class TestSSHKeyView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_escaped_message_when_removing_key(self):
        """Confirm that messages are escaped when removing keys."""
        person = self.factory.makePerson()
        public_key = "ssh-rsa %s x<script>alert()</script>example.com" % (
            self.getUniqueString())
        # Add the key for the user here,
        # since we only care about testing removal.
        getUtility(ISSHKeySet).new(person, public_key)
        browser = self.getUserBrowser(
            canonical_url(person) + '/+editsshkeys', user=person)
        browser.getControl('Remove').click()
        msg = 'Key "x&lt;script&gt;alert()&lt;/script&gt;example.com" removed'
        self.assertEqual(
            extract_text(find_tags_by_class(browser.contents, 'message')[0]),
            msg)

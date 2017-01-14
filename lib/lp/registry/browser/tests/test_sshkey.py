# Copyright 2010-2017 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

from unittest import skipUnless

from zope.component import getUtility

from lp.registry.interfaces.ssh import ISSHKeySet
from lp.services.osutils import find_on_path
from lp.services.webapp import canonical_url
from lp.testing import (
    login_person,
    person_logged_in,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.pages import (
    extract_text,
    find_tags_by_class,
    get_feedback_messages,
    setupBrowserFreshLogin,
    )
from lp.testing.views import create_initialized_view


class TestCanonicalUrl(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_canonical_url(self):
        # The canonical URL of a GPG key is ssh-keys
        person = self.factory.makePerson()
        with person_logged_in(person):
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
        url = '%s/+editsshkeys' % canonical_url(person)
        public_key = "ssh-rsa %s x<script>alert()</script>example.com" % (
            self.getUniqueString())
        with person_logged_in(person):
            # Add the key for the user here,
            # since we only care about testing removal.
            getUtility(ISSHKeySet).new(person, public_key)
            browser = setupBrowserFreshLogin(person)
            browser.open(url)
            browser.getControl('Remove').click()
            msg = (
                'Key "x&lt;script&gt;alert()&lt;/script&gt;example.com" '
                'removed')
            self.assertEqual(
                extract_text(
                    find_tags_by_class(browser.contents, 'message')[0]),
                msg)

    def test_edit_ssh_keys_login_redirect(self):
        """+editsshkeys should redirect to force you to re-authenticate."""
        person = self.factory.makePerson()
        login_person(person)
        view = create_initialized_view(person, "+editsshkeys")
        response = view.request.response
        self.assertEqual(302, response.getStatus())
        expected_url = (
            '%s/+editsshkeys/+login?reauth=1' % canonical_url(person))
        self.assertEqual(expected_url, response.getHeader('location'))

    @skipUnless(find_on_path("ssh-vulnkey"), "requires ssh-vulnkey")
    def test_blacklisted_keys(self):
        """+editsshkeys refuses keys known to be compromised."""
        person = self.factory.makePerson()
        url = '%s/+editsshkeys' % canonical_url(person)
        compromised_key = (
            'ssh-dss AAAAB3NzaC1kc3MAAACBAMDMAwIgYxgquosN4grBbVJCuyLXODSkY2x4/'
            'jYxUPuj0iUwVl/nTdZ2hitv7DE5dshFGUNm4sizXZoX7/u2Y68av2VHwlIkbQ52qM'
            '3ltiPXvS7uP4RjKUEZr+6l6BjohEmnlhhnLdbNy4kj4xTQizE9QSS999PBvQ3csxk'
            'OSZNXAAAAFQDZpXHMZqsqy8s0JxTQPg256XEjtwAAAIEAszRf/KwyKHGGTdbQUjOx'
            'dfyngk2Fol/1fYRtSGpkooAOMTxfWyOZiEigv6Zqt4VAmXuFpSM/DU0tNrbBPvzKV'
            'MkIXwoOfnWimf3ozGuoIxYYLao5pgGqS0dNADOOIaXo6YiVkIYi2YL/7ISq3WLdCe'
            'qy9mSZr9z8esdNfW5SiWsAAACAdPqgY1eCyEfxWCEH+Nz4bsig1DkgdZX27QMzW27'
            'xJdN03GPUABA5HSRHY/QwvpgD+2PlwNf44ceiWEgcPToyWd/7koPoDga8im/B+ui5'
            'j2PQr++prQCa849UMk6Ol9kZWjvNMvk1gM9Rw732DK0FSj0qzk83iK4eqfrZIk3u1'
            'a4= maddog39@ubuntu')
        with person_logged_in(person):
            browser = setupBrowserFreshLogin(person)
            browser.open(url)
            browser.getControl(name='sshkey').value = compromised_key
            browser.getControl('Import Public Key').click()
            expected_message = (
                'This key is known to be compromised due to a security flaw '
                'in the software used to generate it, so it will not be '
                'accepted by Launchpad. See the full Security Notice for '
                'further information and instructions on how to generate '
                'another key.')
            self.assertEqual(
                [expected_message], get_feedback_messages(browser.contents))

# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test DKIM-signed messages"""

__metaclass__ = type

import logging
from StringIO import StringIO

import dkim
import dns.resolver

from canonical.testing.layers import DatabaseFunctionalLayer
from lp.services.features.testing import FeatureFixture
from lp.services.mail import incoming
from lp.services.mail.incoming import authenticateEmail
from lp.services.mail.interfaces import IWeaklyAuthenticatedPrincipal
from lp.services.mail.signedmessage import signed_message_from_string
from lp.testing import TestCaseWithFactory

# sample private key made with 'openssl genrsa' and public key using 'openssl
# rsa -pubout'.  Not really the key for canonical.com ;-)
sample_privkey = """\
-----BEGIN RSA PRIVATE KEY-----
MIIBOwIBAAJBANmBe10IgY+u7h3enWTukkqtUD5PR52Tb/mPfjC0QJTocVBq6Za/
PlzfV+Py92VaCak19F4WrbVTK5Gg5tW220MCAwEAAQJAYFUKsD+uMlcFu1D3YNaR
EGYGXjJ6w32jYGJ/P072M3yWOq2S1dvDthI3nRT8MFjZ1wHDAYHrSpfDNJ3v2fvZ
cQIhAPgRPmVYn+TGd59asiqG1SZqh+p+CRYHW7B8BsicG5t3AiEA4HYNOohlgWan
8tKgqLJgUdPFbaHZO1nDyBgvV8hvWZUCIQDDdCq6hYKuKeYUy8w3j7cgJq3ih922
2qNWwdJCfCWQbwIgTY0cBvQnNe0067WQIpj2pG7pkHZR6qqZ9SE+AjNTHX0CIQCI
Mgq55Y9MCq5wqzy141rnxrJxTwK9ABo3IAFMWEov3g==
-----END RSA PRIVATE KEY-----
"""

sample_pubkey = """\
-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANmBe10IgY+u7h3enWTukkqtUD5PR52T
b/mPfjC0QJTocVBq6Za/PlzfV+Py92VaCak19F4WrbVTK5Gg5tW220MCAwEAAQ==
-----END PUBLIC KEY-----
"""

sample_dns = """\
k=rsa; \
p=MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBANmBe10IgY+u7h3enWTukkqtUD5PR52T\
b/mPfjC0QJTocVBq6Za/PlzfV+Py92VaCak19F4WrbVTK5Gg5tW220MCAwEAAQ=="""


plain_content = """\
From: Foo Bar <foo.bar@canonical.com>
Date: Fri, 1 Apr 2010 00:00:00 +1000
Subject: yet another comment
To: 1@bugs.staging.launchpad.net

  importance critical

Why isn't this fixed yet?"""


class TestDKIM(TestCaseWithFactory):
    """Messages can be strongly authenticated by DKIM."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Login with admin roles as we aren't testing access here.
        TestCaseWithFactory.setUp(self, 'admin@canonical.com')
        self._log_output = StringIO()
        handler = logging.StreamHandler(self._log_output)
        logger = logging.getLogger('mail-authenticate-dkim')
        logger.addHandler(handler)
        self.addCleanup(lambda: logger.removeHandler(handler))
        self.monkeypatch_dns()

    def fake_signing(self, plain_message, canonicalize=None):
        if canonicalize is None:
            canonicalize = (dkim.Relaxed, dkim.Relaxed)
        dkim_line = dkim.sign(plain_message,
            selector='example',
            domain='canonical.com',
            privkey=sample_privkey,
            debuglog=self._log_output,
            canonicalize=canonicalize)
        assert dkim_line[-1] == '\n'
        return dkim_line + plain_message

    def monkeypatch_dns(self):
        self._dns_responses = {}

        def my_lookup(name):
            try:
                return self._dns_responses[name]
            except KeyError:
                raise dns.resolver.NXDOMAIN()

        orig_dnstxt = dkim.dnstxt
        dkim.dnstxt = my_lookup

        def restore():
            dkim.dnstxt = orig_dnstxt

        self.addCleanup(restore)

    def get_dkim_log(self):
        return self._log_output.getvalue()

    def assertStronglyAuthenticated(self, principal, signed_message):
        if IWeaklyAuthenticatedPrincipal.providedBy(principal):
            self.fail('expected strong authentication; got weak:\n'
                + self.get_dkim_log() + '\n\n' + signed_message)

    def assertWeaklyAuthenticated(self, principal, signed_message):
        if not IWeaklyAuthenticatedPrincipal.providedBy(principal):
            self.fail('expected weak authentication; got strong:\n'
                + self.get_dkim_log() + '\n\n' + signed_message)

    def assertDkimLogContains(self, substring):
        l = self.get_dkim_log()
        if l.find(substring) == -1:
            self.fail("didn't find %r in log: %s" % (substring, l))

    def test_dkim_garbage_pubkey(self):
        signed_message = self.fake_signing(plain_content)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            'aothuaonu'
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        self.assertDkimLogContains('invalid format in _domainkey txt record')

    def test_dkim_disabled(self):
        """With disabling flag set, mail isn't trusted."""
        self.useFixture(FeatureFixture({
            'mail.dkim_authentication.disabled': 'true'}))
        # A test that would normally pass will now fail
        self.assertRaises(self.failureException,
            self.test_dkim_valid_strict)

    def test_dkim_valid_strict(self):
        signed_message = self.fake_signing(plain_content,
            canonicalize=(dkim.Simple, dkim.Simple))
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_valid(self):
        signed_message = self.fake_signing(plain_content)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_untrusted_signer(self):
        # Valid signature from an untrusted domain -> untrusted
        signed_message = self.fake_signing(plain_content)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        saved_domains = incoming._trusted_dkim_domains[:]

        def restore():
            incoming._trusted_dkim_domains = saved_domains

        self.addCleanup(restore)
        incoming._trusted_dkim_domains = []
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_signing_irrelevant(self):
        # It's totally valid for a message to be signed by a domain other than
        # that of the From-sender, if that domain is relaying the message.
        # However, we shouldn't then trust the purported sender, because they
        # might have just made it up rather than relayed it.
        tweaked_message = plain_content.replace('foo.bar@canonical.com',
            'steve.alexander@ubuntulinux.com')
        signed_message = self.fake_signing(tweaked_message)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        # should come from From, not the dkim signature
        self.assertEqual(principal.person.preferredemail.email,
            'steve.alexander@ubuntulinux.com')

    def test_dkim_changed_from_address(self):
        # If the address part of the message has changed, it's detected.
        #  We still treat this as weakly authenticated by the purported
        # From-header sender, though perhaps in future we would prefer
        # to reject these messages.
        signed_message = self.fake_signing(plain_content)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        fiddled_message = signed_message.replace(
            'From: Foo Bar <foo.bar@canonical.com>',
            'From: Carlos <carlos@canonical.com>')
        principal = authenticateEmail(
            signed_message_from_string(fiddled_message))
        self.assertWeaklyAuthenticated(principal, fiddled_message)
        # should come from From, not the dkim signature
        self.assertEqual(principal.person.preferredemail.email,
            'carlos@canonical.com')

    def test_dkim_changed_from_realname(self):
        # If the real name part of the message has changed, it's detected.
        signed_message = self.fake_signing(plain_content)
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        fiddled_message = signed_message.replace(
            'From: Foo Bar <foo.bar@canonical.com>',
            'From: Evil Foo <foo.bar@canonical.com>')
        principal = authenticateEmail(
            signed_message_from_string(fiddled_message))
        # We don't care about the real name for determining the principal.
        self.assertWeaklyAuthenticated(principal, fiddled_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_nxdomain(self):
        # If there's no DNS entry for the pubkey it should be handled
        # decently.
        signed_message = self.fake_signing(plain_content)
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_message_unsigned(self):
        # This is a degenerate case: a message with no signature is
        # treated as weakly authenticated.
        # The library doesn't log anything if there's no header at all.
        principal = authenticateEmail(
            signed_message_from_string(plain_content))
        self.assertWeaklyAuthenticated(principal, plain_content)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')

    def test_dkim_body_mismatch(self):
        # The message has a syntactically valid DKIM signature that
        # doesn't actually correspond to what was signed.  We log
        # something about this but we don't want to drop the message.
        signed_message = self.fake_signing(plain_content)
        signed_message += 'blah blah'
        self._dns_responses['example._domainkey.canonical.com.'] = \
            sample_dns
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertWeaklyAuthenticated(principal, signed_message)
        self.assertEqual(principal.person.preferredemail.email,
            'foo.bar@canonical.com')
        self.assertDkimLogContains('body hash mismatch')

    def test_dkim_signed_by_other_address(self):
        # If the message is From one of a person's addresses, and the Sender
        # corresponds to another, and there is a DKIM signature for the Sender
        # domain, this is valid - see bug 643223.  For this to be a worthwhile
        # test  we need the two addresses to be in different domains.   It
        # will be signed by canonical.com, so make that the sender.
        person = self.factory.makePerson(
            email='dkimtest@canonical.com',
            name='dkimtest',
            displayname='DKIM Test')
        self.factory.makeEmail(
            person=person,
            address='dkimtest@example.com')
        self._dns_responses['example._domainkey.canonical.com.'] = sample_dns
        tweaked_message = (
            "Sender: dkimtest@canonical.com\n" + plain_content.replace(
                "From: Foo Bar <foo.bar@canonical.com>",
                "From: DKIM Test <dkimtest@example.com>"))
        signed_message = self.fake_signing(tweaked_message)
        principal = authenticateEmail(
            signed_message_from_string(signed_message))
        self.assertStronglyAuthenticated(principal, signed_message)

# Copyright 2009-2015 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""`PPAKeyGenerator` script class tests."""

__metaclass__ = type

from zope.component import getUtility

from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.interfaces.person import IPersonSet
from lp.services.propertycache import get_property_cache
from lp.services.scripts.base import LaunchpadScriptFailure
from lp.soyuz.interfaces.archive import IArchiveSet
from lp.soyuz.scripts.ppakeygenerator import PPAKeyGenerator
from lp.testing import TestCase
from lp.testing.faketransaction import FakeTransaction
from lp.testing.layers import LaunchpadZopelessLayer


class TestPPAKeyGenerator(TestCase):
    layer = LaunchpadZopelessLayer

    def _fixArchiveForKeyGeneration(self, archive):
        """Override the given archive distribution to 'ubuntutest'.

        This is necessary because 'ubuntutest' is the only distribution in
        the sampledata that contains a usable publishing configuration.
        """
        ubuntutest = getUtility(IDistributionSet).getByName('ubuntutest')
        archive.distribution = ubuntutest

    def _getKeyGenerator(self, archive_reference=None, txn=None):
        """Return a `PPAKeyGenerator` instance.

        Monkey-patch the script object with a fake transaction manager
        and also make it use an alternative (fake and lighter) procedure
        to generate keys for each PPA.
        """
        test_args = []

        if archive_reference is not None:
            test_args.extend(['-A', archive_reference])

        key_generator = PPAKeyGenerator(
            name='ppa-generate-keys', test_args=test_args)

        if txn is None:
            txn = FakeTransaction()
        key_generator.txn = txn

        def fake_key_generation(archive):
            a_key = getUtility(IGPGKeySet).get(1)
            archive.signing_key_fingerprint = a_key.fingerprint
            archive.signing_key_owner = a_key.owner
            del get_property_cache(archive).signing_key

        key_generator.generateKey = fake_key_generation

        return key_generator

    def testArchiveNotFound(self):
        """Raises an error if the specified archive does not exist."""
        key_generator = self._getKeyGenerator(archive_reference='~biscuit')
        self.assertRaisesWithContent(
            LaunchpadScriptFailure,
            "No archive named '~biscuit' could be found.",
            key_generator.main)

    def testPPAAlreadyHasSigningKey(self):
        """Raises an error if the specified PPA already has a signing_key."""
        cprov = getUtility(IPersonSet).getByName('cprov')
        a_key = getUtility(IGPGKeySet).get(1)
        cprov.archive.signing_key_fingerprint = a_key.fingerprint
        cprov.archive.signing_key_owner = a_key.owner

        key_generator = self._getKeyGenerator(
            archive_reference='~cprov/ubuntu/ppa')
        self.assertRaisesWithContent(
            LaunchpadScriptFailure,
            ("PPA for Celso Providelo already has a signing_key (%s)" %
             cprov.archive.signing_key.fingerprint),
            key_generator.main)

    def testGenerateKeyForASinglePPA(self):
        """Signing key generation for a single PPA.

        The 'signing_key' for the specified PPA is generated and
        the transaction is committed once.
        """
        cprov = getUtility(IPersonSet).getByName('cprov')
        self._fixArchiveForKeyGeneration(cprov.archive)

        self.assertTrue(cprov.archive.signing_key is None)

        txn = FakeTransaction()
        key_generator = self._getKeyGenerator(
            archive_reference='~cprov/ubuntutest/ppa', txn=txn)
        key_generator.main()

        self.assertTrue(cprov.archive.signing_key is not None)
        self.assertEquals(txn.commit_count, 1)

    def testGenerateKeyForAllPPA(self):
        """Signing key generation for all PPAs.

        The 'signing_key' for all 'pending-signing-key' PPAs are generated
        and the transaction is committed once for each PPA.
        """
        archives = list(getUtility(IArchiveSet).getPPAsPendingSigningKey())

        for archive in archives:
            self._fixArchiveForKeyGeneration(archive)
            self.assertTrue(archive.signing_key is None)

        txn = FakeTransaction()
        key_generator = self._getKeyGenerator(txn=txn)
        key_generator.main()

        for archive in archives:
            self.assertTrue(archive.signing_key is not None)

        self.assertEquals(txn.commit_count, len(archives))

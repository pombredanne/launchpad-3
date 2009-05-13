# Copyright 2008 Canonical Ltd.  All rights reserved.
"""`PPAKeyGenerator` script class tests."""

__metaclass__ = type

import unittest

from zope.component import getUtility

from lp.soyuz.interfaces.archive import IArchiveSet
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.gpg import IGPGKeySet
from lp.registry.interfaces.person import IPersonSet
from canonical.launchpad.scripts.base import LaunchpadScriptFailure
from lp.soyuz.scripts.ppakeygenerator import PPAKeyGenerator
from canonical.launchpad.testing import TestCase
from canonical.testing import LaunchpadZopelessLayer


class TestPPAKeyGenerator(TestCase):
    layer = LaunchpadZopelessLayer

    def _getFakeZTM(self):
        """Return an instrumented `ZopeTransactionManager`-like object.

        I does nothing apart counting the number of commits issued.

        The result is stored in the 'number_of_commits'.
        """
        self.number_of_commits = 0

        def commit_called():
            self.number_of_commits += 1

        class FakeZTM:
            def commit(self):
                commit_called()
            def begin(self):
                pass

        return FakeZTM()

    def _fixArchiveForKeyGeneration(self, archive):
        """Override the given archive distribution to 'ubuntutest'.

        This is necessary because 'ubuntutest' is the only distribution in
        the sampledata that contains a usable publishing configuration.
        """
        ubuntutest = getUtility(IDistributionSet).getByName('ubuntutest')
        archive.distribution = ubuntutest

    def _getKeyGenerator(self, ppa_owner_name=None):
        """Return a `PPAKeyGenerator` instance.

        Monkey-patch the script object transaction manager (see
        `_getFakeZTM`) and also to use a alternative (fake and lighter)
        procedure to generate keys for each PPA.
        """
        test_args = []

        if ppa_owner_name is not None:
            test_args.extend(['-p', ppa_owner_name])

        key_generator = PPAKeyGenerator(
            name='ppa-generate-keys', test_args=test_args)

        key_generator.txn = self._getFakeZTM()

        def fake_key_generation(archive):
            a_key = getUtility(IGPGKeySet).get(1)
            archive.signing_key = a_key

        key_generator.generateKey = fake_key_generation

        return key_generator

    def testPersonNotFound(self):
        """Raises an error if the specified person does not exist."""
        key_generator = self._getKeyGenerator(ppa_owner_name='biscuit')
        self.assertRaisesWithContent(
            LaunchpadScriptFailure,
            "No person named 'biscuit' could be found.",
            key_generator.main)

    def testPersonHasNoPPA(self):
        """Raises an error if the specified person does not have a PPA. """
        key_generator = self._getKeyGenerator(ppa_owner_name='name16')
        self.assertRaisesWithContent(
            LaunchpadScriptFailure,
            "Person named 'name16' has no PPA.",
            key_generator.main)

    def testPPAAlreadyHasSigningKey(self):
        """Raises an error if the specified PPA already has a signing_key."""
        cprov = getUtility(IPersonSet).getByName('cprov')
        a_key = getUtility(IGPGKeySet).get(1)
        cprov.archive.signing_key = a_key

        key_generator = self._getKeyGenerator(ppa_owner_name='cprov')
        self.assertRaisesWithContent(
            LaunchpadScriptFailure,
            ("PPA for Celso Providelo already has a signing_key (%s)" %
             cprov.archive.signing_key.fingerprint) ,
            key_generator.main)

    def testGenerateKeyForASinglePPA(self):
        """Signing key generation for a single PPA.

        The 'signing_key' for the specified PPA is generated and
        the transaction is committed once.
        """
        cprov = getUtility(IPersonSet).getByName('cprov')
        self._fixArchiveForKeyGeneration(cprov.archive)

        self.assertTrue(cprov.archive.signing_key is None)

        key_generator = self._getKeyGenerator(ppa_owner_name='cprov')
        key_generator.main()

        self.assertTrue(cprov.archive.signing_key is not None)
        self.assertEquals(self.number_of_commits, 1)

    def testGenerateKeyForAllPPA(self):
        """Signing key generation for all PPAs.

        The 'signing_key' for all 'pending-signing-key' PPAs are generated
        and the transaction is committed once for each PPA.
        """
        archives = list(getUtility(IArchiveSet).getPPAsPendingSigningKey())

        for archive in archives:
            self._fixArchiveForKeyGeneration(archive)
            self.assertTrue(archive.signing_key is None)

        key_generator = self._getKeyGenerator()
        key_generator.main()

        for archive in archives:
            self.assertTrue(archive.signing_key is not None)

        self.assertEquals(self.number_of_commits, len(archives))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

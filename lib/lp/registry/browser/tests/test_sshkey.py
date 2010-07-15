# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for GPG key on the web."""

__metaclass__ = type

import unittest

from canonical.launchpad.webapp import canonical_url
from canonical.testing.layers import DatabaseFunctionalLayer
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


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


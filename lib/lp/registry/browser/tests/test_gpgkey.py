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
        # The canonical URL of a GPG key is ???
        person = self.factory.makePerson()
        gpgkey = self.factory.makeGPGKey(person)
        url = canonical_url(gpgkey)
        self.assertEqual('???', url)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

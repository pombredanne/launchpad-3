# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test publisher configs handling."""

__metaclass__ = type

from lp.archivepublisher.config import getPubConfig
from lp.testing import TestCaseWithFactory
from lp.testing.layers import ZopelessDatabaseLayer


class TestGetPubConfig(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_getPubConfig_returns_None_if_no_publisherconfig_found(self):
        archive = self.factory.makeDistribution(no_pubconf=True).main_archive
        self.assertEqual(None, getPubConfig(archive))

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature settings coming from the database"""


__metaclass__ = type

from canonical.testing import layers
from lp.services.features.model import (
    FeatureFlag,
    getFeatureStore,
    )
from lp.testing import TestCase


class TestFeatureModel(TestCase):

    layer = layers.DatabaseFunctionalLayer

    def test_defaultEmptyCollection(self):
        # there are no settings in the sampledata
        store = getFeatureStore()
        self.assertTrue(store.find(FeatureFlag).is_empty())

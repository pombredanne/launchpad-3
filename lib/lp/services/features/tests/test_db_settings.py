# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for feature settings coming from the database"""


from __future__ import with_statement
__metaclass__ = type

import testtools

from canonical.testing import layers
from lp.services.features import (
    settings,
    )
from lp.services.features.model import (
    FeatureFlag,
    FeatureFlagCollection,
    )


class TestFeatureModel(testtools.TestCase):

    layer = layers.DatabaseFunctionalLayer

    def test_defaultEmptyCollection(self):
        # there are no settings in the sampledata
        coll = FeatureFlagCollection()
        self.assertTrue(coll.select().is_empty())

    def test_getSetFlags(self):
        # test connection to Storm is sane
        flag = FeatureFlag(
            scope=u'beta_user',
            flag=u'notification.global.text',
            value=u'\N{SNOWMAN} stormy Launchpad weather ahead',
            priority=100)
        coll = FeatureFlagCollection()
        self.assertFalse(coll.select().is_empty())


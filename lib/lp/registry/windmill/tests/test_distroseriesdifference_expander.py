# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

import transaction

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.windmill.testing import constants
from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.services.features.model import FeatureFlag, getFeatureStore
from lp.testing import WindmillTestCase


class TestDistroSeriesDifferenceExtraJS(WindmillTestCase):
    """Each listed source package can be expanded for extra information."""

    layer = RegistryWindmillLayer

    def setUp(self):
        """Enable the feature and populate with data."""
        super(TestDistroSeriesDifferenceExtraJS, self).setUp()
        # First just ensure that the feature is enabled.
        getFeatureStore().add(FeatureFlag(
            scope=u'default', flag=u'soyuz.derived-series-ui.enabled',
            value=u'on', priority=1))

        # Setup the difference record.
        self.diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foo", versions=dict(
                derived='1.15-2ubuntu1derilucid2', parent='1.17-1'))
        transaction.commit()

        self.package_diffs_url = (
            canonical_url(self.diff.derived_series) + '/+localpackagediffs')

    def test_diff_extra_details_available(self):
        """A successful request for the extra info updates the display."""
        self.client.open(url=self.package_diffs_url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.client.click(link=u'foo')
        self.client.waits.forElement(
            classname=u'diff-extra', timeout=constants.FOR_ELEMENT)


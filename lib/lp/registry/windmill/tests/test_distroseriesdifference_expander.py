# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility

import transaction

from canonical.launchpad.webapp.publisher import canonical_url
from canonical.launchpad.windmill.testing import constants
from canonical.launchpad.windmill.testing import lpuser
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import IDistroSeriesDifferenceSource
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

    def test_diff_extra_details_blacklisting(self):
        """A successful request for the extra info updates the display."""
        #login_person(self.diff.owner, 'test', self.client)
        lpuser.FOO_BAR.ensure_login(self.client)
        self.client.open(url=self.package_diffs_url)
        self.client.waits.forPageLoad(timeout=constants.PAGE_LOAD)
        self.client.click(link=u'foo')
        self.client.waits.forElement(
            classname=u'diff-extra', timeout=constants.FOR_ELEMENT)

        self.client.click(id=u'field.blacklist_options.1')
        self.client.waits.forElementProperty(
            option=u'enabled', id=u'field.blacklist_options.1')

        # Reload the diff and ensure it's been updated.
        transaction.commit()
        diff_source = getUtility(IDistroSeriesDifferenceSource)
        diff_reloaded = diff_source.getByDistroSeriesAndName(
            self.diff.derived_series, 'foo')
        self.assertEqual(
            DistroSeriesDifferenceStatus.BLACKLISTED_ALWAYS,
            diff_reloaded.status)

        # Now set it back so that it's not blacklisted.
        self.client.click(id=u'field.blacklist_options.0')
        self.client.waits.forElementProperty(
            option=u'enabled', id=u'field.blacklist_options.0')
        transaction.commit()
        diff_reloaded = diff_source.getByDistroSeriesAndName(
            self.diff.derived_series, 'foo')
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            diff_reloaded.status)

        # Finally, add a comment to this difference.
        self.client.click(link=u'Add comment')
        self.client.click(
            xpath=u"//div[@class='add-comment-placeholder foo']//textarea")
        self.client.type(
            xpath=u"//div[@class='add-comment-placeholder foo']//textarea",
            text=u"Here's a comment.")
        self.client.click(
            xpath=u"//div[@class='add-comment-placeholder foo']//button")
        self.client.waits.forElement(
            classname=u'boardComment', timeout=constants.FOR_ELEMENT)
        self.client.asserts.assertText(
            classname=u'boardCommentBody', validator=u"Here's a comment.")

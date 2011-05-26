# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility

import transaction

from canonical.launchpad.webapp.publisher import canonical_url
from lp.registry.enum import DistroSeriesDifferenceStatus
from lp.registry.interfaces.distroseriesdifference import IDistroSeriesDifferenceSource
from lp.registry.windmill.testing import RegistryWindmillLayer
from lp.services.features.model import FeatureFlag, getFeatureStore
from lp.testing import WindmillTestCase
from lp.testing.windmill import (
    constants,
    lpuser,
    )


class TestDistroSeriesDifferenceExtraJS(WindmillTestCase):
    """Each listed source package can be expanded for extra information."""

    layer = RegistryWindmillLayer

    def setUp(self):
        """Enable the feature and populate with data."""
        super(TestDistroSeriesDifferenceExtraJS, self).setUp()
        # First just ensure that the feature is enabled.
        getFeatureStore().add(FeatureFlag(
            scope=u'default', flag=u'soyuz.derived_series_ui.enabled',
            value=u'on', priority=1))

        # Setup the difference record.
        self.diff = self.factory.makeDistroSeriesDifference(
            source_package_name_str="foo", versions=dict(
                derived='1.15-2ubuntu1derilucid2', parent='1.17-1'))
        transaction.commit()

    def test_diff_extra_details_blacklisting(self):
        """A successful request for the extra info updates the display."""
        #login_person(self.diff.owner, 'test', self.client)
        client, start_url = self.getClientFor(
            '/+localpackagediffs', user=lpuser.FOO_BAR,
            base_url=canonical_url(self.diff.derived_series))
        client.click(link=u'foo')
        client.waits.forElement(
            classname=u'diff-extra', timeout=constants.FOR_ELEMENT)

        client.click(id=u'field.blacklist_options.1')
        client.waits.forElementProperty(
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
        client.click(id=u'field.blacklist_options.0')
        client.waits.forElementProperty(
            option=u'enabled', id=u'field.blacklist_options.0')
        transaction.commit()
        diff_reloaded = diff_source.getByDistroSeriesAndName(
            self.diff.derived_series, 'foo')
        self.assertEqual(
            DistroSeriesDifferenceStatus.NEEDS_ATTENTION,
            diff_reloaded.status)

        # Finally, add a comment to this difference.
        client.click(link=u'Add comment')
        client.click(
            xpath=u"//div[@class='add-comment-placeholder foo']//textarea")
        client.type(
            xpath=u"//div[@class='add-comment-placeholder foo']//textarea",
            text=u"Here's a comment.")
        client.click(
            xpath=u"//div[@class='add-comment-placeholder foo']//button")
        client.waits.forElement(
            classname=u'boardComment', timeout=constants.FOR_ELEMENT)
        client.asserts.assertText(
            classname=u'boardCommentBody', validator=u"Here's a comment.")

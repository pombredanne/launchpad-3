# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from zope.component import getUtility

from canonical.testing.layers import DatabaseFunctionalLayer
from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.browser.distribution import DistributionPublisherConfigView
from lp.testing import TestCaseWithFactory
from lp.testing.sampledata import LAUNCHPAD_ADMIN


class TestDistributionPublisherConfigView(TestCaseWithFactory):
    """Test `DistributionPublisherConfigView`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Create a test distribution.
        super(TestDistributionPublisherConfigView, self).setUp()
        self.distro = self.factory.makeDistribution()
        login(LAUNCHPAD_ADMIN)

        self.ROOT_DIR = u"rootdir/test"
        self.BASE_URL = u"http://base.url"
        self.COPY_BASE_URL = u"http://copybase.url"

    def test_empty_initial_values(self):
        # Test that the page will display empty field values with no
        # existing config set up.
        view = DistributionPublisherConfigView(
            self.distro, LaunchpadTestRequest())

        for value in view.initial_values:
            self.assertEqual(u"", value)

    def test_previous_initial_values(self):
        # Test that the initial values are the same as the ones in the
        # existing database record.
        pubconf = self.factory.makePublisherConfig(
            distribution=self.distro)

        view = DistributionPublisherConfigView(
            self.distro, LaunchpadTestRequest())

        self.assertEqual(pubconf.root_dir, view.initial_values["root_dir"])
        self.assertEqual(pubconf.base_url, view.initial_values["base_url"])
        self.assertEqual(
            pubconf.copy_base_url, view.initial_values["copy_base_url"])

    def _change_and_test_config(self):
        form = {
            'field.actions.save': 'save',
            'field.root_dir': self.ROOT_DIR,
            'field.base_url': self.BASE_URL,
            'field.copy_base_url': self.COPY_BASE_URL,
        }

        view = DistributionPublisherConfigView(
            self.distro, LaunchpadTestRequest(method='POST', form=form))
        view.initialize()

        config = getUtility(
            IPublisherConfigSet).getByDistribution(self.distro)

        self.assertEqual(self.ROOT_DIR, config.root_dir)
        self.assertEqual(self.BASE_URL, config.base_url)
        self.assertEqual(self.COPY_BASE_URL, config.copy_base_url)

    def test_add_new_config(self):
        # Test POSTing a new config.
        self._change_and_test_config()

    def test_change_existing_config(self):
        # Test POSTing to change existing config.
        pubconf = self.factory.makePublisherConfig(
            distribution=self.distro,
            root_dir=u"random",
            base_url=u"blah",
            copy_base_url=u"foo",
            )
        self._change_and_test_config()

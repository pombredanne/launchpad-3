# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

import soupmatchers
from zope.component import getUtility

from canonical.launchpad.ftests import login
from canonical.launchpad.webapp.servers import LaunchpadTestRequest
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.archivepublisher.interfaces.publisherconfig import IPublisherConfigSet
from lp.registry.browser.distribution import DistributionPublisherConfigView
from lp.registry.interfaces.distribution import IDistributionSet
from lp.testing import (
    login_celebrity,
    TestCaseWithFactory,
    )
from lp.testing.sampledata import LAUNCHPAD_ADMIN
from lp.testing.views import create_initialized_view


class TestDistributionPublisherConfigView(TestCaseWithFactory):
    """Test `DistributionPublisherConfigView`."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        # Create a test distribution.
        super(TestDistributionPublisherConfigView, self).setUp()
        self.distro = self.factory.makeDistribution(no_pubconf=True)
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


class TestDistroAddView(TestCaseWithFactory):
    """Test the +add page for a new distribution."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroAddView, self).setUp()
        self.owner = self.factory.makePerson()
        self.registrant = self.factory.makePerson()
        self.simple_user = self.factory.makePerson()

    def test_registrant_set_by_creation(self):
        # The registrant field should be set to the Person creating
        # the distribution.
        admin = login_celebrity('admin')
        distributionset = getUtility(IDistributionSet)
        creation_form = {
            'field.name': 'newbuntu',
            'field.displayname': 'newbuntu',
            'field.title': 'newbuntu',
            'field.summary': 'newbuntu',
            'field.description': 'newbuntu',
            'field.domainname': 'newbuntu',
            'field.members': self.simple_user.name,
            'field.actions.save': 'Save',
            }
        view = create_initialized_view(
            distributionset, '+add', principal=admin,
            method='POST', form=creation_form)
        distribution = distributionset.getByName('newbuntu')
        self.assertEqual(distribution.owner, admin)
        self.assertEqual(distribution.registrant, admin)


class TestDistroReassignView(TestCaseWithFactory):
    """Test the +reassign page for a new distribution."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestDistroReassignView, self).setUp()
        self.owner = self.factory.makePerson()
        self.registrant = self.factory.makePerson()
        self.simple_user = self.factory.makePerson()

    def test_reassign_distro_change_owner_not_registrant(self):
        # Reassigning a distribution should not change the registrant.
        admin = login_celebrity('admin')
        distribution = self.factory.makeDistribution(
            name="boobuntu", owner=self.owner, registrant=self.registrant)
        reassign_form = {
            'field.owner': self.simple_user.name,
            'field.existing': 'existing',
            'field.actions.change': 'Change',
            }
        view = create_initialized_view(
            distribution, '+reassign', principal=admin,
            method='POST', form=reassign_form)
        self.assertEqual(distribution.owner, self.simple_user)
        self.assertEqual(distribution.registrant, self.registrant)

    def test_reassign_distro_page_title(self):
        # Reassign should say maintainer instead of owner.
        admin = login_celebrity('admin')
        distribution = self.factory.makeDistribution(
            name="boobuntu", owner=self.owner, registrant=self.registrant)
        view = create_initialized_view(
            distribution, '+reassign', principal=admin, method='GET')
        header_match = soupmatchers.HTMLContains(
            soupmatchers.Tag(
                'Header should say maintainer (not owner)', 'h1',
                text='Change the maintainer of Boobuntu'))
        self.assertThat(view.render(), header_match)

# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import (
    person_logged_in,
    TestCaseWithFactory,
    )


class TestOmitTargetedParameter(TestCaseWithFactory):
    """Test all values for the omit_targeted search parameter."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestOmitTargetedParameter, self).setUp()
        self.owner = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.distro = self.factory.makeDistribution(name='mebuntu')
        self.release = self.factory.makeDistroSeries(
            name='inkanyamba', distribution=self.distro)
        self.bug = self.factory.makeBugTask(target=self.release)
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def test_omit_targeted_old_default_true(self):
        response = self.webservice.named_get('/mebuntu/inkanyamba',
            'searchTasks', api_version='1.0').jsonBody()
        self.assertEqual(response['total_size'], 0)

    def test_omit_targeted_new_default_false(self):
        response = self.webservice.named_get('/mebuntu/inkanyamba',
            'searchTasks', api_version='devel').jsonBody()
        self.assertEqual(response['total_size'], 1)


class TestLinkedBlueprintsParameter(TestCaseWithFactory):
    """Tests for the linked_blueprints parameter."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestLinkedBlueprintsParameter, self).setUp()
        self.owner = self.factory.makePerson()
        with person_logged_in(self.owner):
            self.product = self.factory.makeProduct()
        self.bug = self.factory.makeBugTask(target=self.product)
        self.webservice = LaunchpadWebServiceCaller(
            'launchpad-library', 'salgado-change-anything')

    def search(self, api_version, **kwargs):
        return self.webservice.named_get(
            '/%s' % self.product.name, 'searchTasks',
            api_version=api_version, **kwargs).jsonBody()

    def test_linked_blueprints_in_devel(self):
        # Searching for linked Blueprints works in the devel API.
        self.search("devel", linked_blueprints="Show all bugs")

    def test_linked_blueprints_in_devel_2(self):
        # The linked_blueprints is considered. An error is returned if its
        # value is not a member of BugBlueprintSearch.
        self.assertRaises(
            ValueError, self.search, "devel",
            linked_blueprints="Teabags!")

    def test_linked_blueprints_not_in_1_0(self):
        # Searching for linked Blueprints does not work in the 1.0 API. No
        # validation is performed for the linked_blueprints parameter, and
        # thus no error is returned when we pass rubbish.
        self.search("1.0", linked_blueprints="Teabags!")

    def test_linked_blueprints_not_in_beta(self):
        # Searching for linked Blueprints does not work in the beta API. No
        # validation is performed for the linked_blueprints parameter, and
        # thus no error is returned when we pass rubbish.
        self.search("beta", linked_blueprints="Teabags!")

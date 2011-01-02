# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Webservice unit tests related to Launchpad Bugs."""

__metaclass__ = type

from canonical.launchpad.ftests import login
from lp.testing import TestCaseWithFactory
from canonical.launchpad.testing.pages import LaunchpadWebServiceCaller
from canonical.testing.layers import DatabaseFunctionalLayer


class TestOmitTargetedParameter(TestCaseWithFactory):
    """Test all values for the omit_targeted search parameter."""
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        login('foo.bar@canonical.com')
        self.distro = self.factory.makeDistribution(name='mebuntu')
        self.release = self.factory.makeDistroRelease(name='inkanyamba',
            distribution=self.distro)
        self.bug = self.factory.makeBugTask(target=self.release)

        self.webservice = LaunchpadWebServiceCaller('launchpad-library',
            'salgado-change-anything')

    def test_omit_targeted_old_default_true(self):
        response = self.webservice.named_get('/mebuntu/inkanyamba',
            'searchTasks', api_version='1.0').jsonBody()
        self.assertEqual(response['total_size'], 0)

    def test_omit_targeted_new_default_false(self):
        response = self.webservice.named_get('/mebuntu/inkanyamba',
            'searchTasks', api_version='devel').jsonBody()
        self.assertEqual(response['total_size'], 1)

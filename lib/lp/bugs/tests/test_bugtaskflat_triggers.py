# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.model.bug import Bug
from lp.services.database.lpstorm import IStore
from lp.services.features.testing import FeatureFixture
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer


class TestBugTaskFlatTrigger(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestBugTaskFlatTrigger, self).setUp()
        self.useFixture(FeatureFixture(
            {'disclosure.allow_multipillar_private_bugs.enabled': 'true'}))

    def assertFlattened(self, bugtask):
        result = IStore(Bug).execute(
            "SELECT bugtask_flatten(?, true)", (bugtask.id,))
        self.assertIs(True, result.get_one()[0])

    def test_new_bug(self):
        task = self.factory.makeBugTask()
        self.assertFlattened(task)

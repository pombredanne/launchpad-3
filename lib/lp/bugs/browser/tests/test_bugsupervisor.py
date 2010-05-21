# Copyright10 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for bug supervisor views."""

__metaclass__ = type

import unittest

from lp.bugs.browser.bugsupervisor import BugSupervisorEditSchema
from lp.testing import login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view
from canonical.testing import DatabaseFunctionalLayer


class TestProductBugConfigurationView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductBugConfigurationView, self).setUp()
        self.owner = self.factory.makePerson(name='spat')
        self.product = self.factory.makeProduct(name="boing")
        login_person(self.owner)

    def test_view_attributes(self):
        view = create_initialized_view(
            self.product, name='+bugsupervisor')
        label = 'Edit bug supervisor for Boing'
        self.assertEqual(label, view.label)
        self.assertEqual(label, view.page_title)
        fields = ['bug_supervisor']
        self.assertEqual(fields, view.field_names)
        adapter, context = view.adapters.popitem()
        self.assertEqual(BugSupervisorEditSchema, adapter)
        self.assertEqual(self.product, context)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


# Copyright10 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version (see the file LICENSE).

"""Unit tests for bug configuration views."""

__metaclass__ = type

import unittest

from lp.testing import login_person, TestCaseWithFactory
from lp.testing.views import create_initialized_view
from canonical.testing import DatabaseFunctionalLayer


class TestProductBugConfigurationView(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestProductBugConfigurationView, self).setUp()
        self.product = self.factory.makeProduct()
        login_person(self.product.owner)

    def test_view_attributes(self):
        view = create_initialized_view(
            self.product, name='+configure-bugtracker')
        label = 'Configure bug tracker'
        self.assertEqual(label, view.label)
        fields = [
            'bug_supervisor', 'security_contact', 'bugtracker',
            'enable_bug_expiration', 'remote_product',
            'bug_reporting_guidelines']
        self.assertEqual(fields, view.field_names)


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

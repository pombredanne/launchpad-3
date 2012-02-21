# Copyright 2012 Canonical Ltd. This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage sharing."""

__metaclass__ = type

from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class ProductSharingViewTestCase(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_init(self):
        project = self.factory.makeProduct()
        view = create_initialized_view(project, '+sharing')
        self.assertEqual('Sharing', view.page_title)

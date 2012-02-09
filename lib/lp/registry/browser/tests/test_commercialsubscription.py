# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage commercial subscriptions."""

__metaclass__ = type

from lp.services.webapp.publisher import canonical_url
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class PersonVouchersViewTestCase(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_init(self):
        user = self.factory.makePerson()
        project = self.factory.makeProduct(owner=user)
        user_url = canonical_url(user)
        view = create_initialized_view(user, '+vouchers')
        self.assertEqual('Commercial subscription vouchers', view.page_title)
        self.assertEqual(user_url, view.next_url)
        self.assertEqual(view.cancel_url, view.next_url)

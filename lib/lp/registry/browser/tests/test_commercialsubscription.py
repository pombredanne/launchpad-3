# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test views that manage commercial subscriptions."""

__metaclass__ = type

from lp.services.salesforce.interfaces import ISalesforceVoucherProxy
from lp.services.salesforce.tests.proxy import TestSalesforceVoucherProxy
from lp.services.webapp.publisher import canonical_url
from lp.testing import (
    FakeAdapterMixin,
    login_celebrity,
    login_person,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.views import create_initialized_view


class PersonVouchersViewTestCase(FakeAdapterMixin, TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_init_without_vouchers_or_projects(self):
        # Thhe view provides common view properties, but the form is disabled.
        user = self.factory.makePerson()
        self.factory.makeProduct(owner=user)
        voucher_proxy = TestSalesforceVoucherProxy()
        self.registerUtility(voucher_proxy, ISalesforceVoucherProxy)
        user_url = canonical_url(user)
        view = create_initialized_view(user, '+vouchers')
        self.assertEqual('Commercial subscription vouchers', view.page_title)
        self.assertEqual(user_url, view.cancel_url)
        self.assertIs(None, view.next_url)
        self.assertEqual(0, len(view.redeemable_vouchers))
        self.assertEqual([], view.form_fields)

    def test_init_with_vouchers_and_projects(self):
        # The fields are setup when the user hase both vouchers and projects.
        user = self.factory.makePerson()
        login_person(user)
        voucher_proxy = TestSalesforceVoucherProxy()
        voucher_proxy.grantVoucher(
            user, user, user, 12)
        self.registerUtility(voucher_proxy, ISalesforceVoucherProxy)
        self.factory.makeProduct(owner=user)
        view = create_initialized_view(user, '+vouchers')
        self.assertEqual(1, len(view.redeemable_vouchers))
        self.assertEqual(
            ['project', 'voucher'], [f.__name__ for f in view.form_fields])

    def test_init_with_commercial_admin_with_vouchers(self):
        # The fields are setup if the commercial admin has vouchers.
        commercial_admin = login_celebrity('commercial_admin')
        voucher_proxy = TestSalesforceVoucherProxy()
        voucher_proxy.grantVoucher(
            commercial_admin, commercial_admin, commercial_admin, 12)
        self.registerUtility(voucher_proxy, ISalesforceVoucherProxy)
        view = create_initialized_view(commercial_admin, '+vouchers')
        self.assertEqual(1, len(view.redeemable_vouchers))
        self.assertEqual(
            ['project', 'voucher'], [f.__name__ for f in view.form_fields])

    def test_redeem_with_commercial_admin(self):
        # The fields are setup if the commercial admin has vouchers.
        commercial_admin = login_celebrity('commercial_admin')
        voucher_proxy = TestSalesforceVoucherProxy()
        voucher_id = voucher_proxy.grantVoucher(
            commercial_admin, commercial_admin, commercial_admin, 12)
        self.registerUtility(voucher_proxy, ISalesforceVoucherProxy)
        project = self.factory.makeProduct()
        form = {
            'field.project': project.name,
            'field.voucher': voucher_id,
            'field.actions.redeem': 'Redeem',
            }
        view = create_initialized_view(
            commercial_admin, '+vouchers', form=form)
        self.assertEqual([], view.errors)
        self.assertIsNot(None, project.commercial_subscription)
        self.assertEqual(0, len(view.redeemable_vouchers))
        self.assertEqual(
            0, len(view.form_fields['voucher'].field.vocabulary))
        self.assertEqual(
            0, len(view.widgets['voucher'].vocabulary))

    def test_redeem_twice_with_commercial_admin(self):
        # The fields are setup if the commercial admin has vouchers.
        commercial_admin = login_celebrity('commercial_admin')
        voucher_proxy = TestSalesforceVoucherProxy()
        voucher_id_1 = voucher_proxy.grantVoucher(
            commercial_admin, commercial_admin, commercial_admin, 12)
        voucher_id_2 = voucher_proxy.grantVoucher(
            commercial_admin, commercial_admin, commercial_admin, 12)
        self.registerUtility(voucher_proxy, ISalesforceVoucherProxy)
        project_1 = self.factory.makeProduct()
        project_2 = self.factory.makeProduct()
        form = {
            'field.project': project_1.name,
            'field.voucher': voucher_id_1,
            'field.actions.redeem': 'Redeem',
            }
        view = create_initialized_view(
            commercial_admin, '+vouchers', form=form)
        self.assertEqual([], view.errors)
        self.assertIsNot(None, project_1.commercial_subscription)
        self.assertEqual(1, len(view.redeemable_vouchers))
        form = {
            'field.project': project_2.name,
            'field.voucher': voucher_id_2,
            'field.actions.redeem': 'Redeem',
            }
        view = create_initialized_view(
            commercial_admin, '+vouchers', form=form)
        self.assertEqual([], view.errors)
        self.assertIsNot(None, project_2.commercial_subscription)
        self.assertEqual(0, len(view.redeemable_vouchers))

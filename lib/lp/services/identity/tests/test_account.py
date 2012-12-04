# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for `Account` objects."""

__metaclass__ = type
__all__ = []

from lp.services.identity.interfaces.account import (
    AccountStatus,
    AccountStatusError,
    can_transition_to_account_status,
    )
from lp.testing import (
    login_celebrity,
    TestCaseWithFactory,
    )
from lp.testing.layers import DatabaseFunctionalLayer


class TestAccount(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_account_repr_ansii(self):
        # Verify that ANSI displayname is ascii safe.
        distro = self.factory.makeAccount(u'\xdc-account')
        ignore, displayname, status_1, status_2 = repr(distro).rsplit(' ', 3)
        self.assertEqual("'\\xdc-account'", displayname)
        self.assertEqual('(Active account)>', '%s %s' % (status_1, status_2))

    def test_account_repr_unicode(self):
        # Verify that Unicode displayname is ascii safe.
        distro = self.factory.makeAccount(u'\u0170-account')
        ignore, displayname, status_1, status_2 = repr(distro).rsplit(' ', 3)
        self.assertEqual("'\\u0170-account'", displayname)

    def test_status_from_noccount(self):
        # The status may change from NOACCOUNT to ACTIVE.
        account = self.factory.makeAccount(status=AccountStatus.NOACCOUNT)
        login_celebrity('admin')
        for status in [AccountStatus.DEACTIVATED, AccountStatus.SUSPENDED]:
            self.assertFalse(
                can_transition_to_account_status(account.status, status))
            self.assertRaises(
                AccountStatusError, setattr, account, 'status', status)
        self.assertTrue(
            can_transition_to_account_status(
                account.status, AccountStatus.ACTIVE))
        account.status = AccountStatus.ACTIVE
        self.assertEqual(AccountStatus.ACTIVE, account.status)

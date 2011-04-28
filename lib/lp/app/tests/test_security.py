# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from canonical.testing.layers import ZopelessDatabaseLayer
from lp.app.security import AuthorizationBase
from lp.testing import TestCaseWithFactory
from lp.testing.fakemethod import FakeMethod


class FakeSecurityAdapter(AuthorizationBase):

    def __init__(self):
        super(FakeSecurityAdapter, self).__init__(None)
        self.checkAuthenticated = FakeMethod()
        self.checkUnauthenticated = FakeMethod()

    def getCallCounts(self):
        """Helper method to create a tuple of the call counts.

        :returns: A tuple of the call counts for
            (checkAuthenticated, checkUnauthenticated).
        """
        return (
            self.checkAuthenticated.call_count,
            self.checkUnauthenticated.call_count
            )

class TestAuthorizationBase(TestCaseWithFactory):

    layer = ZopelessDatabaseLayer

    def test_default_checkAccountAuthenticated_for_full_fledged_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkAuthenticated() when the given account can be adapted into an
        # IPerson.
        full_fledged_account = self.factory.makePerson().account
        adapter = FakeSecurityAdapter()
        adapter.checkAccountAuthenticated(full_fledged_account)
        self.assertEquals((1, 0), adapter.getCallCounts())

    def test_default_checkAccountAuthenticated_for_personless_account(self):
        # AuthorizationBase.checkAccountAuthenticated should delegate to
        # checkUnauthenticated() when the given account can't be adapted into
        # an IPerson.
        personless_account = self.factory.makeAccount('Test account')
        adapter = FakeSecurityAdapter()
        adapter.checkAccountAuthenticated(personless_account)
        self.assertEquals((0, 1), adapter.getCallCounts())

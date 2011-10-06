# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.browser.logintoken import (
    ClaimTeamView,
    ValidateEmailView,
    ValidateGPGKeyView,
    )
from canonical.launchpad.ftests import LaunchpadFormHarness
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.logintoken import ILoginTokenSet
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.testing import TestCaseWithFactory


class TestCancelActionOnLoginTokenViews(TestCaseWithFactory):
    """Test the 'Cancel' action of LoginToken views.

    These views have an action instead of a link to cancel because we want the
    token to be consumed (so it can't be used again) when the user hits
    Cancel.
    """
    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.person = self.factory.makePerson(name='test-user')
        self.email = removeSecurityProxy(self.person).preferredemail.email
        self.expected_next_url = 'http://127.0.0.1/~test-user'

    def test_ClaimTeamView(self):
        token = getUtility(ILoginTokenSet).new(
            self.person, self.email, self.email, LoginTokenType.TEAMCLAIM)
        self._testCancelAction(ClaimTeamView, token)

    def test_ValidateGPGKeyView(self):
        self.gpg_key = self.factory.makeGPGKey(self.person)
        token = getUtility(ILoginTokenSet).new(
            self.person, self.email, self.email, LoginTokenType.VALIDATEGPG,
            fingerprint=self.gpg_key.fingerprint)
        self._testCancelAction(ValidateGPGKeyView, token)

    def test_ValidateEmailView(self):
        token = getUtility(ILoginTokenSet).new(
            self.person, self.email, 'foo@example.com',
            LoginTokenType.VALIDATEEMAIL)
        self._testCancelAction(ValidateEmailView, token)

    def _testCancelAction(self, view_class, token):
        """Test the 'Cancel' action of the given view, using the given token.

        To test that the action works, we just submit the form with that
        action, check that there are no errors and make sure that the view's
        next_url is what we expect.
        """
        harness = LaunchpadFormHarness(token, view_class)
        harness.submit('cancel', {})
        actions = harness.view.actions.byname
        self.assertIn('field.actions.cancel', actions)
        self.assertEquals(actions['field.actions.cancel'].submitted(), True)
        self.assertEquals(harness.view.errors, [])
        self.assertEquals(harness.view.next_url, self.expected_next_url)


class TestClaimTeamView(TestCaseWithFactory):
    """Test the claiming of a team via login token."""

    layer = DatabaseFunctionalLayer

    def setUp(self):
        TestCaseWithFactory.setUp(self)
        self.claimer = self.factory.makePerson(name='claimer')
        self.claimee_email = 'claimee@example.com'
        self.claimee = self.factory.makePerson(
            name='claimee', email=self.claimee_email,
            email_address_status=EmailAddressStatus.NEW)

    def _claimToken(self, token):
        harness = LaunchpadFormHarness(token, ClaimTeamView)
        harness.submit('confirm', {})
        return [n.message for n in harness.request.notifications]

    def test_CannotClaimTwice(self):
        token1 = getUtility(ILoginTokenSet).new(
            requester=self.claimer, requesteremail=None,
            email=self.claimee_email, tokentype=LoginTokenType.TEAMCLAIM)
        token2 = getUtility(ILoginTokenSet).new(
            requester=self.claimer, requesteremail=None,
            email=self.claimee_email, tokentype=LoginTokenType.TEAMCLAIM)
        msgs = self._claimToken(token1)
        self.assertEquals([u'Team claimed successfully'], msgs)
        msgs = self._claimToken(token2)
        self.assertEquals(
            [u'claimee has already been converted to a team.'], msgs)

# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'AuthTokenSetNavigation',
    'AuthTokenView',
    'NewAccountView',
    'ResetAccountPasswordView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad import _
from canonical.launchpad.webapp import action, GetitemNavigation

from canonical.signon.browser.openidserver import OpenIDMixin
from canonical.launchpad.browser.logintoken import (
    LoginTokenView, NewUserAccountView, ResetPasswordView)
from canonical.launchpad.interfaces.account import IAccountSet
from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.launchpad import UnexpectedFormData
from lp.registry.interfaces.person import PersonCreationRationale


class AuthTokenSetNavigation(GetitemNavigation):

    usedfor = IAuthTokenSet


class AuthTokenView(LoginTokenView):
    """The default view for AuthToken.

    This view will check the token type and then redirect to the specific view
    for that type of token, if it's not yet a consumed token. We use this view
    so we don't have to add "+validateemail", "+newaccount", etc, on URLs we
    send by email.

    If this is a consumed token, then we simply display a page explaining that
    they got this token because they tried to do something that required email
    address confirmation, but that confirmation is already concluded.
    """
    PAGES = LoginTokenView.auth_token_pages


class AuthTokenOpenIDMixinView(OpenIDMixin):
    """An extended OpenID mixin to be used by other AuthToken views."""

    @property
    def has_openid_request(self):
        """Return True if there's an OpenID request in the user's session."""
        try:
            self.restoreRequestFromSession('token' + self.context.token)
        except UnexpectedFormData:
            return False
        return True

    def maybeCompleteOpenIDRequest(self):
        """Respond to a pending OpenID request if one is found.

        The OpenIDRequest is looked up in the session based on the
        login token ID.  If a request exists, the rendered OpenID
        response is returned.

        If no OpenID request is found, None is returned.
        """
        if not self.has_openid_request:
            return None
        return self.renderOpenIDResponse(self.createPositiveResponse())


class ResetAccountPasswordView(AuthTokenOpenIDMixinView, ResetPasswordView):

    @property
    def next_url(self):
        if self.has_openid_request:
            return None
        elif self.context.redirection_url is not None:
            return self.context.redirection_url
        else:
            return self.request.getApplicationURL()

    def reactivate(self, data):
        """Reactivate the account of this token.

        The regular view for resetting a user's password (ResetPasswordView)
        reactivates the person and account of the token, but this one runs on
        the OpenID server so it can't change the Person table, so we override
        reactivate() here to call IAccount.reactivate() instead of
        IPerson.reactivate().
        """
        emailaddress = getUtility(IEmailAddressSet).getByEmail(
            self.context.email)
        # Need to remove the security proxy of the account because at this
        # point the user is not logged in.
        naked_account = removeSecurityProxy(self.context.requester_account)
        naked_account.reactivate(
            comment="User reactivated the account using reset password.",
            password=data['password'],
            preferred_email=emailaddress)

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        super(ResetAccountPasswordView, self).continue_action.success(data)
        return self.maybeCompleteOpenIDRequest()


class NewAccountView(AuthTokenOpenIDMixinView, NewUserAccountView):
    """Page to create a new SSO account."""

    expected_token_types = (LoginTokenType.NEWPERSONLESSACCOUNT,)

    @property
    def next_url(self):
        if self.has_openid_request:
            # For OpenID requests we don't use self.next_url, so don't even
            # bother setting it.
            return None

        if self.context.redirection_url:
            return self.context.redirection_url
        else:
            return self.request.getApplicationURL()

    def _getCreationRationale(self):
        """Return the creation rationale that should be used for this account.

        If there's an OpenID request in the session and self.rpconfig is not
        None, we use the given trust_root to find out the creation rationale.
        If there's no OpenID request we use OWNER_CREATED_UNKNOWN_TRUSTROOT.
        """
        if self.has_openid_request and self.rpconfig is not None:
            return self.rpconfig.creation_rationale
        else:
            return PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        super(NewAccountView, self).continue_action.success(data)
        return self.maybeCompleteOpenIDRequest()

    def _createAccountEmailAndMaybePerson(
            self, displayname, hide_email_addresses, password):
        """Create and return a new Account and EmailAddress.

        This method will create an Account (in the ACTIVE state) and an
        EmailAddress as the account's preferred one.

        Also fire ObjectCreatedEvents for both the newly created Account and
        EmailAddress.
        """
        assert self.context.tokentype == LoginTokenType.NEWPERSONLESSACCOUNT
        person = None
        rationale = self._getCreationRationale()
        account, email = getUtility(IAccountSet).createAccountAndEmail(
            self.context.email, rationale, displayname, password,
            password_is_encrypted=True)
        notify(ObjectCreatedEvent(account))
        notify(ObjectCreatedEvent(email))
        return account, person, email

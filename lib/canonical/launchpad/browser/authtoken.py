# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'AuthTokenSetNavigation',
    'AuthTokenView',
    'NewAccountView',
    'ResetAccountPasswordView',
    'ValidateEmailView',
    ]

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.security.proxy import removeSecurityProxy

from canonical.widgets import PasswordChangeWidget
from canonical.launchpad import _
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, GetitemNavigation,
    LaunchpadFormView)

from canonical.signon.browser.openidserver import OpenIDMixin
from canonical.launchpad.browser.logintoken import (
    BaseTokenView, LoginTokenView, ResetPasswordView, ValidateTeamEmailView)
from canonical.launchpad.interfaces import IMasterObject
from canonical.launchpad.interfaces.account import AccountStatus, IAccountSet
from canonical.launchpad.interfaces.authtoken import (
    IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.emailaddress import IEmailAddressSet
from canonical.launchpad.interfaces.launchpad import UnexpectedFormData
from lp.registry.interfaces.person import (
    INewPersonForm, IPerson, IPersonSet, PersonCreationRationale)


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
    PAGES = LoginTokenView.sso_pages


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
        self.next_url = None
        return self.renderOpenIDResponse(self.createPositiveResponse())


class ResetAccountPasswordView(AuthTokenOpenIDMixinView, ResetPasswordView):

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


class ValidateEmailView(AuthTokenOpenIDMixinView, ValidateTeamEmailView):

    expected_token_types = (LoginTokenType.VALIDATEEMAIL,)

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        super(ValidateEmailView, self).continue_action.success(data)
        return self.maybeCompleteOpenIDRequest()

    def markEmailAsValid(self, email):
        """See `ValidateEmailView`"""
        self.context.requester_account.validateAndEnsurePreferredEmail(email)


class NewAccountView(
        BaseTokenView, AuthTokenOpenIDMixinView, LaunchpadFormView):
    """Page to create a new Launchpad account."""

    created_person = None

    schema = INewPersonForm
    field_names = ['displayname', 'hide_email_addresses', 'password']
    custom_widget('password', PasswordChangeWidget)
    label = 'Complete your registration'
    expected_token_types = (
        LoginTokenType.NEWACCOUNT, LoginTokenType.NEWPROFILE,
        LoginTokenType.NEWPERSONLESSACCOUNT)

    def initialize(self):
        if self.redirectIfInvalidOrConsumedToken():
            return
        else:
            self.email = getUtility(IEmailAddressSet).getByEmail(
                self.context.email)
            super(NewAccountView, self).initialize()

    # Use a method to set self.next_url rather than a property because we
    # want to override self.next_url in a subclass of this.
    def setNextUrl(self):
        if self.has_openid_request:
            # For OpenID requests we don't use self.next_url, so don't even
            # bother setting it.
            return

        if self.context.redirection_url:
            self.next_url = self.context.redirection_url
        elif self.account is not None:
            # User is logged in, redirect to his home page.
            person = IPerson(self.account, None)
            # XXX: salgado, 2009-04-02: We shouldn't reach this path when
            # self.account is a personless account, but unfortunately our
            # OpenID server doesn't store a fallback redirection_url in the
            # AuthTokens it creates (bug=353974), so we need this hack here.
            if person is None:
                self.next_url = self.request.getApplicationURL()
            else:
                self.next_url = canonical_url(person)
        elif self.created_person is not None:
            # User is not logged in, redirect to the created person's home
            # page.
            self.next_url = canonical_url(self.created_person)
        else:
            self.next_url = None

    def validate(self, form_values):
        """Verify if the email address is not used by an existing account."""
        if self.email is not None:
            if self.email.person is not None:
                person = IMasterObject(self.email.person)
                if person.is_valid_person:
                    self.addError(_(
                        'The email address ${email} is already registered.',
                        mapping=dict(email=self.context.email)))
            else:
                self.addError(_(
                    'The email address ${email} is already registered in '
                    'the Launchpad Login Service (used by the Ubuntu shop '
                    'and other OpenID sites). Please use the same email and '
                    'password to log into Launchpad.',
                    mapping=dict(email=self.context.email)))


    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        """Create a new Person with the context's email address and set a
        preferred email and password to it, or use an existing Person
        associated with the context's email address, setting it as the
        preferred address and also setting the password.

        If everything went ok, we consume the LoginToken (self.context), so
        nobody can use it again.
        """
        if self.email is not None:
            assert self.email.person is not None, (
                "People trying to register using emails associated with "
                "personless accounts should be told to just use their Login "
                "Service credentials to log into LP")
            # This is a placeholder profile automatically created by one of
            # our scripts, let's just confirm its email address and set a
            # password.
            person = getUtility(IPersonSet).get(
                removeSecurityProxy(self.email).personID)
            assert not person.is_valid_person, (
                'Account %s has already been claimed and this should '
                'have been caught by the validate() method.' % person.name)
            email = self.email
            # The user is not yet logged in, but we need to set some
            # things on his new account, so we need to remove the security
            # proxy from it.
            # XXX: Guilherme Salgado 2006-09-27 bug=62674:
            # We should be able to login with this person and set the
            # password, to avoid removing the security proxy, but it didn't
            # work, so I'm leaving this hack for now.
            naked_person = removeSecurityProxy(person)
            # Suspended accounts cannot reactivate their profile.
            reason = ('This profile cannot be claimed because the account '
                'is suspended.')
            if self.accountWasSuspended(person.account, reason):
                return
            naked_person.displayname = data['displayname']
            naked_person.hide_email_addresses = data['hide_email_addresses']
            # Need to remove the security proxy of the account because at this
            # point the user is not logged in.
            account = removeSecurityProxy(IMasterObject(person.account))
            account.activate(
                "Activated by new account.",
                password=data['password'],
                preferred_email=self.email)
            naked_person.creation_rationale = self._getCreationRationale()
            naked_person.creation_comment = None
        else:
            account, person, email = self._createAccountPersonAndEmail(
                data['displayname'], data['hide_email_addresses'],
                data['password'])

        self.context.consume()
        self.logInPrincipalByEmail(removeSecurityProxy(email).email)
        self.created_person = person
        self.request.response.addInfoNotification(_(
            "Registration completed successfully"))
        self.setNextUrl()

        return self.maybeCompleteOpenIDRequest()

    def _getCreationRationale(self):
        """Return the creation rationale that should be used for this account.

        If there's an OpenID request in the session we use the given
        trust_root to find out the creation rationale. If there's no OpenID
        request we use PersonCreationRationale.OWNER_CREATED_LAUNCHPAD.
        """
        if self.has_openid_request:
            if self.rpconfig is not None:
                rationale = self.rpconfig.creation_rationale
            else:
                rationale = (
                    PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT)
        else:
            # There is no OpenIDRequest in the session, so we'll assume the
            # user is creating the account because he wants to use Launchpad.
            rationale = PersonCreationRationale.OWNER_CREATED_LAUNCHPAD
        return rationale

    def _createAccountPersonAndEmail(
            self, displayname, hide_email_addresses, password):
        """Create and return a new Account, Person and EmailAddress.

        This method will always create an Account (in the ACTIVE state) and
        an EmailAddress as the account's preferred one.  However, if the
        registration process was not started through OpenID, we'll create also
        a Person.

        Use the given arguments and the email address stored in the
        LoginToken (our context).

        Also fire ObjectCreatedEvents for both the newly created Person
        and EmailAddress.
        """
        rationale = self._getCreationRationale()
        if self.context.tokentype == LoginTokenType.NEWPERSONLESSACCOUNT:
            person = None
            account, email = getUtility(IAccountSet).createAccountAndEmail(
                self.context.email, rationale, displayname,
                password, password_is_encrypted=True)
        else:
            person, email = getUtility(IPersonSet).createPersonAndEmail(
                self.context.email, rationale, displayname=displayname,
                password=password, passwordEncrypted=True,
                hide_email_addresses=hide_email_addresses)
            notify(ObjectCreatedEvent(person))
            person.validateAndEnsurePreferredEmail(email)
            account = getUtility(IAccountSet).get(person.accountID)
            removeSecurityProxy(account).status = AccountStatus.ACTIVE

        notify(ObjectCreatedEvent(account))
        notify(ObjectCreatedEvent(email))
        return account, person, email

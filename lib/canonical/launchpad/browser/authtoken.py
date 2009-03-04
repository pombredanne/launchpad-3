# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'AuthTokenSetNavigation',
    'AuthTokenView',
    'BaseAuthTokenView',
    'NewAccountView',
    'ResetPasswordView',
    'ValidateEmailView',
    ]

import urllib
import cgi

from zope.lifecycleevent import ObjectCreatedEvent
from zope.component import getUtility
from zope.event import notify
from zope.interface import Interface
from zope.security.proxy import removeSecurityProxy

from canonical.widgets import PasswordChangeWidget
from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPrincipal
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, GetitemNavigation,
    LaunchpadFormView, LaunchpadView)

from canonical.launchpad.browser.openidserver import OpenIDMixin
from canonical.launchpad.interfaces.account import AccountStatus, IAccountSet
from canonical.launchpad.interfaces.authtoken import (
    IAuthToken, IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddressSet)
from canonical.launchpad.interfaces.launchpad import UnexpectedFormData
from canonical.launchpad.interfaces.lpstorm import IMasterObject
from canonical.launchpad.interfaces.openidserver import IOpenIDRPConfigSet
from canonical.launchpad.interfaces.person import (
    INewPersonForm, IPerson, IPersonSet, PersonCreationRationale)
from canonical.launchpad.interfaces.shipit import ShipItConstants


class AuthTokenSetNavigation(GetitemNavigation):

    usedfor = IAuthTokenSet


class AuthTokenView(LaunchpadView):
    """The default view for AuthToken.

    This view will check the token type and then redirect to the specific view
    for that type of token, if it's not yet a consumed token. We use this view
    so we don't have to add "+validateemail", "+newaccount", etc, on URLs we
    send by email.

    If this is a consumed token, then we simply display a page explaining that
    they got this token because they tried to do something that required email
    address confirmation, but that confirmation is already concluded.
    """

    PAGES = {
        LoginTokenType.NEWACCOUNT: '+newaccount',
        LoginTokenType.NEWPERSONLESSACCOUNT: '+newaccount',
        LoginTokenType.NEWPROFILE: '+newaccount',
        LoginTokenType.PASSWORDRECOVERY: '+resetpassword',
        LoginTokenType.VALIDATEEMAIL: '+validateemail',
        }

    def render(self):
        if self.context.date_consumed is None:
            url = urllib.basejoin(
                str(self.request.URL), self.PAGES[self.context.tokentype])
            self.request.response.redirect(url)
        else:
            return super(AuthTokenView, self).render()


class BaseAuthTokenView(OpenIDMixin):
    """A view class to be used by other LoginToken views."""

    expected_token_types = ()
    successfullyProcessed = False

    def redirectIfInvalidOrConsumedToken(self):
        """If this is a consumed or invalid token redirect to the LoginToken
        default view and return True.

        An invalid token is a token used for a purpose it wasn't generated for
        (i.e. create a new account with a VALIDATEEMAIL token).
        """
        assert self.expected_token_types
        if (self.context.date_consumed is not None
            or self.context.tokentype not in self.expected_token_types):
            self.request.response.redirect(canonical_url(self.context))
            return True
        else:
            return False

    def success(self, message):
        """Indicate to the user that the token was successfully processed.

        This involves adding a notification message, and redirecting the
        user to their Launchpad page.
        """
        self.successfullyProcessed = True
        self.request.response.addInfoNotification(message)

    def logInPrincipalByEmail(self, email):
        """Login the principal with the given email address."""
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        logInPrincipal(self.request, principal, email)

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

    def _cancel(self):
        """Consume the LoginToken and set self.next_url.

        next_url is set to the home page of this LoginToken's requester.
        """
        self.next_url = canonical_url(self.context.requester)
        self.context.consume()

    def accountWasSuspended(self, account, reason):
        """Return True if the person's account was SUSPENDED, otherwise False.

        When the account was SUSPENDED, the Warning Notification with the
        reason is added to the request's response. The LoginToken is consumed.

        :param account: The IAccount.
        :param reason: A sentence that explains why the SUSPENDED account
            cannot be used.
        """
        if account.status != AccountStatus.SUSPENDED:
            return False
        suspended_account_mailto = (
            'mailto:feedback@launchpad.net?subject=SUSPENDED%20account')
        message = structured(
              '%s Contact a <a href="%s">Launchpad admin</a> '
              'about this issue.' % (reason, suspended_account_mailto))
        self.request.response.addWarningNotification(message)
        self.context.consume()
        return True


class ResetPasswordView(BaseAuthTokenView, LaunchpadFormView):

    schema = IAuthToken
    field_names = ['email', 'password']
    custom_widget('password', PasswordChangeWidget)
    label = 'Reset password'
    expected_token_types = (LoginTokenType.PASSWORDRECOVERY,)

    def initialize(self):
        self.redirectIfInvalidOrConsumedToken()
        super(ResetPasswordView, self).initialize()

    def validate(self, form_values):
        """Validate the email address."""
        email = form_values.get("email", "").strip()
        # All operations with email addresses must be case-insensitive. We
        # enforce that in EmailAddressSet, but here we only do a comparison,
        # so we have to .lower() them first.
        if email.lower() != self.context.email.lower():
            self.addError(_(
                "The email address you provided didn't match the address "
                "you provided when requesting the password reset."))

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        """Reset the user's password. When password is successfully changed,
        the LoginToken (self.context) used is consumed, so nobody can use
        it again.
        """
        emailaddress = getUtility(IEmailAddressSet).getByEmail(
            self.context.email)
        account = self.context.requester_account
        # Suspended accounts cannot reset their password.
        reason = ('Your password cannot be reset because your account '
                  'is suspended.')
        if self.accountWasSuspended(account, reason):
            return

        naked_account = removeSecurityProxy(account)
        # Reset password can be used to reactivate a deactivated account.
        if account.status == AccountStatus.DEACTIVATED:
            naked_account.reactivate(
                comment="User reactivated the account using reset password.",
                password=data['password'],
                preferred_email=emailaddress)
            self.request.response.addInfoNotification(
                _('Welcome back to Launchpad.'))
        else:
            naked_account.password = data.get('password')

        person = IMasterObject(self.context.requester, None)
        # Make sure this person has a preferred email address.
        if person is not None and person.preferredemail != emailaddress:
            # Must remove the security proxy of the email address because
            # the user is not logged in at this point and we may need to
            # change its status.
            removeSecurityProxy(person).validateAndEnsurePreferredEmail(
                removeSecurityProxy(emailaddress))

        if self.context.redirection_url is not None:
            self.next_url = self.context.redirection_url
        elif person is not None:
            self.next_url = canonical_url(person)
        else:
            assert self.has_openid_request, (
                'No redirection URL specified and this is not part of an '
                'OpenID authentication.')

        self.context.consume()

        self.logInPrincipalByEmail(self.context.email)

        self.request.response.addInfoNotification(
            _('Your password has been reset successfully.'))

        return self.maybeCompleteOpenIDRequest()

    @action(_('Cancel'), name='cancel')
    def cancel_action(self, action, data):
        self._cancel()


class ValidateEmailView(BaseAuthTokenView, LaunchpadFormView):

    schema = Interface
    field_names = []
    expected_token_types = (LoginTokenType.VALIDATEEMAIL,)

    def initialize(self):
        self.redirectIfInvalidOrConsumedToken()
        super(ValidateEmailView, self).initialize()

    def validate(self, data):
        """Make sure the email address this token refers to is not in use."""
        validated = (
            EmailAddressStatus.VALIDATED, EmailAddressStatus.PREFERRED)
        requester = self.context.requester

        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(self.context.email)
        if email is not None:
            if email.person.id != requester.id:
                dupe = email.person
                dname = cgi.escape(dupe.name)
                # Yes, hardcoding an autogenerated field name is an evil
                # hack, but if it fails nothing will happen.
                # -- Guilherme Salgado 2005-07-09
                url = allvhosts.configs['mainsite'].rooturl
                url += '/people/+requestmerge?field.dupeaccount=%s' % dname
                self.addError(
                        structured(_(
                    'This email address is already registered for another '
                    'Launchpad user account. This account can be a '
                    'duplicate of yours, created automatically, and in this '
                    'case you should be able to <a href="${url}">merge them'
                    '</a> into a single one.',
                    mapping=dict(url=url))))
            elif email.status in validated:
                self.addError(_(
                    "This email address is already registered and validated "
                    "for your Launchpad account. There's no need to validate "
                    "it again."))
            else:
                # Yay, email is not used by anybody else and is not yet
                # validated.
                pass

    @action(_('Cancel'), name='cancel')
    def cancel_action(self, action, data):
        self._cancel()

    @action(_('Continue'), name='continue')
    def continue_action(self, action, data):
        """Mark the new email address as VALIDATED in the database.

        If this is the first validated email of this person, it'll be marked
        as the preferred one.

        If the requester is a team, the team's contact address is removed (if
        any) and this becomes the team's contact address.
        """
        self.next_url = canonical_url(self.context.requester)

        email = self._ensureEmail()
        self.markEmailAsValid(email)

        self.context.consume()
        self.request.response.addInfoNotification(
            _('Email address successfully confirmed.'))
        return self.maybeCompleteOpenIDRequest()

    def _ensureEmail(self):
        """Make sure self.requester has this token's email address as one of
        its email addresses and return it.
        """
        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(self.context.email)
        if email is None:
            email = emailset.new(self.context.email, self.context.requester)
        return email

    def markEmailAsValid(self, email):
        """Mark the given email address as valid."""
        self.context.requester.validateAndEnsurePreferredEmail(email)


class NewAccountView(BaseAuthTokenView, LaunchpadFormView):
    """Page to create a new Launchpad account.

    # This is just a small test to make sure
    # LoginOrRegister.registered_origins and
    # NewAccountView.urls_and_rationales are kept in sync.
    >>> from canonical.launchpad.webapp.login import LoginOrRegister
    >>> urls = sorted(LoginOrRegister.registered_origins.values())
    >>> urls == sorted(NewAccountView.urls_and_rationales.keys())
    True
    """

    urls_and_rationales = {
        ShipItConstants.ubuntu_url:
            PersonCreationRationale.OWNER_CREATED_SHIPIT,
        ShipItConstants.kubuntu_url:
            PersonCreationRationale.OWNER_CREATED_SHIPIT,
        ShipItConstants.edubuntu_url:
            PersonCreationRationale.OWNER_CREATED_SHIPIT,
        }

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
            self.next_url = canonical_url(IPerson(self.account))
        elif self.created_person is not None:
            # User is not logged in, redirect to the created person's home
            # page.
            self.next_url = canonical_url(self.created_person)
        else:
            self.next_url = None

    def validate(self, form_values):
        """Verify if the email address is not used by an existing account."""
        if self.email is not None:
            # Better spelt as IMasterObject(self.email.person), but that
            # issues an unnecessary database call.
            person = getUtility(IPersonSet).get(
                removeSecurityProxy(self.email).personID)
            if person.is_valid_person:
                self.addError(_(
                    'The email address ${email} is already registered.',
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
            naked_person.activateAccount(
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
        request but there is a rationale for the logintoken's redirection_url,
        then use that, otherwise uses
        PersonCreationRationale.OWNER_CREATED_LAUNCHPAD.
        """
        if self.has_openid_request:
            rpconfig = getUtility(IOpenIDRPConfigSet).getByTrustRoot(
                self.openid_request.trust_root)
            if rpconfig is not None:
                rationale = rpconfig.creation_rationale
            else:
                rationale = (
                    PersonCreationRationale.OWNER_CREATED_UNKNOWN_TRUSTROOT)
        else:
            # There is no OpenIDRequest in the session, so we'll try to infer
            # the creation rationale from the token's redirection_url.
            rationale = self.urls_and_rationales.get(
                self.context.redirection_url)
            if rationale is None:
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

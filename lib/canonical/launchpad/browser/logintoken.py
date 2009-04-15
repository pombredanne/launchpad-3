# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'BugTrackerHandshakeView',
    'ClaimProfileView',
    'ClaimTeamView',
    'LoginTokenSetNavigation',
    'LoginTokenView',
    'MergePeopleView',
    'ResetPersonPasswordView',
    'ValidateTeamEmailView',
    'ValidateGPGKeyView',
    ]

from itertools import chain
import pytz

from zope.app.form.browser import TextAreaWidget
from zope.component import getUtility
from zope.interface import alsoProvides, directlyProvides
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import flush_database_updates
from canonical.widgets import LaunchpadRadioWidget, PasswordChangeWidget
from canonical.launchpad import _
from canonical.launchpad.interfaces import IMasterObject
from canonical.launchpad.webapp.interfaces import IAlwaysSubmittedWidget
from canonical.launchpad.webapp.menu import structured
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, GetitemNavigation,
    LaunchpadEditFormView, LaunchpadFormView, LaunchpadView)

from canonical.launchpad.browser.authtoken import (
    AuthTokenView, BaseAuthTokenView, ResetPasswordView, ValidateEmailView)
from lp.registry.browser.team import HasRenewalPolicyMixin
from canonical.launchpad.interfaces import (
    EmailAddressStatus, GPGKeyAlgorithm, GPGKeyNotFoundError,
    GPGVerificationError, IEmailAddressSet, IGPGHandler, IGPGKeySet,
    IGPGKeyValidationForm, ILoginTokenSet, IPerson, IPersonSet,
    ITeam, LoginTokenType)


UTC = pytz.UTC


class LoginTokenSetNavigation(GetitemNavigation):

    usedfor = ILoginTokenSet


class LoginTokenView(AuthTokenView):
    """The default view for LoginToken.

    This view will check the token type and then redirect to the specific view
    for that type of token, if it's not yet a consumed token. We use this view
    so we don't have to add "+validateemail", "+newaccount", etc, on URLs we
    send by email.

    If this is a consumed token, then we simply display a page explaining that
    they got this token because they tried to do something that required email
    address confirmation, but that confirmation is already concluded.
    """
    PAGES = AuthTokenView.PAGES.copy()
    PAGES.update({
            LoginTokenType.ACCOUNTMERGE: '+accountmerge',
            LoginTokenType.VALIDATETEAMEMAIL: '+validateteamemail',
            LoginTokenType.VALIDATEGPG: '+validategpg',
            LoginTokenType.VALIDATESIGNONLYGPG: '+validatesignonlygpg',
            LoginTokenType.PROFILECLAIM: '+claimprofile',
            LoginTokenType.TEAMCLAIM: '+claimteam',
            LoginTokenType.BUGTRACKER: '+bugtracker-handshake',
            })


class ResetPersonPasswordView(ResetPasswordView):

    def reactivate(self, data):
        emailaddress = getUtility(IEmailAddressSet).getByEmail(
            self.context.email)
        removeSecurityProxy(self.context.requester).reactivate(
            comment="User reactivated the account using reset password.",
            password=data['password'],
            preferred_email=emailaddress)


class ClaimProfileView(BaseAuthTokenView, LaunchpadFormView):
    schema = IPerson
    field_names = ['displayname', 'hide_email_addresses', 'password']
    custom_widget('password', PasswordChangeWidget)
    label = 'Claim Launchpad profile'

    expected_token_types = (LoginTokenType.PROFILECLAIM,)

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            self.claimed_profile = getUtility(IEmailAddressSet).getByEmail(
                self.context.email).person
        super(ClaimProfileView, self).initialize()

    @property
    def initial_values(self):
        return {'displayname': self.claimed_profile.displayname}

    @property
    def next_url(self):
        return canonical_url(self.claimed_profile)

    @action(_('Continue'), name='confirm')
    def confirm_action(self, action, data):
        email = getUtility(IEmailAddressSet).getByEmail(self.context.email)
        person = IMasterObject(email.person)

        # The user is not yet logged in, but we need to set some
        # things on his new account, so we need to remove the security
        # proxy from it.
        # XXX: Guilherme Salgado 2006-09-27 bug=62674:
        # We should be able to login with this person and set the
        # password, to avoid removing the security proxy, but it didn't
        # work, so I'm leaving this hack for now.
        naked_person = removeSecurityProxy(person)
        naked_person.displayname = data['displayname']
        naked_person.hide_email_addresses = data['hide_email_addresses']

        naked_email = removeSecurityProxy(email)

        removeSecurityProxy(IMasterObject(email.account)).activate(
            comment="Activated by claim profile.",
            password=data['password'],
            preferred_email=naked_email)
        self.context.consume()
        self.logInPrincipalByEmail(naked_email.email)
        self.request.response.addInfoNotification(_(
            "Profile claimed successfully"))


class ClaimTeamView(
    BaseAuthTokenView, HasRenewalPolicyMixin, LaunchpadEditFormView):

    schema = ITeam
    field_names = [
        'teamowner', 'displayname', 'teamdescription', 'subscriptionpolicy',
        'defaultmembershipperiod', 'renewal_policy', 'defaultrenewalperiod']
    label = 'Claim Launchpad team'
    custom_widget('teamdescription', TextAreaWidget, height=10, width=30)
    custom_widget(
        'renewal_policy', LaunchpadRadioWidget, orientation='vertical')
    custom_widget(
        'subscriptionpolicy', LaunchpadRadioWidget, orientation='vertical')

    expected_token_types = (LoginTokenType.TEAMCLAIM,)

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            self.claimed_profile = getUtility(IPersonSet).getByEmail(
                self.context.email)
            # Let's pretend the claimed profile provides ITeam while we
            # render/process this page, so that it behaves like a team.
            directlyProvides(removeSecurityProxy(self.claimed_profile), ITeam)
        super(ClaimTeamView, self).initialize()

    def setUpWidgets(self, context=None):
        self.form_fields['teamowner'].for_display = True
        super(ClaimTeamView, self).setUpWidgets(context=self.claimed_profile)
        alsoProvides(self.widgets['teamowner'], IAlwaysSubmittedWidget)

    @property
    def initial_values(self):
        return {'teamowner': self.context.requester}

    @action(_('Continue'), name='confirm')
    def confirm_action(self, action, data):
        self.claimed_profile.convertToTeam(team_owner=self.context.requester)
        # Although we converted the person to a team it seems that the
        # security proxy still thinks it's an IPerson and not an ITeam,
        # which means to edit it we need to be logged in as the person we
        # just converted into a team.  Of course, we can't do that, so we'll
        # have to remove its security proxy before we update it.
        self.updateContextFromData(
            data, context=removeSecurityProxy(self.claimed_profile))
        self.next_url = canonical_url(self.claimed_profile)
        self.request.response.addInfoNotification(
            _('Team claimed successfully'))

    @action(_('Cancel'), name='cancel')
    def cancel_action(self, action, data):
        self._cancel()


class ValidateGPGKeyView(BaseAuthTokenView, LaunchpadFormView):

    schema = IGPGKeyValidationForm
    field_names = []
    expected_token_types = (LoginTokenType.VALIDATEGPG,
                            LoginTokenType.VALIDATESIGNONLYGPG)

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            if self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
                self.field_names = ['text_signature']
        super(ValidateGPGKeyView, self).initialize()

    def validate(self, data):
        self.gpg_key = self._getGPGKey()
        if self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
            self._validateSignOnlyGPGKey(data)

    @action(_('Cancel'), name='cancel')
    def cancel_action(self, action, data):
        self._cancel()

    @action(_('Continue'), name='continue')
    def continue_action_gpg(self, action, data):
        self.next_url = canonical_url(self.context.requester)
        assert self.gpg_key is not None
        can_encrypt = (
            self.context.tokentype != LoginTokenType.VALIDATESIGNONLYGPG)
        self._activateGPGKey(self.gpg_key, can_encrypt=can_encrypt)

    def _validateSignOnlyGPGKey(self, data):
        # Verify the signed content.
        signedcontent = data.get('text_signature')
        if signedcontent is None:
            return

        try:
            signature = getUtility(IGPGHandler).getVerifiedSignature(
                signedcontent.encode('ASCII'))
        except (GPGVerificationError, UnicodeEncodeError), e:
            self.addError(_(
                'Launchpad could not verify your signature: ${err}',
                mapping=dict(err=str(e))))
            return

        if signature.fingerprint != self.context.fingerprint:
            self.addError(_(
                'The key used to sign the content (${fprint}) is not the '
                'key you were registering',
                mapping=dict(fprint=signature.fingerprint)))
            return

        # We compare the word-splitted content to avoid failures due
        # to whitepace differences.
        if signature.plain_data.split() != self.validationphrase.split():
            self.addError(_(
                'The signed content does not match the message found '
                'in the email.'))
            return

    def _activateGPGKey(self, key, can_encrypt):
        gpgkeyset = getUtility(IGPGKeySet)

        fingerprint = key.fingerprint
        requester = self.context.requester
        person_url = canonical_url(requester)

        # Is it a revalidation ?
        lpkey = gpgkeyset.getByFingerprint(fingerprint)

        if lpkey:
            lpkey.active = True
            lpkey.can_encrypt = can_encrypt
            msgid = _(
                'Key ${lpkey} successfully reactivated. '
                '<a href="${url}/+editpgpkeys">See more Information'
                '</a>',
                mapping=dict(lpkey=lpkey.displayname, url=person_url))
            self.request.response.addInfoNotification(structured(msgid))
            self.context.consume()
            return

        # Otherwise prepare to add
        ownerID = self.context.requester.id
        keyid = key.keyid
        keysize = key.keysize
        algorithm = GPGKeyAlgorithm.items[key.algorithm]

        # Add new key in DB. See IGPGKeySet for further information
        lpkey = gpgkeyset.new(ownerID, keyid, fingerprint, keysize, algorithm,
                              can_encrypt=can_encrypt)

        self.context.consume()
        self.request.response.addInfoNotification(_(
            "The key ${lpkey} was successfully validated. ",
            mapping=dict(lpkey=lpkey.displayname)))
        created, owned_by_others = self._createEmailAddresses(key.emails)

        if len(created):
            msgid = _(
                "<p>Some of your key's UIDs (<code>${emails}</code>) are "
                "not registered in Launchpad. If you want to use them in "
                'Launchpad, you will need to <a href="${url}/+editemails">'
                'confirm them</a> first.</p>',
                mapping=dict(emails=', '.join(created), url=person_url))
            self.request.response.addInfoNotification(structured(msgid))

        if len(owned_by_others):
            msgid = _(
                "<p>Also, some of them (<code>${emails}</code>) are "
                "associated with other profile(s) in Launchpad, so you may "
                'want to <a href="/people/+requestmerge">merge them</a> into '
                "your current one.</p>",
                mapping=dict(emails=', '.join(owned_by_others)))
            self.request.response.addInfoNotification(structured(msgid))

    def _createEmailAddresses(self, uids):
        """Create EmailAddresses for the GPG UIDs that do not exist yet.

        For each of the given UIDs, check if it is already registered and, if
        not, register it.

        Return a tuple containing the list of newly created emails (as
        strings) and the emails that exist and are already assigned to another
        person (also as strings).
        """
        emailset = getUtility(IEmailAddressSet)
        requester = self.context.requester
        emails = chain(requester.validatedemails, [requester.preferredemail])
        # Must remove the security proxy because the user may not be logged in
        # and thus won't be allowed to view the requester's email addresses.
        emails = [
            removeSecurityProxy(email).email.lower() for email in emails]

        created = []
        existing_and_owned_by_others = []
        for uid in uids:
            # Here we use .lower() because the case of email addresses's chars
            # don't matter to us (e.g. 'foo@baz.com' is the same as
            # 'Foo@Baz.com').  However, note that we use the original form
            # when creating a new email.
            if uid.lower() not in emails:
                # EmailAddressSet.getByEmail() is not case-sensitive, so
                # there's no need to do uid.lower() here.
                if emailset.getByEmail(uid) is not None:
                    # This email address is registered but does not belong to
                    # our user.
                    existing_and_owned_by_others.append(uid)
                else:
                    # The email is not yet registered, so we register it for
                    # our user.
                    email = emailset.new(uid, requester)
                    created.append(uid)

        return created, existing_and_owned_by_others

    @property
    def validationphrase(self):
        """The phrase used to validate sign-only GPG keys"""
        utctime = self.context.date_created.astimezone(UTC)
        return 'Please register %s to the\nLaunchpad user %s.  %s UTC' % (
            self.context.fingerprint, self.context.requester.name,
            utctime.strftime('%Y-%m-%d %H:%M:%S'))

    def _getGPGKey(self):
        """Look up the OpenPGP key for this login token.

        If the key can not be retrieved from the keyserver, the key
        has been revoked or expired, None is returned and an error is set
        using self.addError.
        """
        gpghandler = getUtility(IGPGHandler)

        requester = self.context.requester
        fingerprint = self.context.fingerprint
        assert fingerprint is not None

        person_url = canonical_url(requester)
        try:
            key = gpghandler.retrieveKey(fingerprint)
        except GPGKeyNotFoundError:
            self.addError(
                structured(_(
                'Launchpad could not import this OpenPGP key, because '
                '${key}. Check that you published it correctly in the '
                'global key ring (using <kbd>gpg --send-keys '
                'KEY</kbd>) and that you entered the fingerprint '
                'correctly (as produced by <kbd>gpg --fingerprint '
                'YOU</kdb>). Try later or <a href="${url}/+editpgpkeys"> '
                'cancel your request</a>.',
                mapping=dict(key=key, url=person_url))))
            return None

        # If key is globally revoked, skip the import and consume the token.
        if key.revoked:
            self.addError(
                    structured(_(
                'The key ${key} cannot be validated because it has been '
                'publicly revoked. You will need to generate a new key '
                '(using <kbd>gpg --genkey</kbd>) and repeat the previous '
                'process to <a href="${url}/+editpgpkeys">find and '
                'import</a> the new key.',
                mapping=dict(key=key.keyid, url=person_url))))
            return None

        if key.expired:
            self.addError(
                        structured(_(
                'The key ${key} cannot be validated because it has expired. '
                'Change the expiry date (in a terminal, enter '
                '<kbd>gpg --edit-key <var>your@e-mail.address</var></kbd> '
                'then enter <kbd>expire</kbd>), and try again.',
                mapping=dict(key=key.keyid))))
            return None

        return key


class ValidateTeamEmailView(ValidateEmailView):
    expected_token_types = (LoginTokenType.VALIDATETEAMEMAIL,)

    def markEmailAsValid(self, email):
        """See `ValidateEmailView`"""
        self.context.requester.setContactAddress(email)


class MergePeopleView(BaseAuthTokenView, LaunchpadView):

    expected_token_types = (LoginTokenType.ACCOUNTMERGE,)
    mergeCompleted = False

    def initialize(self):
        self.redirectIfInvalidOrConsumedToken()
        self.dupe = getUtility(IPersonSet).getByEmail(self.context.email)

    def success(self, message):
        # We're not a GeneralFormView, so we need to do the redirect
        # ourselves.
        BaseAuthTokenView.success(self, message)
        self.request.response.redirect(canonical_url(self.context.requester))

    def processForm(self):
        """Perform the merge."""
        if self.request.method != "POST":
            return

        # Merge requests must have a valid user account (one with a preferred
        # email) as requester.
        assert self.context.requester.preferredemail is not None
        self._doMerge()
        if self.mergeCompleted:
            self.success(_(
                'The accounts have been merged successfully. Everything that '
                'belonged to the duplicated account should now belong to '
                'your own account.'))
        else:
            self.success(_(
                'The e-mail address %s has been assigned to you, but the '
                'duplicate account you selected has other registered e-mail '
                'addresses too. To complete the merge, you have to prove '
                'that you have access to all those e-mail addresses.'
                % self.context.email))
        self.context.consume()

    def _doMerge(self):
        # The user proved that he has access to this email address of the
        # dupe account, so we can assign it to him.
        requester = self.context.requester
        emailset = getUtility(IEmailAddressSet)
        email = removeSecurityProxy(emailset.getByEmail(self.context.email))
        # As a person can have at most one preferred email, ensure
        # that this new email does not have the PREFERRED status.
        email.status = EmailAddressStatus.NEW
        email.personID = requester.id
        email.accountID = requester.accountID
        requester.validateAndEnsurePreferredEmail(email)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()

        # Now we must check if the dupe account still have registered email
        # addresses. If it hasn't we can actually do the merge.
        if emailset.getByPerson(self.dupe):
            self.mergeCompleted = False
            return

        # Call Stuart's magic function which will reassign all of the dupe
        # account's stuff to the user account.
        getUtility(IPersonSet).merge(self.dupe, requester)
        self.mergeCompleted = True


class BugTrackerHandshakeView(BaseAuthTokenView):
    """A view for authentication BugTracker handshake tokens."""
    expected_token_types = (LoginTokenType.BUGTRACKER,)

    def __call__(self):
        # We don't render any templates from this view as it's a
        # machine-only one, so we set the response to be plaintext.
        self.request.response.setHeader('Content-type', 'text/plain')

        # Reject the request if it is not a POST - but do not consume
        # the token.
        if self.request.method != 'POST':
            self.request.response.setStatus(405)
            self.request.response.setHeader('Allow', 'POST')
            return ("Only POST requests are accepted for bugtracker "
                    "handshakes.")

        # If the token has been used already or is invalid, return an
        # HTTP 410 (Gone).
        if self.redirectIfInvalidOrConsumedToken():
            self.request.response.setStatus(410)
            return "Token has already been used or is invalid."

        # The token is valid, so consume it and return an HTTP 200. This
        # tells the remote tracker that authentication was successful.
        self.context.consume()
        self.request.response.setStatus(200)
        self.request.response.setHeader('Content-type', 'text/plain')
        return "Handshake token validated."


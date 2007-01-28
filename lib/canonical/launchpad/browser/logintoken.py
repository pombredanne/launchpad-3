# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'LoginTokenSetNavigation',
    'LoginTokenView',
    'ResetPasswordView',
    'ValidateEmailView',
    'NewAccountView',
    'MergePeopleView',
    'ClaimProfileView',
    ]

import urllib
import pytz

from zope.component import getUtility
from zope.event import notify
from zope.app.form.interfaces import WidgetsError
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.database.sqlbase import flush_database_updates

from canonical.widgets import PasswordChangeWidget

from canonical.lp.dbschema import (
    EmailAddressStatus, GPGKeyAlgorithm, LoginTokenType,
    PersonCreationRationale)

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPerson
from canonical.launchpad.webapp import (
    action, canonical_url, custom_widget, GeneralFormView, GetitemNavigation,
    LaunchpadView, LaunchpadFormView)

from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, ILaunchBag, ILoginTokenSet, IPerson,
    IGPGKeySet, IGPGHandler, GPGVerificationError, GPGKeyNotFoundError,
    ShipItConstants, UBUNTU_WIKI_URL)

UTC = pytz.timezone('UTC')


class LoginTokenSetNavigation(GetitemNavigation):

    usedfor = ILoginTokenSet


class LoginTokenView(LaunchpadView):
    """The default view for LoginToken.

    This view will check the token type and then redirect to the specific view
    for that type of token, if it's not yet a consumed token. We use this view
    so we don't have to add "+validateemail", "+newaccount", etc, on URLs we
    send by email.

    If this is a consumed token, then we simply display a page explaining that
    they got this token because they tried to do something that required email
    address confirmation, but that confirmation is already concluded.
    """

    PAGES = {LoginTokenType.PASSWORDRECOVERY: '+resetpassword',
             LoginTokenType.ACCOUNTMERGE: '+accountmerge',
             LoginTokenType.NEWACCOUNT: '+newaccount',
             LoginTokenType.NEWPROFILE: '+newaccount',
             LoginTokenType.VALIDATEEMAIL: '+validateemail',
             LoginTokenType.VALIDATETEAMEMAIL: '+validateteamemail',
             LoginTokenType.VALIDATEGPG: '+validategpg',
             LoginTokenType.VALIDATESIGNONLYGPG: '+validatesignonlygpg',
             LoginTokenType.PROFILECLAIM: '+claimprofile',
             }

    def render(self):
        if self.context.date_consumed is None:
            url = urllib.basejoin(
                str(self.request.URL), self.PAGES[self.context.tokentype])
            self.request.response.redirect(url)
        else:
            return LaunchpadView.render(self)


class BaseLoginTokenView:
    """A view class to be used by other LoginToken views."""

    expected_token_types = ()
    successfullyProcessed = False
    errormessage = ""

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

    def assertNoErrors(self):
        assert not self.errormessage, \
               'token processing can not succeed with an error message set'

    def success(self, message):
        """Indicate to the user that the token has been successfully processed.

        This involves adding a notification message, and redirecting the
        user to their Launchpad page.
        """
        self.assertNoErrors()
        self.successfullyProcessed = True
        self.request.response.addInfoNotification(message)

    def logInPersonByEmail(self, email):
        """Login the person with the given email address."""
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        logInPerson(self.request, principal, email)


class ClaimProfileView(BaseLoginTokenView, LaunchpadFormView):

    schema = IPerson
    field_names = ['displayname', 'hide_email_addresses', 'password']
    custom_widget('password', PasswordChangeWidget)
    label = 'Claim Launchpad profile'
    expected_token_types = (LoginTokenType.PROFILECLAIM,)
    claimed_profile = None

    def initialize(self):
        if not self.redirectIfInvalidOrConsumedToken():
            self.claimed_profile = getUtility(IEmailAddressSet).getByEmail(
                self.context.email).person
            LaunchpadFormView.initialize(self)

    @property
    def initial_values(self):
        return {'displayname': self.claimed_profile.displayname}

    @property
    def next_url(self):
        return canonical_url(self.claimed_profile)

    @action(_('Continue'), name='confirm')
    def confirm_action(self, action, data):
        email = getUtility(IEmailAddressSet).getByEmail(self.context.email)
        # The user is not yet logged in, but we need to set some
        # things on his new account, so we need to remove the security
        # proxy from it.
        # XXX: We should be able to login with this person and set the
        # password, to avoid removing the security proxy, but it didn't
        # work, so I'm leaving this hack for now.
        # https://launchpad.net/bugs/62674
        # -- Guilherme Salgado, 2006-09-27
        from zope.security.proxy import removeSecurityProxy
        naked_person = removeSecurityProxy(email.person)
        naked_person.displayname = data['displayname']
        naked_person.hide_email_addresses = data['hide_email_addresses']
        naked_person.password = data['password']

        email.person.validateAndEnsurePreferredEmail(email)
        self.context.consume()
        self.logInPersonByEmail(email.email)
        self.success(_("Profile claimed successfully"))


class ResetPasswordView(BaseLoginTokenView, GeneralFormView):

    def initialize(self):
        self.email = None
        self.expected_token_types = (LoginTokenType.PASSWORDRECOVERY,)
        self.top_of_page_errors = []
        self.redirectIfInvalidOrConsumedToken()

    def validate(self, form_values):
        """Validate the email address."""
        email = form_values.get("email").strip()
        # All operations with email addresses must be case-insensitive. We
        # enforce that in EmailAddressSet, but here we only do a comparison,
        # so we have to .lower() them first.
        if email.lower() != self.context.email.lower():
            self.top_of_page_errors.append(
                "The email address you provided didn't match the address "
                "you provided when requesting the password reset.")
            raise WidgetsError(self.top_of_page_errors)

    def assertNoErrors(self):
        assert not self.top_of_page_errors and not self.errors, \
               'token processing can not succeed with an error message set'

    def nextURL(self):
        return canonical_url(self.context.requester)

    def process(self, password, email):
        """Reset the user's password. When password is successfully changed,
        the LoginToken (self.context) used is removed, so nobody can use
        it again.
        """
        emailset = getUtility(IEmailAddressSet)
        emailaddress = emailset.getByEmail(self.context.email)
        person = emailaddress.person

        # XXX: It should be possible to do the login before this and avoid
        # this hack. In case the user doesn't want to be logged in
        # automatically we can log him out after doing what we want.
        # https://launchpad.net/bugs/62674
        # XXX: Steve Alexander, 2005-03-18
        #      Local import, because I don't want this import copied elsewhere!
        #      This code is to be removed when the UpgradeToBusinessClass
        #      specification is implemented.
        from zope.security.proxy import removeSecurityProxy
        naked_person = removeSecurityProxy(person)
        #      end of evil code.

        # Make sure this person has a preferred email address.
        if naked_person.preferredemail != emailaddress:
            naked_person.validateAndEnsurePreferredEmail(emailaddress)

        naked_person.password = password
        self.context.consume()

        if self.request.form.get('logmein'):
            self.logInPersonByEmail(self.context.email)

        self.success(_('Your password has been reset successfully'))


class ValidateEmailView(BaseLoginTokenView, LaunchpadView):

    def initialize(self):
        self.expected_token_types = (LoginTokenType.VALIDATEEMAIL,
                                     LoginTokenType.VALIDATETEAMEMAIL,
                                     LoginTokenType.VALIDATEGPG,
                                     LoginTokenType.VALIDATESIGNONLYGPG)

    def success(self, message):
        # We're not a GeneralFormView, so we need to do the redirect
        # ourselves.
        BaseLoginTokenView.success(self, message)
        self.request.response.redirect(canonical_url(self.context.requester))

    def render(self):
        if not self.redirectIfInvalidOrConsumedToken():
            return LaunchpadView.render(self)

    def processForm(self):
        """Process the action specified by the LoginToken.

        If necessary, verify the requester's password before actually
        processing anything.
        """
        if self.request.method != "POST":
            return

        if self.context.tokentype == LoginTokenType.VALIDATETEAMEMAIL:
            self.setTeamContactAddress()
            if not self.errormessage:
                self.success(_('Contact email address validated successfully'))
        elif self.context.tokentype == LoginTokenType.VALIDATEEMAIL:
            self.markEmailAddressAsValidated()
            if not self.errormessage:
                self.success(_('Email address successfully confirmed'))
        elif self.context.tokentype == LoginTokenType.VALIDATEGPG:
            self.validateGpg()
        elif self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
            self.validateSignOnlyGpg()
        else:
            # Nothing to do
            pass

    def setTeamContactAddress(self):
        """Set the new email address as the team's contact email address.

        Make sure that the new email address is owned by the team, if it
        already exists, set it as the team's contact address (removing any
        previous contact address) and remove the logintoken used to validate
        this email address.
        """
        requester = self.context.requester
        email = self._ensureEmail(self.context.email)
        if email is not None:
            if requester.preferredemail is not None:
                requester.preferredemail.destroySelf()
            requester.setPreferredEmail(email)

        self.context.consume()

    def markEmailAddressAsValidated(self):
        """Mark the new email address as VALIDATED in the database.

        If this is the first validated email of this person, it'll be marked
        as the preferred one.
        """
        email = self._ensureEmail(self.context.email)
        requester = self.context.requester
        if email is not None:
            requester.validateAndEnsurePreferredEmail(email)

        self.context.consume()

    def validateGpg(self):
        """Validate a gpg key."""
        key = self._getGPGKey()
        if not key:
            return

        self._activateGPGKey(key, can_encrypt=True)

    def validateSignOnlyGpg(self):
        """Validate a gpg key."""
        gpghandler = getUtility(IGPGHandler)

        # retrieve respective key info
        key = self._getGPGKey()
        if not key:
            return

        fingerprint = self.context.fingerprint

        # verify the signed content
        signedcontent = self.request.form.get('signedcontent', '')
        try:
            signature = gpghandler.getVerifiedSignature(
                signedcontent.encode('ASCII'))
        except (GPGVerificationError, UnicodeEncodeError), e:
            self.errormessage = (
                'Launchpad could not verify your signature: %s'
                % str(e))
            return

        if signature.fingerprint != fingerprint:
            self.errormessage = (
                'The key used to sign the content (%s) is not the key '
                'you were registering' % signature.fingerprint)
            return
            
        # we compare the word-splitted content to avoid failures due
        # to whitepace differences.
        if signature.plain_data.split() != self.validationphrase.split():
            self.errormessage = (
                'The signed content does not match the message found '
                'in the email.')
            return

        self._activateGPGKey(key, can_encrypt=False)

    @property
    def validationphrase(self):
        """The phrase used to validate sign-only GPG keys"""
        utctime = self.context.created.astimezone(UTC)
        return 'Please register %s to the\nLaunchpad user %s.  %s UTC' % (
            self.context.fingerprint, self.context.requester.name,
            utctime.strftime('%Y-%m-%d %H:%M:%S'))


    def _getGPGKey(self):
        """Look up the OpenPGP key for this login token.

        If the key can not be retrieved from the keyserver, the key
        has been revoked or expired, None is returned and
        self.errormessage is set appropriately.
        """
        gpghandler = getUtility(IGPGHandler)

        requester = self.context.requester
        fingerprint = self.context.fingerprint
        assert fingerprint is not None

        person_url = canonical_url(requester)
        try:
            key = gpghandler.retrieveKey(fingerprint)
        except GPGKeyNotFoundError:
            self.errormessage = (
                'Launchpad could not import this OpenPGP key, because %s. '
                'Check that you published it correctly in the global key ring '
                '(using <kbd>gpg --send-keys KEY</kbd>) and that you '
                'entered the fingerprint correctly (as produced by <kbd>'
                'gpg --fingerprint YOU</kdb>). Try later or '
                '<a href="%s/+editpgpkeys">cancel your request</a>.'
                % (key, person_url))
            return None

        # if key is globally revoked skip import and remove token
        if key.revoked:
            self.errormessage = (
                'The key %s cannot be validated because it has been '
                'publicly revoked. You will need to generate a new key '
                '(using <kbd>gpg --genkey</kbd>) and repeat the previous '
                'process to <a href="%s/+editpgpkeys">find and import</a> '
                'the new key.' % (key.keyid, person_url))
            self.context.consume()
            return None

        if key.expired:
            self.errormessage = (
                'The key %s cannot be validated because it has expired. '
                'Change the expiry date (in a terminal, enter '
                '<kbd>gpg --edit-key <var>your@e-mail.address</var></kbd> '
                'then enter <kbd>expire</kbd>), and try again.' % key.keyid)
            self.context.consume()
            return None

        return key

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
            self.success('Key %s successfully reactivated. '
                         '<a href="%s/+editpgpkeys">See more Information</a>'
                         % (lpkey.displayname, person_url))
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
        infomessage = (
            "The key %s was successfully validated. " % (lpkey.displayname))
        guessed, hijacked = self._guessGPGEmails(key.emails)

        if len(guessed):
            # build email list
            emails = ' '.join([email.email for email in guessed]) 

            infomessage += (
                '<p>Some email addresses were found in your key but are '
                'not registered with Launchpad:<code>%s</code>. If you '
                'want to use these addressess with Launchpad, you need to '
                '<a href="%s/+editemails\">confirm them</a>.</p>'
                % (emails, person_url))

        if len(hijacked):
            # build email list
            emails = ' '.join([email.email for email in hijacked]) 
            infomessage += (
                "<p>Also some of them were registered into another "
                "account(s):<code>%s</code>. Those accounts, probably "
                "already belong to you, in this case you should be able to "
                "<a href=\"/people/+requestmerge\">merge them</a> into your "
                "current account.</p>"
                % emails
                )

        self.success(infomessage)

    def _guessGPGEmails(self, uids):
        """Figure out which emails from the GPG UIDs are unknown in LP
        context, add them as NEW EmailAddresses (guessed) and return a
        list containing the just added address for UI feedback.
        """
        emailset = getUtility(IEmailAddressSet)
        requester = self.context.requester
        # build a list of already validated and preferred emailaddress
        # in lowercase for comparision reasons
        emails = set(email.email.lower() 
                     for email in requester.validatedemails)
        emails.add(requester.preferredemail.email.lower())

        guessed = []
        hijacked = []
        # iter through UIDs
        for uid in uids:
            # if UID isn't validated/preferred, append it to list
            if uid.lower() not in emails:
                # verify if the email isn't owned by other person.
                lpemail = emailset.getByEmail(uid)
                if lpemail:
                    hijacked.append(lpemail)
                    continue
                # store guessed email address with status NEW
                email = emailset.new(uid, requester)
                guessed.append(email)

        return guessed, hijacked

    def _ensureEmail(self, emailaddress):
        """Make sure self.requester has <emailaddress> as one of its email
        addresses with status NEW and return it."""
        validated = (EmailAddressStatus.VALIDATED, EmailAddressStatus.PREFERRED)
        requester = self.context.requester

        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(emailaddress)
        if email is not None:
            if email.person.id != requester.id:
                dupe = email.person
                # Yes, hardcoding an autogenerated field name is an evil 
                # hack, but if it fails nothing will happen.
                # -- Guilherme Salgado 2005-07-09
                url = '/people/+requestmerge?field.dupeaccount=%s' % dupe.name
                self.errormessage = (
                        'This email address is already registered for another '
                        'Launchpad user account. This account can be a '
                        'duplicate of yours, created automatically, and '
                        'in this case you should be able to '
                        '<a href="%s">merge them</a> into a single one.' % url)
                return None

            elif email.status in validated:
                self.errormessage = (
                        "This email address is already registered and "
                        "validated for your Launchpad account. There's "
                        "no need to validate it again.")
                return None

            else:
                return email

        # New email validated by the user. We must add it to our emailaddress
        # table.
        email = emailset.new(emailaddress, requester)
        return email


class NewAccountView(BaseLoginTokenView, GeneralFormView):
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
        UBUNTU_WIKI_URL: PersonCreationRationale.OWNER_CREATED_UBUNTU_WIKI}

    created_person = None

    def initialize(self):
        self.expected_token_types = (
            LoginTokenType.NEWACCOUNT, LoginTokenType.NEWPROFILE)
        self.top_of_page_errors = []
        self.redirectIfInvalidOrConsumedToken()
        self.email = getUtility(IEmailAddressSet).getByEmail(
            self.context.email)

    def assertNoErrors(self):
        assert not self.top_of_page_errors and not self.errors, (
           'token processing can not succeed with an error message set')

    def nextURL(self):
        if self.context.redirection_url:
            return self.context.redirection_url
        elif self.user is not None:
            # User is logged in, redirect to his home page.
            return canonical_url(self.user)
        elif self.created_person is not None:
            # User is not logged in, redirect to the created person's home
            # page.
            return canonical_url(self.created_person)
        else:
            return None

    def validate(self, form_values):
        """Verify if the email address is not used by an existing account."""
        if self.email is not None and self.email.person.is_valid_person:
            self.top_of_page_errors.append(_(
                'The email address %s is already registered.'
                % self.context.email))
            raise WidgetsError(self.top_of_page_errors)

    def process(self, displayname, hide_email_addresses, password):
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
            person = self.email.person
            assert not person.is_valid_person, (
                'Account %s has already been claimed and this should '
                'have been caught by the validate() method.' % person.name)
            email = self.email
            # The user is not yet logged in, but we need to set some
            # things on his new account, so we need to remove the security
            # proxy from it.
            # XXX: We should be able to login with this person and set the
            # password, to avoid removing the security proxy, but it didn't
            # work, so I'm leaving this hack for now.
            # https://launchpad.net/bugs/62674
            # -- Guilherme Salgado, 2006-09-27
            from zope.security.proxy import removeSecurityProxy
            naked_person = removeSecurityProxy(person)
            naked_person.displayname = displayname
            naked_person.hide_email_addresses = hide_email_addresses
            naked_person.password = password
            naked_person.creation_rationale = self._getCreationRationale()
            naked_person.creation_comment = None
        else:
            person, email = self._createPersonAndEmail(
                displayname, hide_email_addresses, password)

        self.created_person = person
        person.validateAndEnsurePreferredEmail(email)
        self.context.consume()
        self.logInPersonByEmail(email.email)
        self.success(_("Registration completed successfully"))

    def _getCreationRationale(self):
        """Return the creation rationale that should be used for this person.

        If there's a rationale for the logintoken's redirection_url, then use
        it, otherwise uses PersonCreationRationale.OWNER_CREATED_LAUNCHPAD.
        """
        rationale = self.urls_and_rationales.get(self.context.redirection_url)
        if rationale is None:
            rationale = PersonCreationRationale.OWNER_CREATED_LAUNCHPAD
        return rationale

    def _createPersonAndEmail(
            self, displayname, hide_email_addresses, password):
        """Create and return a new Person and EmailAddress.

        Use the given arguments and the email address stored in the
        LoginToken (our context).

        Also fire ObjectCreatedEvents for both the newly created Person
        and EmailAddress.
        """
        rationale = self._getCreationRationale()
        person, email = getUtility(IPersonSet).createPersonAndEmail(
            self.context.email, rationale, displayname=displayname,
            password=password, passwordEncrypted=True,
            hide_email_addresses=hide_email_addresses)

        notify(ObjectCreatedEvent(person))
        notify(ObjectCreatedEvent(email))
        return person, email


class MergePeopleView(BaseLoginTokenView, LaunchpadView):

    def initialize(self):
        self.expected_token_types = (LoginTokenType.ACCOUNTMERGE,)
        self.mergeCompleted = False
        self.dupe = getUtility(IPersonSet).getByEmail(self.context.email)

    def render(self):
        if not self.redirectIfInvalidOrConsumedToken():
            return LaunchpadView.render(self)

    def success(self, message):
        # We're not a GeneralFormView, so we need to do the redirect
        # ourselves.
        BaseLoginTokenView.success(self, message)
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
                'belonged to the duplicated account should now belong to your '
                'own account.'))
        else:
            self.success(_(
                'The e-mail address %s has been assigned to you, but the '
                'duplicate account you selected has other registered e-mail '
                'addresses too. To complete the merge, you have to prove that '
                'you have access to all those e-mail addresses.' 
                % self.context.email))
        self.context.consume()

    def _doMerge(self):
        # The user proved that he has access to this email address of the
        # dupe account, so we can assign it to him.
        requester = self.context.requester
        emailset = getUtility(IEmailAddressSet)
        email = emailset.getByEmail(self.context.email)
        email.person = requester.id
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


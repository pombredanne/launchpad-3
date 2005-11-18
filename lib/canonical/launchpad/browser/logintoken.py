# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'LoginTokenSetNavigation',
    'LoginTokenView',
    'ResetPasswordView',
    'ValidateEmailView',
    'NewAccountView',
    'MergePeopleView',
    ]

import urllib
import pytz

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.database.sqlbase import flush_database_updates

from canonical.lp.dbschema import EmailAddressStatus, LoginTokenType
from canonical.lp.dbschema import GPGKeyAlgorithm

from canonical.launchpad import _
from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPerson
from canonical.launchpad.webapp import canonical_url, GetitemNavigation

from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, IPasswordEncryptor, ILoginTokenSet,
    IGPGKeySet, IGPGHandler, GPGVerificationError)

UTC = pytz.timezone('UTC')


class LoginTokenSetNavigation(GetitemNavigation):

    usedfor = ILoginTokenSet


class LoginTokenView:
    """The default view for LoginToken.

    This view will check the token type and then redirect to the specific view
    for that type of token. We use this view so we don't have to add
    "+validateemail", "+newaccount", etc, on URLs we send by email.
    """

    PAGES = {LoginTokenType.PASSWORDRECOVERY: '+resetpassword',
             LoginTokenType.ACCOUNTMERGE: '+accountmerge',
             LoginTokenType.NEWACCOUNT: '+newaccount',
             LoginTokenType.VALIDATEEMAIL: '+validateemail',
             LoginTokenType.VALIDATETEAMEMAIL: '+validateteamemail',
             LoginTokenType.VALIDATEGPG: '+validategpg',
             LoginTokenType.VALIDATESIGNONLYGPG: '+validatesignonlygpg',
             }

    def __init__(self, context, request):
        self.context = context
        self.request = request
        url = urllib.basejoin(str(request.URL),
                              self.PAGES[context.tokentype])
        request.response.redirect(url)


class BaseLoginTokenView:
    """A base view class to be used by other LoginToken views."""

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.errormessage = ""
        self.formProcessed = False

    def successfullyProcessed(self):
        """Return True if the form was processed without any errors."""
        return self.formProcessed and not self.errormessage

    def validateRequesterPassword(self, password):
        """Return True if <password> is the same as the requester's password.

        In case of failure, an error message is assigned to self.errormessage.
        """
        assert self.context.requester is not None
        encryptor = getUtility(IPasswordEncryptor)
        if encryptor.validate(password, self.context.requester.password):
            return True
        else:
            self.errormessage = "Wrong password. Please check and try again."
            return False

    def logInPersonByEmail(self, email):
        """Login the person with the given email address."""
        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email)
        logInPerson(self.request, principal, email)


class ResetPasswordView(BaseLoginTokenView):

    def __init__(self, context, request):
        BaseLoginTokenView.__init__(self, context, request)
        self.email = None

    def processForm(self):
        """Check the email address, check if both passwords match and then
        reset the user's password. When password is successfully changed, the
        LoginToken (self.context) used is removed, so nobody can use it again.
        """
        if self.request.method != "POST":
            return

        form = self.request.form
        self.email = form.get("email").strip()
        # All operations with email addresses must be case-insensitive. We
        # enforce that in EmailAddressSet, but here we only do a comparison,
        # so we have to .lower() them first.
        if self.email.lower() != self.context.email.lower():
            self.errormessage = (
                "The email address you provided didn't match the address "
                "you provided when requesting the password reset.")
            return

        password = form.get("password")
        password2 = form.get("password2")
        if not password and not password2:
            self.errormessage = "Your password cannot be empty."
            return

        if password != password2:
            self.errormessage = "Password didn't match."
            return

        emailset = getUtility(IEmailAddressSet)
        emailaddress = emailset.getByEmail(self.context.email)
        person = emailaddress.person

        # XXX: It should be possible to do the login before this and avoid
        # this hack. In case the user doesn't want to be logged in
        # automatically we can log him out after doing what we want.
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

        encryptor = getUtility(IPasswordEncryptor)
        password = encryptor.encrypt(password)
        naked_person.password = password
        self.formProcessed = True
        self.context.destroySelf()

        if form.get('logmein'):
            self.logInPersonByEmail(self.context.email)

        self.request.response.addInfoNotification(
                _('Your password has successfully been reset'))
        self.request.response.redirect(canonical_url(
                self.context.requester))


class ValidateEmailView(BaseLoginTokenView):

    def __init__(self, context, request):
        BaseLoginTokenView.__init__(self, context, request)
        self.infomessage = ""

    def processForm(self):
        """Process the action specified by the LoginToken.

        If necessary, verify the requester's password before actually
        processing anything.
        """
        if self.request.method != "POST":
            return

        self.formProcessed = True
        if self.context.tokentype == LoginTokenType.VALIDATETEAMEMAIL:
            self.setTeamContactAddress()
            self.request.response.addInfoNotification(
                _('Contact email address validated successfully'))
            self.request.response.redirect(
                canonical_url(self.context.requester))
            return

        password = self.request.form.get("password")
        if not self.validateRequesterPassword(password):
            return

        if self.context.tokentype == LoginTokenType.VALIDATEEMAIL:
            self.markEmailAddressAsValidated()
            self.request.response.addInfoNotification(
                _('Email address successfully confirmed'))
        elif self.context.tokentype == LoginTokenType.VALIDATEGPG:
            self.validateGpg()
        elif self.context.tokentype == LoginTokenType.VALIDATESIGNONLYGPG:
            self.validateSignOnlyGpg()

        if self.successfullyProcessed():
            self.request.response.addInfoNotification(_(self.infomessage))
            self.request.response.redirect(
                canonical_url(self.context.requester))

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
            requester.preferredemail = email

        # At this point, either this email address is validated or it can't be
        # validated for this team because it's owned by someone else in
        # Launchpad, so we can safely delete all logintokens for this team 
        # and this email address.
        logintokenset = getUtility(ILoginTokenSet)
        logintokenset.deleteByEmailAndRequester(self.context.email, requester)

    def markEmailAddressAsValidated(self):
        """Mark the new email address as VALIDATED in the database.

        If this is the first validated email of this person, it'll be marked
        as the preferred one.
        """
        email = self._ensureEmail(self.context.email)
        requester = self.context.requester
        if email is not None:
            requester.validateAndEnsurePreferredEmail(email)
            if self.request.form.get('logmein'):
                self.logInPersonByEmail(email.email)

        # At this point, either this email address is validated or it can't be
        # validated for this user because it's owned by someone else in
        # Launchpad, so we can safely delete all logintokens for this user 
        # and this email address.
        logintokenset = getUtility(ILoginTokenSet)
        logintokenset.deleteByEmailAndRequester(self.context.email, requester)

    def validateGpg(self):
        """Validate a gpg key."""
        if self.request.form.get('logmein'):
            self.logInPersonByEmail(self.context.requesteremail)

        requester = self.context.requester

        # retrieve respective key info
        key = self._getGPGKey()
        if not key:
            return

        self._activateGPGKey(key, can_encrypt=False)

    def validateSignOnlyGpg(self):
        """Validate a gpg key."""
        if self.request.form.get('logmein'):
            self.logInPersonByEmail(self.context.requesteremail)

        requester = self.context.requester
        person_url = canonical_url(requester)

        logintokenset = getUtility(ILoginTokenSet)
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
        logintokenset = getUtility(ILoginTokenSet)
        gpghandler = getUtility(IGPGHandler)

        requester = self.context.requester
        fingerprint = self.context.fingerprint
        assert fingerprint is not None

        # retrieve respective key info
        result, key = gpghandler.retrieveKey(fingerprint)

        person_url = canonical_url(requester)
        if not result:
            self.errormessage = (
                'Launchpad could not import GPG key, the reason was: %s .'
                'Check if you published it correctly in the global key ring '
                '(using <kbd>gpg --send-keys KEY</kbd>) and that you '
                'entered the fingerprint correctly (as produced by <kbd>'
                'gpg --fingerprint YOU</kdb>). Try later or '
                '<a href="%s/+editgpgkeys">cancel your request</a>.'
                % (key, person_url))
            return None

        # if key is globally revoked skip import and remove token
        if key.revoked:
            self.errormessage = (
                'The key %s cannot be validated because it has been '
                'publicly revoked. You will need to generate a new key '
                '(using <kbd>gpg --genkey</kbd>) and repeat the previous '
                'process to <a href="%s/+editgpgkeys">find and import</a> '
                'the new key.' % (key.keyid, person_url))
            logintokenset.deleteByFingerprintAndRequester(fingerprint,
                                                          requester)
            return None

        if key.expired:
            self.errormessage = (
                'The key %s cannot be validated because it has expired. '
                'You will need to generate a new key '
                '(using <kbd>gpg --genkey</kbd>) and repeat the previous '
                'process to <a href="%s/+editgpgkeys">find and import</a> '
                'the new key.' % (key.keyid, person_url))
            logintokenset.deleteByFingerprintAndRequester(fingerprint,
                                                          requester)
            return None

        return key

    def _activateGPGKey(self, key, can_encrypt):
        logintokenset = getUtility(ILoginTokenSet)
        gpgkeyset = getUtility(IGPGKeySet)

        fingerprint = key.fingerprint
        requester = self.context.requester
        person_url = canonical_url(requester)

        # Is it a revalidation ?
        lpkey = gpgkeyset.getByFingerprint(fingerprint)

        if lpkey:
            lpkey.active = True
            lpkey.can_encrypt = can_encrypt
            self.infomessage = (
                'The key %s was successfully revalidated. '
                '<a href="%s/+editgpgkeys">See more Information</a>'
                % (lpkey.displayname, person_url))
            self.formProcessed = True

            logintokenset.deleteByFingerprintAndRequester(fingerprint,
                                                          requester)
            return

        # Otherwise prepare to add
        ownerID = self.context.requester.id
        keyid = key.keyid
        keysize = key.keysize
        algorithm = GPGKeyAlgorithm.items[key.algorithm]

        # Add new key in DB. See IGPGKeySet for further information
        lpkey = gpgkeyset.new(ownerID, keyid, fingerprint, keysize, algorithm,
                              can_encrypt=can_encrypt)

        logintokenset.deleteByFingerprintAndRequester(fingerprint, requester)

        self.infomessage = (
            "The key %s was successfully validated. " % (lpkey.displayname))

        self.formProcessed = True

        guessed, hijacked = self._guessGPGEmails(key.emails)

        if len(guessed):
            # build email list
            emails = ' '.join([email.email for email in guessed]) 

            self.infomessage += (
                '<p>Some e-mail addresses were found in your key but are '
                'not registered with Launchpad:<code>%s</code>. If you '
                'want to use these addressess with Launchpad, you need to '
                '<a href="%s/+editemails\">confirm them</a>.</p>'
                % (emails, person_url))

        if len(hijacked):
            # build email list
            emails = ' '.join([email.email for email in hijacked]) 
            self.infomessage += (
                "<p>Also some of them were registered into another "
                "account(s):<code>%s</code>. Those accounts, probably "
                "already belong to you, in this case you should be able to "
                "<a href=\"/people/+requestmerge\">merge them</a> into your "
                "current account.</p>"
                % emails
                )

    def _guessGPGEmails(self, uids):
        """Figure out which emails from the GPG UIDs are unknown in LP
        context, add them as NEW EmailAddresses (guessed) and return a
        list containing the just added address for UI feedback.
        """
        emailset = getUtility(IEmailAddressSet)
        requester = self.context.requester
        # build a list of already validated and preferred emailaddress
        # in lowercase for comparision reasons
        emails = set(email.email.lower() for email in
                     requester.validatedemails)
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
                email = emailset.new(uid, requester.id)
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
                        'This email is already registered for another '
                        'Launchpad user account. This account can be a '
                        'duplicate of yours, created automatically, and '
                        'in this case you should be able to '
                        '<a href="%s">merge them</a> into a single one.' % url)
                return None

            elif email.status in validated:
                self.errormessage = (
                        "This email is already registered and validated "
                        "for your Launchpad account. There's no need to "
                        "validate it again.")
                return None

            else:
                return email

        # New email validated by the user. We must add it to our emailaddress
        # table.
        email = emailset.new(emailaddress, requester.id)
        return email


class NewAccountView(AddView, BaseLoginTokenView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        """Check if both passwords match and then create a new Person.
        When everything went ok, we delete the LoginToken (self.context) from
        the database, so nobody can use it again.
        """
        person, email = getUtility(IPersonSet).createPersonAndEmail(
                self.context.email, displayname=data['displayname'], 
                givenname=data['givenname'], familyname=data['familyname'],
                password=data['password'], passwordEncrypted=True)

        notify(ObjectCreatedEvent(person))
        notify(ObjectCreatedEvent(email))

        person.validateAndEnsurePreferredEmail(email)
        self._nextURL = canonical_url(person)
        self.context.destroySelf()
        getUtility(ILoginTokenSet).deleteByEmailAndRequester(
            email.email, requester=None)
        self.logInPersonByEmail(email.email)
        return True


class MergePeopleView(BaseLoginTokenView):

    def __init__(self, context, request):
        BaseLoginTokenView.__init__(self, context, request)
        self.mergeCompleted = False
        self.dupe = getUtility(IPersonSet).getByEmail(context.email)

    def processForm(self):
        """Check if the password is correct and perform the merge."""
        if self.request.method != "POST":
            return

        # Merge requests must have a valid user account (one with a preferred
        # email) as requester.
        assert self.context.requester.preferredemail is not None
        self.formProcessed = True
        if self.validateRequesterPassword(self.request.form.get("password")):
            self._doMerge()
            if self.mergeCompleted: 
                self.request.response.addInfoNotification(
                        _('The merge you requested was concluded with success. '
                          'Now, everything that was owned by the duplicated ' 
                          'account should be owned by your user account.'))
            else:
                self.request.response.addInfoNotification(
                        _('The email address %s have been assigned to you, but '
                          'the dupe account you selected still have more ' 
                          'registered email addresses. In order to actually ' 
                          'complete the merge, you have to prove that you have '
                          'access to all email addresses of that account.' %
                          self.context.email))
            self.request.response.redirect(
                    canonical_url(self.context.requester))
            self.context.destroySelf()

    def _doMerge(self):
        # The user proved that he has access to this email address of the
        # dupe account, so we can assign it to him.
        requester = self.context.requester
        email = getUtility(IEmailAddressSet).getByEmail(self.context.email)
        email.person = requester.id
        requester.validateAndEnsurePreferredEmail(email)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()

        if self.request.form.get('logmein'):
            self.logInPersonByEmail(email.email)

        # Now we must check if the dupe account still have registered email
        # addresses. If it hasn't we can actually do the merge.
        if getUtility(IEmailAddressSet).getByPerson(self.dupe):
            self.mergeCompleted = False
            return

        # Call Stuart's magic function which will reassign all of the dupe
        # account's stuff to the user account.
        getUtility(IPersonSet).merge(self.dupe, requester)
        self.mergeCompleted = True


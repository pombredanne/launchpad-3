# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'LoginTokenView',
    'ResetPasswordView',
    'ValidateEmailView',
    'NewAccountView',
    'MergePeopleView',
    ]

import urllib

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.database.sqlbase import flush_database_updates

from canonical.lp.dbschema import EmailAddressStatus, LoginTokenType
from canonical.lp.dbschema import GPGKeyAlgorithm

from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPerson
from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.interfaces import (
    IPersonSet, IEmailAddressSet, IPasswordEncryptor, ILoginTokenSet,
    IGPGKeySet, IGpgHandler, ILaunchBag)


class LoginTokenView(object):
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
             LoginTokenType.VALIDATEGPG: '+validategpg'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        url = urllib.basejoin(str(request.URL),
                              self.PAGES[context.tokentype])
        request.response.redirect(url)


class ResetPasswordView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.formProcessed = False
        self.email = None

    def processForm(self):
        """Check the email address, check if both passwords match and then
        reset the user's password. When password is successfully changed, the
        LoginToken (self.context) used is removed, so nobody can use it again.

        """
        if self.request.method != "POST":
            return

        self.email = self.request.form.get("email").strip()
        if self.email != self.context.email:
            self.errormessage = (
                "The email address you provided didn't match the address "
                "you provided when requesting the password reset.")
            return

        password = self.request.form.get("password")
        password2 = self.request.form.get("password2")
        if not password and not password2:
            self.errormessage = "Your password cannot be empty."
            return

        if password != password2:
            self.errormessage = "Password didn't match."
            return

        # Make sure this person has a preferred email address.
        emailset = getUtility(IEmailAddressSet)
        emailaddress = emailset.getByEmail(self.context.email)
        person = emailaddress.person
        if person.preferredemail != emailaddress:
            person.validateAndEnsurePreferredEmail(emailaddress)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()

        # XXX: Steve Alexander, 2005-03-18
        #      Local import, because I don't want this import copied elsewhere!
        #      This code is to be removed when the UpgradeToBusinessClass
        #      specification is implemented.
        from zope.security.proxy import removeSecurityProxy
        naked_person = removeSecurityProxy(person)
        #      end of evil code.

        encryptor = getUtility(IPasswordEncryptor)
        password = encryptor.encrypt(password)
        naked_person.password = password
        self.formProcessed = True
        self.context.destroySelf()

    def successfullyProcessed(self):
        return self.formProcessed and not self.errormessage


class ValidateEmailView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.errormessage = ""
        self.infomessage = ""
        self.formProcessed = False

    def successfullyProcessed(self):
        return self.formProcessed and not self.errormessage

    def processForm(self):
        if self.request.method != "POST":
            return

        # Email validation requests must have a registered requester.
        assert self.context.requester is not None
        self.formProcessed = True
        if self.context.tokentype == LoginTokenType.VALIDATEEMAIL:
            self.validatePersonEmail()
        elif self.context.tokentype == LoginTokenType.VALIDATETEAMEMAIL:
            self.validateTeamEmail()
        elif self.context.tokentype == LoginTokenType.VALIDATEGPG:
            self.validateGpg()

    def validateTeamEmail(self):
        """Set the new email address as the team's contact email address."""
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

    def validatePersonEmail(self):
        """Check the password and validate a person's email address."""
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please check and try again."
            return 

        email = self._ensureEmail(self.context.email)
        if email is not None:
            requester.validateAndEnsurePreferredEmail(email)

        # At this point, either this email address is validated or it can't be
        # validated for this user because it's owned by someone else in
        # Launchpad, so we can safely delete all logintokens for this user 
        # and this email address.
        logintokenset = getUtility(ILoginTokenSet)
        logintokenset.deleteByEmailAndRequester(self.context.email, requester)

    def validateGpg(self):
        """Check the password and validate a gpg key."""
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please check and try again."
            return

        fingerprint = self.context.fingerprint

        gpgkeyset = getUtility(IGPGKeySet)
        logintokenset = getUtility(ILoginTokenSet)
        # No fingerprint, is it plausible ??
        if fingerprint == None:
            self.errormessage = (
                "Launchpad could not register this token because it has no "
                "fingerprint information. Check you entered it correctly, "
                "and try again.")
            return

        # retrieve respective key info
        gpghandler = getUtility(IGpgHandler)
        result, key = gpghandler.retrieveKey(fingerprint)

        if not result:
            self.errormessage = (
                "Launchpad could not import GPG key, the reason was: %s ."
                "Check if you published it correctly in the global key ring "
                "(using <kbd>gpg --send-keys KEY</kbd>) and that you add "
                "entered the fingerprint correctly (as produced by <kbd>"
                "gpg --fingerprint YOU</kdb>). Try later or <a href=\"/people"
                "/%s/+editgpgkey\">cancel your request</a>."
                % (key, requester.name))
            return        

        # Is it a revalidation ?
        lpkey = gpgkeyset.getByFingerprint(fingerprint)
        
        if lpkey:            
            # if key is globally revoked skip import and remove token
            if key.revoked:
                self.errormessage = (
                    "The key %s cannot be revalidated, because it has been"
                    "publicly revoked. You will need to generate a new key"
                    "(using <kbd>gpg --genkey</kbd>) and repeat the previous "
                    "process to <a href=\"/people/%s/+editgpgkey\">find and "
                    "import</a> the new key."% (lpkey.displayname,
                                                requester.name))
            else:
                gpgkeyset.activateGpgKey(lpkey.id)
                self.infomessage = (
                    "The key %s was successfully revalidated. <a href=\"/"
                    "people/%s/+editgpgkey\">See more Information</a>"
                    % (lpkey.displayname, requester.name))
                self.formProcessed = True

            logintokenset.deleteByFingerprintAndRequester(fingerprint,
                                                          requester)
            
            return

        # Otherwise prepare to add
        ownerID = self.context.requester.id
        fingerprint = key.fingerprint
        keyid = key.keyid
        keysize = key.keysize
        algorithm = GPGKeyAlgorithm.items[key.algorithm]

        # Add new key in DB. See IGPGKeySet for further information
        lpkey = gpgkeyset.new(ownerID, keyid, fingerprint, keysize, algorithm)

        logintokenset.deleteByFingerprintAndRequester(fingerprint, requester)

        self.infomessage = (
            "The key %s was successfully validated. " % (lpkey.displayname))

        self.formProcessed = True

        guessed, hijacked = self._guessGpgEmails(key.uids)

        if len(guessed):
            # build email list
            emails = ' '.join([email.email for email in guessed]) 

            self.infomessage += (
                "<p>Some e-mail addresses were found in your key but are "
                "not registered with Launchpad:<code>%s</code>. If you "
                "want to use these addressess with Launchpad, you need to "
                "<a href=\"/people/%s/+emails\">confirm them</a>.</p>"
                % (emails, requester.name))

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

    def _guessGpgEmails(self, uids):
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
                self.errormessage = (
                        'This email is already registered for another '
                        'Launchpad user account. This account can be a '
                        'duplicate of yours, created automatically, and '
                        'in this case you should be able to '
                        '<a href="/people/+requestmerge">merge them</a> '
                        'into a single one.')
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
        

class NewAccountView(AddView):

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
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        person, email = getUtility(IPersonSet).createPersonAndEmail(
                self.context.email, displayname=kw['displayname'], 
                givenname=kw['givenname'], familyname=kw['familyname'],
                password=kw['password'], passwordEncrypted=True)

        notify(ObjectCreatedEvent(person))
        notify(ObjectCreatedEvent(email))

        person.validateAndEnsurePreferredEmail(email)
        self._nextURL = canonical_url(person)
        self.context.destroySelf()

        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email.email)
        if principal is not None and principal.validate(kw['password']):
            logInPerson(self.request, principal, email.email)
        return True


class MergePeopleView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.errormessage = ""
        self.formProcessed = False
        self.mergeCompleted = False
        self.dupe = getUtility(IPersonSet).getByEmail(context.email)

    def processForm(self):
        if self.request.method != "POST":
            return

        self.formProcessed = True
        if self.validate():
            self.doMerge()
            self.context.destroySelf()

    def successfullyProcessed(self):
        return self.formProcessed and not self.errormessage

    def validate(self):
        """Verify if the user provided the correct password."""
        # Merge requests must have a registered requester.
        assert self.context.requester is not None
        assert self.context.requesteremail is not None
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please try again."
            return False

        return True

    def doMerge(self):
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
        
        # Now we must check if the dupe account still have registered email
        # addresses. If it haven't we can actually do the merge.
        if getUtility(IEmailAddressSet).getByPerson(self.dupe.id):
            self.mergeCompleted = False
            return

        # Call Stuart's magic function which will reassign all of the dupe
        # account's stuff to the user account.
        pset = getUtility(IPersonSet).merge(self.dupe, requester)
        self.mergeCompleted = True


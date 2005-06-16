# Copyright 2004 Canonical Ltd
import urllib

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.database.sqlbase import flush_database_updates

from canonical.lp.dbschema import EmailAddressStatus, LoginTokenType
from canonical.lp.dbschema import GPGKeyAlgorithm

from canonical.foaf.nickname import generate_nick

from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPerson

from canonical.launchpad.interfaces import IPersonSet, IEmailAddressSet
from canonical.launchpad.interfaces import IPasswordEncryptor, IEmailAddressSet
from canonical.launchpad.interfaces import ILoginTokenSet, IGPGKeySet
from canonical.launchpad.interfaces import IGpgHandler


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
             LoginTokenType.VALIDATEGPGUID: '+validateuid'}

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
            self.errormessage = ("The email address you provided didn't "
                                 "match with the one you provided when you "
                                 "requested the password reset.")
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
        emailaddress.status = EmailAddressStatus.VALIDATED

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()

        person = emailaddress.person

        # XXX: Steve Alexander, 2005-03-18
        #      Local import, because I don't want this import copied elsewhere!
        #      This code is to be removed when the UpgradeToBusinessClass
        #      specification is implemented.
        from zope.security.proxy import removeSecurityProxy
        naked_person = removeSecurityProxy(person)
        #      end of evil code.

        if (person.preferredemail is None and 
            len(person.validatedemails) == 1):
            # This user have no preferred email set and this is the only
            # validated email he owns. We must set it as the preferred one.
            naked_person.preferredemail = emailaddress

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
        elif self.context.tokentype == LoginTokenType.VALIDATEGPGUID:
            self.validateGpgUid()

    def validateTeamEmail(self):
        """Set the new email address as the team's contact email address."""
        requester = self.context.requester
        email = self._registerEmail(self.context.email)
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
        """Check the password and validate a person's email address.
        
        Also, if this is the first validated email for this user, we 
        set it as the PREFERRED one for that user. 
        """
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please check and try again."
            return 

        status = EmailAddressStatus.VALIDATED
        if not requester.preferredemail and not requester.validatedemails:
            # This is the first VALIDATED email for this Person, and we
            # need it to be the preferred one, to be able to communicate
            # with the user.
            status = EmailAddressStatus.PREFERRED

        email = self._registerEmail(self.context.email)
        if email is not None:
            email.status = status

        # At this point, either this email address is validated or it can't be
        # validated for this user because it's owned by someone else in
        # Launchpad, so we can safely delete all logintokens for this user 
        # and this email address.
        logintokenset = getUtility(ILoginTokenSet)
        logintokenset.deleteByEmailAndRequester(self.context.email, requester)

  
    def validateGpgUid(self):
        """Check the password and validate a gpg key UID.
        Validate it as normal email account then insert the gpg key if
        needed.
        """
        self.validatePersonEmail()
        self._ensureGPG()   


    def _registerEmail(self, emailaddress):
        """Register <emailaddress> with status VALIDATED and return it.

        If <emailaddress> is already registered in Launchpad, we just set 
        it as VALIDATED and then return.
        """
        validated = (EmailAddressStatus.VALIDATED, EmailAddressStatus.PREFERRED)
        status = EmailAddressStatus.VALIDATED
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
        email = emailset.new(emailaddress, status, requester.id)
        return email

    def _ensureGPG(self):
        """Ensure the correspondent GPGKey entry for the UID."""
        fingerprint = self.context.fingerprint        
        gpgkeyset = getUtility(IGPGKeySet)
        
        # No fingerprint, is it plausible ??
        if fingerprint == None:
            self.errormessage = ('No fingerprint information attached to '
                                 'this Token.') 
            return
        
        # GPG was already inserted 
        if gpgkeyset.getByFingerprint(fingerprint):
            self.errormessage = ('The GPG Key in question was already '
                                 'imported to the Launchpad Context.') 
            return

        # Import the respective public key
        gpghandler = getUtility(IGpgHandler)

        result, pubkey = gpghandler.getPubKey(fingerprint)
        
        if not result:
            self.errormessage = ('Could not get GPG key')
            return

        key = gpghandler.importPubKey(pubkey)

        if not key:
            self.errormessage = ('Could not Import GPG key')
            return
        
        # Otherwise prepare to add
        ownerID = self.context.requester.id
        fingerprint = key.fingerprint
        keyid = key.keyid
        keysize = key.keysize
        algorithm = GPGKeyAlgorithm.items[key.algorithm]
        revoked = key.revoked
        
        # Add new key in DB. See IGPGKeySet for further information
        return gpgkeyset.new(ownerID, keyid, fingerprint,
                             keysize, algorithm, revoked)
        

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

        kw['name'] = generate_nick(self.context.email)
        person = getUtility(IPersonSet).newPerson(**kw)
        notify(ObjectCreatedEvent(person))

        emailset = getUtility(IEmailAddressSet)
        preferred = EmailAddressStatus.PREFERRED
        email = emailset.new(self.context.email, preferred, person.id)
        notify(ObjectCreatedEvent(email))

        self._nextURL = '/people/%s' % person.name
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
        email = getUtility(IEmailAddressSet).getByEmail(self.context.email)
        email.person = self.context.requester.id
        email.status = EmailAddressStatus.VALIDATED

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
        pset = getUtility(IPersonSet).merge(self.dupe, self.context.requester)
        self.mergeCompleted = True


# Copyright 2004 Canonical Ltd
import urllib

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.lp.dbschema import EmailAddressStatus, LoginTokenType

from canonical.foaf.nickname import generate_nick

from canonical.launchpad.database import EmailAddress

from canonical.launchpad.webapp.interfaces import IPlacelessLoginSource
from canonical.launchpad.webapp.login import logInPerson

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IPasswordEncryptor


class LoginTokenView(object):
    """The default view for LoginToken.

    This view will check the token type and then redirect to the specific view
    for that type of token. We use this view so we don't have to add
    "+validate", "+newaccount", etc, on URLs we send by email.
    """

    PAGES = {LoginTokenType.PASSWORDRECOVERY: '+resetpassword',
             LoginTokenType.ACCOUNTMERGE: '+accountmerge',
             LoginTokenType.NEWACCOUNT: '+newaccount',
             LoginTokenType.VALIDATEEMAIL: '+validate'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        url = urllib.basejoin(str(request.URL), self.PAGES[context.tokentype])
        request.response.redirect(url)


class ResetPasswordView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.submitted = False
        self.email = None

    def processForm(self):
        """Check the email address, check if both passwords match and then
        reset the user's password. When password is successfully changed, the
        LoginToken (self.context) used is removed, so nobody can use it again.
        """
        if self.request.method != "POST":
            return

        self.email = self.request.form.get("email").strip()
        if email != self.context.email:
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
            return False

        # Make sure this person has a preferred email address.
        emailaddress = EmailAddress.byEmail(self.context.email)
        person = emailaddress.person
        if person.preferredemail is None:
            person.preferredemail = emailaddress

        encryptor = getUtility(IPasswordEncryptor)
        password = encryptor.encrypt(password)
        person.password = password
        self.submitted = True
        self.context.destroySelf()

    def success(self):
        return self.submitted and not self.errormessage


class ValidateEmailView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context
        self.errormessage = ""

    def formSubmitted(self):
        if self.request.method == "POST":
            self.validate()
            return True
        return False

    def validate(self):
        """Check the requester and requesteremail, verify if the user provided
        the correct password and then set the email address status to
        VALIDATED. Also, if this is the first validated email for this user,
        we set it as the PREFERRED one for that user.
        When everything went ok, we delete the LoginToken (self.context) from
        the database, so nobody can use it again.
        """
        # Email validation requests must have a registered requester.
        assert self.context.requester is not None
        assert self.context.requesteremail is not None
        requester = self.context.requester
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, requester.password):
            self.errormessage = "Wrong password. Please try again."
            return 

        results = EmailAddress.selectBy(email=self.context.requesteremail)
        assert results.count() == 1
        reqemail = results[0]
        assert reqemail.person == requester

        status = int(EmailAddressStatus.VALIDATED)
        if not requester.preferredemail and not requester.validatedemails:
            # This is the first VALIDATED email for this Person, and we
            # need it to be the preferred one, to be able to communicate
            # with the user.
            status = int(EmailAddressStatus.PREFERRED)

        results = EmailAddress.selectBy(email=self.context.email)
        if results.count() > 0:
            # This email was obtained via gina or lucille and have been
            # marked as NEW on the DB. In this case all we have to do is
            # set that email status to VALIDATED.
            assert results.count() == 1
            email = results[0]
            email.status = status
            self.context.destroySelf()
            return

        # New email validated by the user. We must add it to our emailaddress
        # table.
        email = EmailAddress(email=self.context.email, status=status,
                             person=requester.id)
        self.context.destroySelf()


class NewAccountView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'
        self.passwordMismatch = False

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

        errors = []

        password = kw['password']
        # We don't want to pass password2 to PersonSet.new().
        password2 = kw.pop('password2')
        if password2 != password:
            self.passwordMismatch = True
            errors.append('Password mismatch')

        if errors:
            raise WidgetsError(errors)

        kw['name'] = generate_nick(self.context.email)
        person = getUtility(IPersonSet).newPerson(**kw)
        notify(ObjectCreatedEvent(person))

        email = EmailAddress(person=person.id, email=self.context.email,
                             status=int(EmailAddressStatus.PREFERRED))
        notify(ObjectCreatedEvent(email))

        self._nextURL = '/foaf/people/%s' % person.name
        self.context.destroySelf()

        loginsource = getUtility(IPlacelessLoginSource)
        principal = loginsource.getPrincipalByLogin(email.email)
        if principal is not None and principal.validate(password):
            logInPerson(self.request, principal, email.email)
        return True


# Copyright 2004 Canonical Ltd

from zope.component import getUtility
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.event.objectevent import ObjectCreatedEvent

from canonical.lp.dbschema import EmailAddressStatus

from canonical.foaf.nickname import generate_nick

from canonical.launchpad.database import EmailAddress

from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IPasswordEncryptor


class ResetPasswordView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.submitted = False

    def processForm(self):
        if self.request.method != "POST":
            return False

        email = self.request.form.get("email").strip()
        if email != self.context.email:
            self.errormessage = ("The email address you provided didn't "
                                 "match with the one you provided when you "
                                 "requested the password reset.")
            return False

        password = self.request.form.get("password")
        password2 = self.request.form.get("password2")
        if not password and not password2:
            self.errormessage = "Your password cannot be empty."
            return False

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
        return True

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
            return

        # New email validated by the user. We must add it to our emailaddress
        # table.
        email = EmailAddress(email=self.context.email, status=status,
                             person=requester.id)


class NewAccountView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        password = kw['password']
        # We don't want to pass password2 to PersonSet.new().
        password2 = kw.pop('password2')
        if not password and not password2:
            kw.pop('password')
            self._nextURL = "%s?nullpassword=1" % self.request.URL
            return False

        if password2 != password:
            # Do not display the password in the form when an error
            # occurs.
            kw.pop('password')
            self._nextURL = "%s?passwordmismatch=1" % self.request.URL
            return False

        nick = generate_nick(self.context.email)
        kw['name'] = nick
        person = getUtility(IPersonSet).new(**kw)
        notify(ObjectCreatedEvent(person))
        email = EmailAddress(person=person.id, email=self.context.email,
                             status=int(EmailAddressStatus.PREFERRED))
        notify(ObjectCreatedEvent(email))
        self._nextURL = '/foaf/people/%s' % person.name
        return True


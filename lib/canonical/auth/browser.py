# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Browser-related code for the reset-your-password application.

"""
__metaclass__ = type

import re

from canonical.launchpad.database import EmailAddress
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.auth import AuthApplication
from canonical.launchpad.webapp.zodb import zodbconnection

# Note that this appears as "valid email" in the UI, because that term is
# more familiar to users, even if it is less correct.
well_formed_email_re = re.compile(
    r"^[_\.0-9a-z-+]+@([0-9a-z-]{1,}\.)*[a-z]{2,}$")

def well_formed_email(emailaddr):
    """Returns True if emailaddr is well-formed, otherwise returns False.

    >>> well_formed_email('foo.bar@baz.museum')
    True
    >>> well_formed_email('mark@hbd.com')
    True
    >>> well_formed_email('art@cat-flap.com')
    True
    >>> well_formed_email('a@b.b.tw')
    True
    >>> well_formed_email('a@b.b.b.b.tw')
    True
    >>> well_formed_email('i@tm')
    True
    >>> well_formed_email('')
    False
    >>> well_formed_email('a@b')
    False
    >>> well_formed_email('a@foo.b')
    False

    """
    return bool(well_formed_email_re.match(emailaddr))


class SendPasswordToEmail:

    __used_for__ = AuthApplication

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.success = False
        self.email = request.get("email", "").strip().lower()

    def getResult(self):
        # Act only if the form has been filled in with an email address.
        if not self.email:
            return

        if not well_formed_email(self.email):
            return 'Please check you have entered a valid email address.'

        # Try to get from the database the Person who owns this email address
        person = self.context.getPersonFromDatabase(self.email)
        if person is None:
            return ('Your account details have not been found.'
                    ' Please check your subscription'
                    ' email address and try again.')

        random_link = self.context.newLongURL(person)
        self.context.sendPasswordChangeEmail(random_link, self.email)
        self.success = True


class ChangeEmailPassword:

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.email = request.get("email", "")
        self.password = request.get("password", "").strip()
        self.repassword = request.get("repassword", "").strip()
        self.code = request.get("code", "")

        self.success = False
        self.error = False

    def getResult(self):

        if (self.email and self.password and self.repassword):
            # Check if the given email address has a valid format

            if not well_formed_email(self.email):
                return 'Please check you have entered a valid email address.'

            # Verify password misstyping

            if self.password != self.repassword:
                return ('Password mismatch. Please check you ' 
                        'have entered your password correctly.')

            else:
                # Get the lookup table of long-url -> person
                # from the ZODB.
                resets = zodbconnection.passwordresets

                try:
                    person = resets.getPerson(self.code)
                except KeyError:
                    self.error = True
                    return

                email_results = EmailAddress.selectBy(email=self.email)

                if email_results.count() > 0:
                    person_check = email_results[0].person

                    if person.id != person_check.id:
                        person = False

                    if person:
                        encryptor = getUtility(IPasswordEncryptor)
                        person.password = encryptor.encrypt(self.password)

                        self.success = True
                        return 'Your password has successfully been reset.'

                self.error = True
                return


# Copyright 2004 Canonical Ltd

# zope imports
from zope.component import getUtility

# lp imports
from canonical.lp.dbschema import EmailAddressStatus
from canonical.lp.dbschema import LoginTokenType

# interface import
from canonical.launchpad.interfaces import IEmailAddressSet
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.launchpad.interfaces import ILaunchBag, ILoginTokenSet

from canonical.launchpad.mail.sendmail import simple_sendmail


def sendEmailValidationRequest(token, appurl):
    template = open('lib/canonical/launchpad/templates/validate-email.txt').read()
    fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"

    replacements = {'longstring': token.token,
                    'requester': token.requester.browsername(),
                    'requesteremail': token.requesteremail,
                    'toaddress': token.email,
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Validate your email address"
    simple_sendmail(fromaddress, token.email, subject, message)



# Copyright 2004 Canonical Ltd

# sqlobject/sqlos
from canonical.database.sqlbase import flushUpdates

# lp imports
from canonical.lp.dbschema import EmailAddressStatus
from canonical.lp.dbschema import LoginTokenType

from canonical.auth.browser import well_formed_email

# interface import
from canonical.launchpad.interfaces import IEmailAddressSet
from canonical.launchpad.interfaces import IPasswordEncryptor
from canonical.launchpad.interfaces import ILaunchBag, ILoginTokenSet

from canonical.launchpad.mail.sendmail import simple_sendmail

# zope imports
from zope.component import getUtility


class EmailAddressEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = "Your changes have been saved."
        self.user = getUtility(ILaunchBag).user

    def formSubmitted(self):
        if "SUBMIT_CHANGES" in self.request.form:
            self.processEmailChanges()
            return True
        elif "VALIDATE_EMAIL" in self.request.form:
            self.processValidationRequest()
            return True
        else:
            return False

    def processEmailChanges(self):
        user = self.user
        emailset = getUtility(IEmailAddressSet)
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, user.password):
            self.message = "Wrong password. Please try again."
            return

        newemail = self.request.form.get("newemail", "").strip()
        if newemail:
            if not well_formed_email(newemail):
                self.message = "'%s' is not a valid email address." % newemail
                return

            email = emailset.getByEmail(newemail)
            if email is not None and email.person.id == user.id:
                self.message = ("The email address '%s' is already registered "
                                "as your email address. This can be either "
                                "because you already added this email address "
                                "before or because it have been detected by "
                                "our system as being yours. In case it was "
                                "detected by our systeam, it's probably "
                                "shown on this page, inside <em>Detected "
                                "Emails</em>." % email.email)
                return
            elif email is not None:
                self.message = ("The email address '%s' was already "
                                "registered by user '%s'. If you think that "
                                "is a duplicated account, you can go to the "
                                "<a href=\"../+requestmerge\">Merge Accounts"
                                "</a> page to claim this email address and "
                                "everything that is owned by that account.") % \
                               (email.email, email.person.browsername())
                return

            login = getUtility(ILaunchBag).login
            logintokenset = getUtility(ILoginTokenSet)
            token = logintokenset.new(user, login, newemail, 
                                      LoginTokenType.VALIDATEEMAIL)
            sendEmailValidationRequest(token, self.request.getApplicationURL())
            self.message = ("A new message was sent to '%s', please follow "
                            "the instructions on that message to validate "
                            "your email address.") % newemail

        id = self.request.form.get("PREFERRED_EMAIL")
        if id is not None:
            # XXX: salgado 2005-01-06: Ideally, any person that is able to
            # login *must* have a PREFERRED email, and this will not be
            # needed anymore. But for now we need this cause id may be "".
            id = int(id)
            if getattr(user.preferredemail, 'id', None) != id:
                email = emailset.get(id)
                assert email.person == user
                assert email.status == EmailAddressStatus.VALIDATED
                user.preferredemail = email

        ids = self.request.form.get("REMOVE_EMAIL")
        if ids is not None:
            # We can have multiple email adressess marked for deletion, and in
            # this case ids will be a list. Otherwise ids will be str or int
            # and we need to make a list with that value to use in the for 
            # loop.
            if not isinstance(ids, list):
                ids = [ids]

            for id in ids:
                email = emailset.get(id)
                assert email.person == user
                if user.preferredemail != email:
                    # The following lines are a *real* hack to make sure we
                    # don't let the user with no validated email address.
                    # Ideally, we wouldn't need this because all users would
                    # have a preferred email address.
                    if user.preferredemail is None and \
                       len(user.validatedemails) > 1:
                        # No preferred email set. We can only delete this
                        # email if it's not the last validated one.
                        email.destroySelf()
                    elif user.preferredemail is not None:
                        # This user have a preferred email and it's not this
                        # one, so we can delete it.
                        email.destroySelf()

        flushUpdates()

    def processValidationRequest(self):
        id = self.request.form.get("NOT_VALIDATED_EMAIL")
        email = getUtility(IEmailAddressSet).get(id)
        self.message = ("A new email was sent to '%s' with instructions "
                        "on how to validate it.") % email.email
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(self.user, login, email.email,
                                  LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token, self.request.getApplicationURL())


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



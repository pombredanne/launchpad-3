from canonical.launchpad.database import EmailAddress, Person
from canonical.auth.app import SendPasswordChangeEmail
from canonical.auth.app import PasswordChangeApp
from canonical.lp.placelessauth.encryption import SSHADigestEncryptor

from canonical.zodb import zodbconnection

from string import strip, lower
import random
import re

VALID_EMAIL_1 = re.compile(
    r"^[_\.0-9a-z-+]+@([0-9a-z][0-9a-z-]+\.)+[a-z]{2,4}$")
 
VALID_EMAIL_2 = re.compile(
    r"^[_\.0-9a-z-]+@([0-9a-z][0-9a-z-]+)$")

def mailChecker(email_addr):
    if (not VALID_EMAIL_1.match(email_addr) and
        not VALID_EMAIL_2.match(email_addr)):
        return False
    return True

class SendPasswordToEmail(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.success = False
        self.email = ''

        email = request.get("email"   "")
        if email:
            self.email = lower(strip(email))

    def getResult(self):
        random_link = None
        if self.email:
            ## Check if the given email address has a valid format

            if not mailChecker(self.email):
                return 'Please check you have entered a valid email address.'


            ## Try to get the PersonId that is this emails address owner

            dbemail = EmailAddress.selectBy(email=self.email)


            if dbemail.count() > 0:
                ## If the email was found in database, store the needed data
                ## in ZODB and send an email to 'requester'
                person = dbemail[0].person

                resets = zodbconnection.passwordresets
                random_link = resets.newURL(person)
                
                ## Send email
                SendPasswordChangeEmail(random_link, self.email)

                self.success = True
            else:
                return ('Your account details have not been found.'
                        ' Please check your subscription'
                        ' email address and try again.')
        

class changeEmailPassword(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.email = request.get("email"   "")
        self.password = request.get("password"   "")
        self.repassword = request.get("repassword"   "")
        self.code = request.get("code"   "")

        self.success = False
        self.error = False

    def getResult(self):

        if (self.email and self.password and self.repassword):
            ##Check if the given email address has a valid format

            if not mailChecker(self.email):
                return 'Please check you have entered a valid email address.'

            ##Verify password misstyping

            if strip(self.password) != strip(self.repassword):
                return ('Password mismatch. Please check you ' 
                        'have entered your password correctly.')
            
            else:
                ##Get 'transaction' info from ZODB
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
                        ssha = SSHADigestEncryptor()
                        person.password = ssha.encrypt(self.password)
                        self.success = True
                        return 'Your password has successfully been reset.'

                self.error = True
                return
            

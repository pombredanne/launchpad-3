from canonical.launchpad.database import EmailAddress, Person
from canonical.auth.app import SendPasswordChangeEmail
from canonical.auth.app import PasswordChangeApp

from canonical.zodb import zodbconnection

from string import strip
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
        ##XXX: self.success is used only for tests
        ##Daniel Debonzi 2004-10-03
        self.success = False

        self.email = request.get("email"   "")

    def getResult(self):
        random_link = None
        if self.email:
            ## Check if the given email address has a valid format

            if not mailChecker(self.email):
                return 'Please check you have entered a valid email address.'


            ## Try to get the PersonId that is this emails address owner

            person = EmailAddress.selectBy(email=self.email)

            if person.count() > 0:
                ## If the email was found in database, store the needed data
                ## in ZODB and send an email to 'requester'

                resets = zodbconnection.passwordresets
                random_link = resets.newURL(person[0])
                
                ## Send email
                SendPasswordChangeEmail(random_link, self.email)

            return ('Thank you. You will receive and email shortly.'
                    'Please reset your password as soon as possible.')
        

class changeEmailPassword(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.email = request.get("email"   "")
        self.password = request.get("password"   "")
        self.repassword = request.get("repassword"   "")
        self.code = request.get("code"   "")

        ## The process will be done successifully
        ## Until it fails somewhere
        self.success = True

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

                ## How about it? Makes sense?
                ## Must be checked
                ## Daniel Debonzi 2004-10-03
                resets = zodbconnection.passwordresets

                try:
                    person = resets.getPerson(self.code)
                except KeyError:
                    self.success = False
                    return

                person_results = EmailAddress.selectBy(email=self.email)

                if person_results.count() > 0:
                    person_check = person_results[0]
                
                if person.id != person_check.id:
                    person = False
                

                if person:
                    ##Change password

                    ##XXX: password must be encrypted
                    ##Daniel Debonzi 2004-10-03
                    person.password=self.password
                    return 'You password has successfully been reset.'

                self.success = False
                return

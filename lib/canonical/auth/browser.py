from canonical.launchpad.database import EmailAddress, Person
from canonical.auth.app import sendPasswordChangeEmail
from canonical.auth.app import passwordChangeApp

from canonical.zodb import zodbconnection

from string import strip
import random

class sendPasswordToEmail(object):
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
            """
            Check if the given email address has a valid format
            """
            ##XXX: Must be enhaced
            ##Daniel Debonzi 2004-10-03
            if '@' not in self.email:                
                return 'Sorry. Bad email address format'

            """
            Try to get the PersonId that is this emails address owner
            """
            try:
                personId = EmailAddress.selectBy(email=self.email)[0].id
                """
                Generate the 'transaction' code
                """
                random_link = ''.join([random.choice('0123456789abcdfghjklmnpqrstvwxz') for count in range(40)]) 
                ##self.success = random_link
            except:
                """
                If the email is not present in launchpad database
                the 'requester' should not be warned. Like this
                nobody can track launchpad users
                """
                pass

            """
            If the email was found in database, store the needed data
            in ZODB and send an email to 'requester'
            """
            if random_link:
                ##XXX: Check it carefully. Is it the right way to use ZODB?
                ##Daniel Debonzi 2003-10-03
                reminders = zodbconnection.passwordreminders
                reminders.append(personId, random_link)

                get_transaction().commit()

                """
                Send email
                """
                sendPasswordChangeEmail(random_link, self.email)
                
                
            return ('If your email was found in our database '
                    'an email has been sent to you with '
                    'instructions to change your password. '
                    'Thanks')
        

class changeEmailPassword(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.email = request.get("email"   "")
        self.password = request.get("password"   "")
        self.repassword = request.get("repassword"   "")
        self.code = request.get("code"   "")

    def getResult(self):

        if (self.email and self.password and self.repassword):
            """
            Check if the given email address has a valid format
            """
            ##XXX: Must be enhaced
            ##Daniel Debonzi 2004-10-03
            if '@' not in self.email:
                return 'Sorry. Bad email address format'

            """
            Verify password misstyping
            """
            if strip(self.password) != strip(self.repassword):
                return 'The Passwords does not match'
            
            else:
                """
                Get 'transaction' info from ZODB
                """
                ## How about it? Makes sense?
                ## Must be checked
                ## Daniel Debonzi 2004-10-03
                reminders = zodbconnection.passwordreminders
                personId = reminders.retrieve(self.code)

                get_transaction().commit()
                
                try:
                    """
                    Check if the email match
                    """
                    personId_check = EmailAddress.selectBy(email=self.email)[0].id
                    if personId != personId_check:
                        raise
                except:
                    personId = False
                

                if personId:
                    """
                    Change password
                    """
                    user = Person.get(personId)
                    ##XXX: password must be encrypted
                    ##Daniel Debonzi 2004-10-03
                    user.password=self.password
                    return 'Your password has been successfully changed. Thanks'

                return 'Sorry, your password could not be changed'

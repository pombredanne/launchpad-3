from canonical.database.foaf import EmailAddress, Person
from canonical.auth.app import sendPasswordChangeEmail
from canonical.auth.app import passwordChangeApp

from canonical.zodb import zodbconnection

from string import strip
import random

class sendPasswordToEmail(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.success = False
        """ The message to be shown in template """
        self.message = None

        email = request.get("email"   "")

        if email:
            """
            Check if the given email address has a valid format
            """
            #XXX: Must be enhaced
            if '@' not in email:                
                self.message = 'Sorry. Bad email address format'
                return

            """
            Try to get the PersonId that is this emails address owner
            """
            try:
                personId = EmailAddress.selectBy(email=email)[0].id
                """
                Generate the 'transaction' code
                """
                self.success = ''.join([random.choice('0123456789abcdfghjklmnpqrstvwxz') for count in range(40)]) 
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
            if self.success:
                ##XXX: Check it carefully
                reminders = zodbconnection.passwordreminders

                ##XXX: Check more carefully
                reminders.append(personId, self.success)

                get_transaction().commit()

                """
                Send email
                """
                sendPasswordChangeEmail(self.success, email)
                
                
            self.message = ('If your email was found in our database '
                            'an email has been sent to you with '
                            'instructions to change your password. '
                            'Thanks')
            

class changeEmailPassword(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = ''

        email = request.get("email"   "")
        password = request.get("password"   "")
        repassword = request.get("repassword"   "")
        code = request.get("code"   "")

        if (email and password and repassword):
            """
            Check if the given email address has a valid format
            """
            #XXX: Must be enhaced
            if '@' not in email:
                self.message = 'Sorry. Bad email address format'
                return

            """
            Verify password misstyping
            """
            if strip(password) != strip(repassword):
                self.message = 'The Passwords does not match'
                return
            
            else:
                """
                Get 'transaction' info from ZODB
                """
                ## How about it? Makes sense?
                ## Must be checked
                reminders = zodbconnection.passwordreminders
                personId = reminders.retrieve(code)

                get_transaction().commit()
                
                try:
                    """
                    Check if the email match
                    """
                    personId_check = EmailAddress.selectBy(email=email)[0].id
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
                    user.password=password
                    self.message = 'Your password has been successfully changed. Thanks'

                else:
                    self.message = 'Sorry, your password could not be changed'


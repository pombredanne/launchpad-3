from canonical.zodb import zodbconnection

from smtplib import SMTP

class passwordChangeApp(object):
    """ Change Password Application"""
    def __init__(self, name):
        """
        Store the url password change code
        to be passed to the view class in
        a form input type hidden
        """
        self.code = name


class sendPasswordChangeEmail(object):
    """ Send an Password change special link for a user """
    def __init__(self, code, email):

        ##XXX: What about this mail template idea?
        template = open('lib/canonical/auth/mailTemplate')

        msg = template.read() % code
        template.close()

        ##XXX: Remove the line below.. here just for test
        ##email = 'Daniel Debonzi <debonzi@gwyddion.com>'
               
        ##XXX: where to take the mailserver and sender from
        ## Perhaps mailserver and sender as well as the default
        ## mail body could be in ZODB.
        sender = SMTP("localhost")
        sender.sendmail("Launchpad Team <launchpad@warthogs.hbd.com>",
                        email,
                        msg)

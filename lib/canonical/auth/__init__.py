# Copyright 2004 Canonical Ltd.  All rights reserved.
#
"""Password reset application.

"""
__metaclass__ = type

from persistent import Persistent
from zope.interface import implements
from zope.component import getUtility

from BTrees.OOBTree import OOBTree

from canonical.launchpad.interfaces import IAuthApplication
from canonical.launchpad.interfaces import IPasswordResets
from canonical.launchpad.interfaces import IPersonSet

from canonical.launchpad.database import EmailAddress

from canonical.zodb import zodbconnection

from datetime import datetime, timedelta
import random
from smtplib import SMTP


class PasswordResetsExpired(Exception):
    """This is raised when you use an expired URL"""


class PasswordResets(Persistent):
    implements(IPasswordResets)

    characters = '0123456789bcdfghjklmnpqrstvwxz'
    urlLength = 40
    lifetime = timedelta(hours=3)

    def __init__(self):
        self.lookup = OOBTree()

    def newURL(self, person):
        long_url = self._makeURL()
        self.lookup[long_url] = (person.id, datetime.utcnow())
        return long_url

    def getPerson(self, long_url, _currenttime=None):
        # _currenttime may be passed in for unit-testing, to easily
        # simulate requests made at different times.

        # A _currenttime of None means use the current time.
        if _currenttime is None:
            currenttime = datetime.utcnow()
        else:
            currenttime = _currenttime

        person_id, whencreated = self.lookup[long_url]

        if currenttime > whencreated + self.lifetime:
            raise PasswordResetsExpired
        if currenttime < whencreated:
            raise AssertionError(
                "Current time is before when the URL was created")

        person = getUtility(IPersonSet)[person_id]
        return person

    def _makeURL(self):
        return ''.join([random.choice(self.characters)
                        for count in range(self.urlLength)])


class UbuntuLinuxSite(object):
    """The 'fake ubuntu linux website' application.

    This exists to provide a URL beneath which the skin is changed to
    one that looks like the website at http://ubuntulinux.org.
    """


class AuthApplication:
    """Something that URLs get attached to.  See configure.zcml."""
    implements(IAuthApplication)

    def __getitem__(self, name):
        return PasswordChangeApp(name)

    def sendPasswordChangeEmail(self, longurlsegment, toaddress):
        """Send an Password change special link for a user."""
        template = open(
            'lib/canonical/auth/forgotten-password-email.txt').read()
        fromaddress = "Ubuntu Webmaster <webmaster@ubuntulinux.org>"
        date = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

        replacements = {'longstring': longurlsegment,
                        'toaddress': toaddress,
                        'fromaddress': fromaddress,
                        'date': date
                        }

        message = template % replacements

        sender = SMTP("localhost")
        sender.sendmail(fromaddress, toaddress, message)

    def getPersonFromDatabase(self, emailaddr):
        """Returns the Person in the database who has the given email address.

        If there is no Person for that email address, returns None.
        """
        dbemail = EmailAddress.selectBy(email=emailaddr)
        if dbemail.count() > 0:
            return dbemail[0].person
        else:
            return None

    def newLongURL(self, person):
        """Creates a new long url for the given person.

        Returns the long url segment.
        """
        return zodbconnection.passwordresets.newURL(person)

class PasswordChangeApp:
    """Change Password Application"""
    def __init__(self, name):
        # Store the url password change code to be passed to the view
        # class in a form input type hidden.
        self.code = name





# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: fb47064d-e0cd-45d2-b552-f92e803aae71
"""Authentication and related things.

"""

from persistent import Persistent
from zope.interface import implements
from zope.component import getUtility

from BTrees.OOBTree import OOBTree

from canonical.auth.app import PasswordChangeApp

from canonical.launchpad.interfaces import IAuthApplication
from canonical.launchpad.interfaces import IPasswordResets
from canonical.launchpad.interfaces import IPersonSet

from datetime import datetime, timedelta
import random

__metaclass__ = type

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
        if _currenttime is None:
            currenttime = datetime.utcnow()
        else:
            currenttime = _currenttime

        person_id, whencreated = self.lookup[long_url]

        if currenttime > whencreated + self.lifetime:
            raise PasswordResetsExpired
        if currenttime < whencreated:
            raise AssertionError("Current time is before when the URL was created")

        person = getUtility(IPersonSet)[person_id]

        return person
    

    def _makeURL(self):
        return ''.join([random.choice(self.characters) for count in range(self.urlLength)])


class AuthApplication:
    """Something that URLs get attached to.  See configure.zcml."""
    implements(IAuthApplication)

    def __getitem__(self, name):
        return PasswordChangeApp(name)

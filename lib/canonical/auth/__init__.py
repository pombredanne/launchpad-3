# Copyright 2004 Canonical Ltd.  All rights reserved.
#
# arch-tag: fb47064d-e0cd-45d2-b552-f92e803aae71
"""Authentication and related things.

"""

from persistent import Persistent
from zope.interface import implements
from canonical.auth.app import passwordChangeApp

from canonical.launchpad.interfaces import IAuthApplication
from canonical.launchpad.interfaces import IPasswordReminders

from datetime import datetime, timedelta

__metaclass__ = type

class PasswordReminders(Persistent):    
    """The object that manages password reminders.

    Get hold of this object by using the zodb connection:

    >>> from canonical.zodb import zodbconnection
    >>> reminders = zodbconnection.passwordreminders
    """
    implements(IPasswordReminders)

    def __init__(self):
        ##FIXME: Perhaps its a good Ideia to use BTree
        ##Daniel Debonzi 2004-10-03
        self.change_list = {}
    
    def append(self, personId, code):
        self.change_list[code] = [personId, datetime.now()]

    def retrieve(self, code):
        if code not in self.change_list.keys():
            return None

        personId, request_time = self.change_list[code]
        del self.change_list[code]
        ##TODO check if time has not expired
        ##Daniel Debonzi 2004-10-03
        return personId


class AuthApplication:
    """Something that URLs get attached to.  See configure.zcml."""
    implements(IAuthApplication)

    def __getitem__(self, name):
        return passwordChangeApp(name)

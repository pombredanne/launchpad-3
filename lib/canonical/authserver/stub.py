# Copyright 2004 Canonical Ltd.  All rights reserved.

from zope.interface import implements

from canonical.authserver.interfaces import IUserDetailsStorage

class StubUserDetailsStorage(object):
    """Stub implementation of IUserDetailsStorage"""
    implements(IUserDetailsStorage)

    def getUser(self, loginID):
        return {}

    def authUser(self, loginID, sshaDigestedPassword):
        return {}

    def createUser(self, loginID, sshaDigestedPassword, displayname,
                   emailAddresses):
        return 'STUB'


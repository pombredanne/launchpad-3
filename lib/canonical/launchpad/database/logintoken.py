# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from datetime import datetime
import random

# Zope interfaces
from zope.interface import implements

# SQL imports
from sqlobject import DateTimeCol, ForeignKey, IntCol, StringCol
from canonical.database.sqlbase import SQLBase

# canonical imports
from canonical.launchpad.interfaces import ILoginToken, ILoginTokenSet
from canonical.lp.dbschema import LoginTokenType


class LoginToken(SQLBase):
    implements(ILoginToken)
    _table = 'LoginToken'

    requester = ForeignKey(dbName='requester', foreignKey='Person')
    requesteremail = StringCol(dbName='requesteremail') 
    email = StringCol(dbName='email', notNull=True)
    token = StringCol(dbName='token', unique=True)
    tokentype = IntCol(dbName='tokentype', notNull=True)
    created = DateTimeCol(dbName='created', notNull=True)


class LoginTokenSet(object):
    implements(ILoginTokenSet)

    def __getitem__(self, tokentext):
        results = LoginToken.selectBy(token=tokentext)
        if results.count() > 0:
            assert results.count() == 1
            return results[0]
        else:
            raise KeyError, tokentext


def newLoginToken(requester, requesteremail, email, tokentype):
    """ Create a new LoginToken object. Parameters must be:
    requester: a Person object or None (in case of a new account)

    requesteremail: the email address used to login on the system. Can
    also be None in case of a new account
    
    email: the email address that this request will be sent to
    
    tokentype: the type of the request, according to
    dbschema.LoginTokenType
    """

    characters = '0123456789bcdfghjklmnpqrstvwxz'
    length = 40
    token = ''.join([random.choice(characters) for count in range(length)])
    return LoginToken(requester=requester, requesteremail=requesteremail,
                      email=email, token=token, tokentype=int(tokentype),
                      created=datetime.utcnow())


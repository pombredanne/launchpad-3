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

    def new(self, requester, requesteremail, email, tokentype):
        """See ILoginTokenSet"""
        characters = '0123456789bcdfghjklmnpqrstvwxz'
        length = 16
        token = ''.join([random.choice(characters) for count in range(length)])
        return LoginToken(requester=requester, requesteremail=requesteremail,
                          email=email, token=token, tokentype=int(tokentype),
                          created=datetime.utcnow())

    def __getitem__(self, tokentext):
        results = LoginToken.selectBy(token=tokentext)
        if results.count() > 0:
            assert results.count() == 1
            return results[0]
        else:
            raise KeyError, tokentext


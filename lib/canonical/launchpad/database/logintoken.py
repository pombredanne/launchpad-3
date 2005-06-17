# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LoginToken', 'LoginTokenSet']

from datetime import datetime
import random

from zope.interface import implements

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, AND

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.interfaces import ILoginToken, ILoginTokenSet
from canonical.lp.dbschema import LoginTokenType, EnumCol


class LoginToken(SQLBase):
    implements(ILoginToken)
    _table = 'LoginToken'

    requester = ForeignKey(dbName='requester', foreignKey='Person')
    requesteremail = StringCol(dbName='requesteremail', notNull=False,
                               default=None) 
    email = StringCol(dbName='email', notNull=True)
    token = StringCol(dbName='token', unique=True)
    tokentype = EnumCol(dbName='tokentype', notNull=True,
                        schema=LoginTokenType)
    created = UtcDateTimeCol(dbName='created', notNull=True)
    fingerprint = StringCol(dbName='fingerprint', notNull=False,
                            default=None)

    title = 'Launchpad Email Verification'


class LoginTokenSet:
    implements(ILoginTokenSet)

    def __init__(self):
        self.title = 'Launchpad Email Verification System'

    def get(self, id, default=None):
        try:
            return LoginToken.get(id)
        except SQLObjectNotFound:
            return default

    def searchByEmailAndRequester(self, email, requester):
        return LoginToken.select(AND(LoginToken.q.email==email,
                                     LoginToken.q.requesterID==requester.id))

    def deleteByEmailAndRequester(self, email, requester):
        for token in self.searchByEmailAndRequester(email, requester):
            token.destroySelf()
            
    def new(self, requester, requesteremail, email, tokentype,
            fingerprint=None):
        """See ILoginTokenSet."""
        characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
        length = 20
        token = ''.join([random.choice(characters) for count in range(length)])
        reqid = getattr(requester, 'id', None)
        return LoginToken(requesterID=reqid, requesteremail=requesteremail,
                          email=email, token=token, tokentype=tokentype,
                          created=UTC_NOW, fingerprint=fingerprint)

    def __getitem__(self, tokentext):
        token = LoginToken.selectOneBy(token=tokentext)
        if token is None:
            raise KeyError, tokentext
        return token


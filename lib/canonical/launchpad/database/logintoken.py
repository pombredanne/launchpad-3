# Copyright 2004 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['LoginToken', 'LoginTokenSet']

from datetime import datetime
import random

from zope.interface import implements
from zope.component import getUtility

from sqlobject import ForeignKey, StringCol, SQLObjectNotFound, AND

from canonical.database.sqlbase import SQLBase
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol

from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.interfaces import (
    ILoginToken, ILoginTokenSet, IGPGHandler
    )
from canonical.lp.dbschema import LoginTokenType, EnumCol
from canonical.launchpad.validators.email import valid_email

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

    def sendEmailValidationRequest(self, appurl):
        """See ILoginToken."""
        template = open(
            'lib/canonical/launchpad/emailtemplates/validate-email.txt').read()
        fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"

        replacements = {'longstring': self.token,
                        'requester': self.requester.browsername,
                        'requesteremail': self.requesteremail,
                        'toaddress': self.email,
                        'appurl': appurl}
        message = template % replacements

        subject = "Launchpad: Validate your email address"
        simple_sendmail(fromaddress, self.email, subject, message)

    def sendGpgValidationRequest(self, appurl, key, encrypt=None):
        """See ILoginToken."""
        formatted_uids = ''
        for email in key.uids:
            formatted_uids += '\t%s\n' % email
        
        template = open(
            'lib/canonical/launchpad/emailtemplates/validate-gpg.txt').read()
        fromaddress = "Launchpad GPG Validator <noreply@ubuntu.com>"
        
        replacements = {'longstring': self.token,
                        'requester': self.requester.browsername,
                        'requesteremail': self.requesteremail,
                        'displayname': key.displayname, 
                        'fingerprint': key.fingerprint,
                        'uids': formatted_uids,
                        'appurl': appurl}
        message = template % replacements

        # encrypt message if requested
        if encrypt:
            gpghandler = getUtility(IGPGHandler)
            message = gpghandler.encryptContent(message, key.fingerprint)

        subject = "Launchpad: Validate your GPG Key"
        simple_sendmail(fromaddress, self.email, subject, message)


class LoginTokenSet:
    implements(ILoginTokenSet)

    def __init__(self):
        self.title = 'Launchpad Email Verification System'

    def get(self, id, default=None):
        """See ILoginTokenSet."""
        try:
            return LoginToken.get(id)
        except SQLObjectNotFound:
            return default

    def searchByEmailAndRequester(self, email, requester):
        """See ILoginTokenSet."""
        return LoginToken.select(AND(LoginToken.q.email==email,
                                     LoginToken.q.requesterID==requester.id))

    def deleteByEmailAndRequester(self, email, requester):
        """See ILoginTokenSet."""
        for token in self.searchByEmailAndRequester(email, requester):
            token.destroySelf()

    def searchByFingerprintAndRequester(self, fingerprint, requester):
        """See ILoginTokenSet."""
        return LoginToken.select(AND(LoginToken.q.fingerprint==fingerprint,
                                     LoginToken.q.requesterID==requester.id))

    def getPendingGpgKeys(self, requesterid=None):
        """See ILoginTokenSet."""
        query = 'tokentype=%s ' % LoginTokenType.VALIDATEGPG.value

        if requesterid:
            query += 'AND requester=%s' % requesterid
        
        return LoginToken.select(query)

    def deleteByFingerprintAndRequester(self, fingerprint, requester):
        for token in self.searchByFingerprintAndRequester(fingerprint,
                                                          requester):
            token.destroySelf()
            
    def new(self, requester, requesteremail, email, tokentype,
            fingerprint=None):
        """See ILoginTokenSet."""
        assert valid_email(email)
        if tokentype not in LoginTokenType.items:
            raise ValueError(
                "tokentype is not an item of LoginTokenType: %s" % tokentype)

        characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
        length = 20
        token = ''.join([random.choice(characters) for count in range(length)])
        reqid = getattr(requester, 'id', None)
        return LoginToken(requesterID=reqid, requesteremail=requesteremail,
                          email=email, token=token, tokentype=tokentype,
                          created=UTC_NOW, fingerprint=fingerprint)

    def __getitem__(self, tokentext):
        """See ILoginTokenSet."""
        token = LoginToken.selectOneBy(token=tokentext)
        if token is None:
            raise KeyError, tokentext
        return token


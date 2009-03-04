# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['AuthToken', 'AuthTokenSet']

from zope.interface import implements

import pytz
from storm.base import Storm
from storm.properties import Int, Unicode, DateTime
from storm.references import Reference
from storm.store import Store

from canonical.config import config

from canonical.database.constants import UTC_NOW
from canonical.database.enumcol import DBEnum

from canonical.launchpad.components.tokens import (
    create_unique_token_for_table)
from canonical.launchpad.helpers import get_email_template
from canonical.launchpad.interfaces.authtoken import (
    IAuthToken, IAuthTokenSet, LoginTokenType)
from canonical.launchpad.interfaces.launchpad import NotFoundError
from canonical.launchpad.interfaces.lpstorm import IMasterObject, IMasterStore
from canonical.launchpad.interfaces.person import IPerson
from canonical.launchpad.mail import simple_sendmail, format_address
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.webapp import canonical_url


class AuthToken(Storm):
    implements(IAuthToken)
    __storm_table__ = 'AuthToken'

    def __init__(self, account, requesteremail, email, tokentype,
                 redirection_url):
        super(AuthToken, self).__init__()
        self.token = create_unique_token_for_table(20, AuthToken.token)
        self.tokentype = tokentype

        self.requester_account = account
        self.requesteremail = requesteremail
        self.email = email

        self.redirection_url = redirection_url

    id = Int(primary=True)

    date_created = DateTime(tzinfo=pytz.utc)
    date_consumed = DateTime(tzinfo=pytz.utc)
    tokentype = DBEnum('token_type', enum=LoginTokenType, allow_none=False)
    token = Unicode(allow_none=False)

    requester_account_id = Int('requester')
    requester_account = Reference(
        requester_account_id,
        'canonical.launchpad.database.account.Account.id')
    requesteremail = Unicode('requester_email')

    email = Unicode(allow_none=False)
    redirection_url = Unicode()

    password = '' # Quick fix for Bug #2481

    title = 'Launchpad Email Verification'

    @property
    def requester(self):
        return IPerson(self.requester_account, None)

    def consume(self):
        """See ILoginToken."""
        self.date_consumed = UTC_NOW

        result = Store.of(self).find(
            AuthToken, email=self.email, tokentype=self.tokentype,
            requester_account_id=self.requester_account_id,
            date_consumed=None)
        for token in result:
            token.date_consumed = UTC_NOW

    def _send_email(self, from_name, subject, message, headers=None):
        """Send an email to this token's email address."""
        from_address = format_address(
            from_name, config.canonical.noreply_from_address)
        to_address = str(self.email)
        simple_sendmail(
            from_address, to_address, subject, message,
            headers=headers, bulk=False)

    def sendEmailValidationRequest(self):
        """See ILoginToken."""
        template = get_email_template('validate-email-neutral.txt')
        replacements = {'requester': self.requester_account.displayname,
                        'requesteremail': self.requesteremail,
                        'toaddress': self.email,
                        'token_url': canonical_url(self)}
        message = template % replacements
        subject = "Login Service: Validate your email address"
        self._send_email("Login Service Email Validator", subject, message)

    def sendPasswordResetEmail(self):
        """See ILoginToken."""
        template = get_email_template('forgottenpassword-neutral.txt')
        from_name = "Login Service"
        message = template % dict(token_url=canonical_url(self))
        subject = "Login Service: Forgotten Password"
        self._send_email(from_name, subject, message)

    def sendNewUserEmail(self):
        """See ILoginToken."""
        template = get_email_template('newuser-email-neutral.txt')
        message = template % dict(token_url=canonical_url(self))

        from_name = "Login Service"
        subject = "Login Service: Finish your registration"
        self._send_email(from_name, subject, message)


class AuthTokenSet:
    implements(IAuthTokenSet)

    title = 'Launchpad e-mail address confirmation'

    def get(self, id, default=None):
        """See IAuthTokenSet."""
        store = IMasterStore(AuthToken)
        token = store.get(AuthToken, id)
        if token is None:
            return default
        return token

    def searchByEmailAccountAndType(self, email, account, type,
                                    consumed=None):
        """See IAuthTokenSet."""
        conditions = [
            AuthToken.email == email,
            AuthToken.requester_account == account,
            AuthToken.tokentype == type
            ]

        if consumed is True:
            conditions.append(AuthToken.date_consumed != None)
        elif consumed is False:
            conditions.append(AuthToken.date_consumed == None)
        else:
            assert consumed is None, (
                "consumed should be one of {True, False, None}. Got '%s'."
                % consumed)

        # It's important to always use the MASTER_FLAVOR store here
        # because we don't want replication lag to cause a 404 error.
        store = IMasterStore(AuthToken)
        return store.find(AuthToken, *conditions)

    def deleteByEmailAccountAndType(self, email, account, type):
        """See IAuthTokenSet."""
        self.searchByEmailAccountAndType(email, account, type).remove()

    def new(self, requester, requesteremail, email, tokentype,
            redirection_url):
        """See IAuthTokenSet."""
        assert valid_email(email)
        if tokentype not in [LoginTokenType.PASSWORDRECOVERY,
                             LoginTokenType.NEWACCOUNT,
                             LoginTokenType.VALIDATEEMAIL,
                             LoginTokenType.NEWPERSONLESSACCOUNT]:
            # XXX: Guilherme Salgado, 2005-12-09:
            # Aha! According to our policy, we shouldn't raise ValueError.
            raise ValueError(
                "tokentype is not a valid AuthToken type: %s" %
                tokentype.name)

        if requester is not None:
            requester = IMasterObject(requester)

        if isinstance(redirection_url, str):
            redirection_url = unicode(redirection_url)

        token = AuthToken(account=requester,
                          requesteremail=requesteremail,
                          email=email, tokentype=tokentype,
                          redirection_url=redirection_url)

        store = IMasterStore(AuthToken)
        store.add(token)
        return token

    def __getitem__(self, tokentext):
        """See IAuthTokenSet."""
        store = IMasterStore(AuthToken)
        token = store.find(AuthToken, token=tokentext).one()
        if token is None:
            raise NotFoundError(tokentext)
        return token

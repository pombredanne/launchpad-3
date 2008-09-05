# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for Account and associates."""

__metaclass__ = type
__all__ = ['Account', 'AccountPassword', 'AccountSet']

import random

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol
from sqlobject.sqlbuilder import AND

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces.account import (
        AccountCreationRationale, AccountStatus,
        IAccount, IAccountSet)
from canonical.launchpad.interfaces.emailaddress import EmailAddressStatus
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.launchpad.interfaces.openidserver import IOpenIDRPSummarySet
from canonical.launchpad.webapp.vhosts import allvhosts


class Account(SQLBase):
    """An Account."""

    implements(IAccount)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    displayname = StringCol(dbName='displayname', notNull=True)

    creation_rationale = EnumCol(
            dbName='creation_rationale', schema=AccountCreationRationale,
            notNull=True)
    status = EnumCol(
            enum=AccountStatus, default=AccountStatus.NOACCOUNT,
            notNull=True)
    date_status_set = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    status_comment = StringCol(dbName='status_comment', default=None)

    openid_identifier = StringCol(
            dbName='openid_identifier', notNull=True, default=DEFAULT)

    # XXX sinzui 2008-09-04 bug=264783:
    # Remove this attribute, in the DB, drop openid_identifier, then
    # rename new_openid_identifier => openid_identifier.
    new_openid_identifier = StringCol(
            dbName='old_openid_identifier', notNull=False, default=DEFAULT)

    # The password is actually stored in a seperate table for security
    # reasons, so use a property to hide this implementation detail.
    def _get_password(self):
        password = AccountPassword.selectOneBy(account=self)
        if password is None:
            return None
        else:
            return password.password

    def _set_password(self, value):
        password = AccountPassword.selectOneBy(account=self)

        if value is not None and password is None:
            # There is currently no AccountPassword record and we need one.
            AccountPassword(account=self, password=value)
        elif value is None and password is not None:
            # There is an AccountPassword record that needs removing.
            AccountPassword.delete(password.id)
        elif value is not None:
            # There is an AccountPassword record that needs updating.
            password.password = value
        elif value is None and password is None:
            # Nothing to do
            pass
        else:
            assert False, "This should not be reachable."

    password = property(_get_password, _set_password)


class AccountSet:
    """See `IAccountSet`."""
    implements(IAccountSet)

    def new(self, rationale, displayname, memonic=None,
            password=None, password_is_encrypted=False):
        """See `IAccountSet`."""

        account = Account(
                displayname=displayname, creation_rationale=rationale)

        # Create the openid_identifier for the OpenID identity URL.
        if memonic is not None:
            account.new_openid_identifier = self.createOpenIdentifier(memonic)

        # Create the password record.
        if password is not None:
            if not password_is_encrypted:
                password = getUtility(IPasswordEncryptor).encrypt(password)
            AccountPassword(account=account, password=password)

        return account

    def getByEmail(self, email):
        """See `IAccountSet`."""
        return Account.selectOne('''
            EmailAddress.account = Account.id
            AND lower(EmailAddress.email) = lower(trim(%s))
            ''' % sqlvalues(email),
            clauseTables=['EmailAddress'])

    def getByOpenIdIdentifier(self, openid_identifier):
        """See `IAccountSet`."""
        return Account.selectOne(
            AND(
                Account.q.openid_identifier == openid_identifier,
                Account.q.status == AccountStatus.ACTIVE,
                EmailAddress.q.accountID == Account.q.id,
                EmailAddress.q.status == EmailAddressStatus.PREFERRED,
               ),)

    def createOpenIdentifier(self, memonic):
        """See `IAccountSet`."""
        assert isinstance(memonic, (str, unicode)) and memonic is not '', (
            "The memonic must be a non-empty string.")
        identity_url_root = allvhosts.configs['id'].rooturl
        openidrpsummaryset = getUtility(IOpenIDRPSummarySet)
        tokens = range(0, 999)
        random.shuffle(tokens)
        # This method might be faster by collecting all accounts and summaries
        # that end with the memonic. The chances of collision seem minute,
        # given that the intended memonic is a unique user name.
        for token in tokens:
            token = '%03d' % token
            openid_identifier = '%s/%s' % (token, memonic)
            account = self.getByOpenIdIdentifier(openid_identifier)
            if account is not None:
                continue
            summaries = openidrpsummaryset.getByIdentifier(
                identity_url_root + openid_identifier)
            if summaries.count() == 0:
                return openid_identifier
        raise AssertionError(
            "An openid_identifier could not be created with the memonic '%s'."
            % memonic)


class AccountPassword(SQLBase):
    """SQLObject wrapper to the AccountPassword table.

    Note that this class is not exported, as the existence of the
    AccountPassword table only needs to be known by this module.
    """
    account = ForeignKey(
            dbName='account', foreignKey='Account', alternateID=True)
    password = StringCol(dbName='password', notNull=True)


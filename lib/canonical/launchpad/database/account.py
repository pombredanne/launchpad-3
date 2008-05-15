# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for an Account and associates."""

__metaclass__ = type
__all__ = ['Account', 'AccountPassword', 'AccountSet']

from zope.component import getUtility
from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
        AccountCreationRationale, AccountStatus,
        IAccount, IAccountSet, IPasswordEncryptor)


class Account(SQLBase):
    """An Account."""

    implements(IAccount)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    displayname = StringCol(dbName='displayname', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', default=None)

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


    # The password is actually stored in a seperate table for security
    # reasons, so use a property to hide this implementation detail.
    def _get_password(self):
        password = AccountPassword.selectOneBy(account=self)
        if password is not None:
            return password.password
        else:
            return None

    def _set_password(self, value):
        password = AccountPassword.selectOneBy(account=self)

        if value is not None and password is None:
            # There is currently no AccountPassword record and we need one.
            AccountPassword(account=self, password=value)
        elif password is None:
            # There is an AccountPassword record that needs removing.
            AccountPassword.delete(password.id)
        elif value is not None:
            # There is an AccountPassword record that needs updating.
            password.password = value

    password = property(_get_password, _set_password)


class AccountSet:
    implements(IAccountSet)

    def new(self, rationale, displayname, emailaddress,
            plaintext_password=None, encrypted_password=None):
        """See IAccountSet."""

        account = Account(
                displayname=displayname, creation_rationale=rationale,
                person=emailaddress.person)

        # Link the EmailAddress to the Account.
        emailaddress.account = account

        # Create the password record
        if encrypted_password is None and password is not None:
            encrypted_password = getUtility(IPasswordEncryptor).encrypt(
                    password)
        if encrypted_password is not None:
            AccountPassword(account=account, password=encrypted_password)

        return account

    def getByEmail(self, email):
        """See IAccountSet."""
        return Account.selectOne('''
            EmailAddress.account = Account.id
            AND lower(EmailAddress.email) = %s
            ''' % sqlvalues(email.strip().lower()),
            clauseTables=['EmailAddress'])

    def getByPerson(self, person):
        """See IAccountSet."""
        if person.isTeam():
            return None
        return Account.selectOneBy(person=person)


class AccountPassword(SQLBase):
    """SQLObject wrapper to the AccountPassword table.

    Note that this class is not exported, as the existance of the
    AccountPassword table only needs to be known by this module.
    """
    account = ForeignKey(
            dbName='account', foreignKey='Account', alternateID=True)
    password = StringCol(dbName='password', notNull=True)


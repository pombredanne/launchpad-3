# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for an Account and associates."""

__metaclass__ = type
__all__ = ['Account', 'AccountPassword', 'AccountSet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.interfaces import (
        AccountCreationRationale, AccountStatus,
        IAccount, IAccountSet)


class Account(SQLBase):
    """An Account."""

    implements(IAccount)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    displayname = StringCol(dbName='displayname', notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person')

    creation_rationale = EnumCol(
            dbName='creation_rationale', schema=AccountCreationRationale,
            notNull=True)
    status = EnumCol(
            enum=AccountStatus, default=AccountStatus.ACTIVE,
            notNull=True)
    date_status_set = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    status_comment = StringCol(dbName='status_comment')

    openid_identifier = StringCol(
            dbName='openid_identifier', notNull=True, default=DEFAULT)


    # The password is actually stored in a seperate table for security
    # reasons, so use a property to hide this implementation detail.
    def _get_password(self):
        return AccountPassword.byAccountID(self.id).password

    def _set_password(self, value):
        AccountPassword.byAccountID(self.id).password = value

    password = property(_get_password, _set_password)

    def _set_status(self, value):
        """Update date_status_set when status is updated."""
        self._SO_set_status(value)
        self.sync()


class AccountSet:
    implements(IAccountSet)

    def new(self):
        """See IAccountSet."""

    def getByEmail(self, email):
        """See IAccountSet."""
        return Account.selectOne('''
            EmailAddress.account = Account.id
            AND lower(EmailAddress.email) = %s
            ''' % sqlvalues(email.strip().lower()),
            clauseTables=['EmailAddress'])

    def getByPerson(self, person):
        """See IAccountSet."""
        return Account.selectOneBy(person=person)


class AccountPassword(SQLBase):
    """SQLObject wrapper to the AccountPassword table.

    Note that this class is not exported, as the existance of the
    AccountPassword table only needs to be known by this module.
    """
    account = ForeignKey(
            dbName='account', foreignKey='Account', alternateID=True)
    password = StringCol(dbName='password', notNull=True)


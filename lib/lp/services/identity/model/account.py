# Copyright 2009-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation classes for Account and associates."""

__metaclass__ = type
__all__ = [
    'Account',
    'AccountSet',
    ]

import datetime

from sqlobject import StringCol
from storm.locals import ReferenceSet
from zope.interface import implementer

from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import (
    IMasterStore,
    IStore,
    )
from lp.services.database.sqlbase import SQLBase
from lp.services.identity.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    IAccount,
    IAccountSet,
    )
from lp.services.openid.model.openididentifier import OpenIdIdentifier


class AccountStatusEnumCol(EnumCol):

    def __set__(self, obj, value):
        if self.__get__(obj) == value:
            return
        IAccount['status'].bind(obj)._validate(value)
        super(AccountStatusEnumCol, self).__set__(obj, value)


@implementer(IAccount)
class Account(SQLBase):
    """An Account."""

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    displayname = StringCol(dbName='displayname', notNull=True)

    creation_rationale = EnumCol(
        dbName='creation_rationale', schema=AccountCreationRationale,
        notNull=True)
    status = AccountStatusEnumCol(
        enum=AccountStatus, default=AccountStatus.NOACCOUNT, notNull=True)
    date_status_set = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    status_history = StringCol(dbName='status_comment', default=None)

    openid_identifiers = ReferenceSet(
        "Account.id", OpenIdIdentifier.account_id)

    def __repr__(self):
        displayname = self.displayname.encode('ASCII', 'backslashreplace')
        return "<%s '%s' (%s)>" % (
            self.__class__.__name__, displayname, self.status)

    def addStatusComment(self, user, comment):
        """See `IAccountModerateRestricted`."""
        prefix = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        if user is not None:
            prefix += ' %s' % user.name
        old_lines = (
            self.status_history.splitlines() if self.status_history else [])
        self.status_history = '\n'.join(
            old_lines + ['%s: %s' % (prefix, comment), ''])

    def setStatus(self, status, user, comment):
        """See `IAccountModerateRestricted`."""
        comment = comment or ''
        self.addStatusComment(
            user, '%s -> %s: %s' % (self.status.title, status.title, comment))
        # date_status_set is maintained by a DB trigger.
        self.status = status

    def reactivate(self, comment):
        """See `IAccountSpecialRestricted`."""
        self.setStatus(AccountStatus.ACTIVE, None, comment)


@implementer(IAccountSet)
class AccountSet:
    """See `IAccountSet`."""

    def new(self, rationale, displayname, openid_identifier=None,
            status=AccountStatus.NOACCOUNT):
        """See `IAccountSet`."""
        assert status in (AccountStatus.NOACCOUNT, AccountStatus.PLACEHOLDER)
        account = Account(
            displayname=displayname, creation_rationale=rationale,
            status=status)

        # Create an OpenIdIdentifier record if requested.
        if openid_identifier is not None:
            assert isinstance(openid_identifier, unicode)
            identifier = OpenIdIdentifier()
            identifier.account = account
            identifier.identifier = openid_identifier
            IMasterStore(OpenIdIdentifier).add(identifier)

        return account

    def get(self, id):
        """See `IAccountSet`."""
        account = IStore(Account).get(Account, id)
        if account is None:
            raise LookupError(id)
        return account

    def getByOpenIDIdentifier(self, openid_identifier):
        """See `IAccountSet`."""
        store = IStore(Account)
        account = store.find(
            Account,
            Account.id == OpenIdIdentifier.account_id,
            OpenIdIdentifier.identifier == openid_identifier).one()
        if account is None:
            raise LookupError(openid_identifier)
        return account

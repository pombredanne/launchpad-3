# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Implementation classes for Account and associates."""

__metaclass__ = type
__all__ = [
    'Account',
    'AccountPassword',
    'AccountSet',
    ]

from sqlobject import (
    ForeignKey,
    StringCol,
    )
from storm.locals import ReferenceSet
from zope.component import getUtility
from zope.interface import implements

from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.lpstorm import (
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
from lp.services.identity.model.emailaddress import EmailAddress
from lp.services.openid.model.openididentifier import OpenIdIdentifier
from lp.services.webapp.interfaces import IPasswordEncryptor


class Account(SQLBase):
    """An Account."""

    implements(IAccount)

    date_created = UtcDateTimeCol(notNull=True, default=UTC_NOW)

    displayname = StringCol(dbName='displayname', notNull=True)

    creation_rationale = EnumCol(
        dbName='creation_rationale', schema=AccountCreationRationale,
        notNull=True)
    status = EnumCol(
        enum=AccountStatus, default=AccountStatus.NOACCOUNT, notNull=True)
    date_status_set = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    status_comment = StringCol(dbName='status_comment', default=None)

    openid_identifiers = ReferenceSet(
        "Account.id", OpenIdIdentifier.account_id)

    def __repr__(self):
        displayname = self.displayname.encode('ASCII', 'backslashreplace')
        return "<%s '%s' (%s)>" % (
            self.__class__.__name__, displayname, self.status)

    @property
    def preferredemail(self):
        """See `IAccount`."""
        from lp.registry.interfaces.person import IPerson
        return IPerson(self).preferredemail

    def reactivate(self, comment, password):
        """See `IAccountSpecialRestricted`."""
        self.status = AccountStatus.ACTIVE
        self.status_comment = comment
        self.password = password

    # The password is actually stored in a separate table for security
    # reasons, so use a property to hide this implementation detail.
    def _get_password(self):
        # We have to force the switch to the auth store, because the
        # AccountPassword table is not visible via the main store
        # for security reasons.
        password = IStore(AccountPassword).find(
            AccountPassword, accountID=self.id).one()
        if password is None:
            return None
        else:
            return password.password

    def _set_password(self, value):
        # Making a modification, so we explicitly use the auth store master.
        store = IMasterStore(AccountPassword)
        password = store.find(
            AccountPassword, accountID=self.id).one()

        if value is not None and password is None:
            # There is currently no AccountPassword record and we need one.
            AccountPassword(accountID=self.id, password=value)
        elif value is None and password is not None:
            # There is an AccountPassword record that needs removing.
            store.remove(password)
        elif value is not None:
            # There is an AccountPassword record that needs updating.
            password.password = value
        elif value is None and password is None:
            # Nothing to do
            pass
        else:
            assert False, "This should not be reachable."

    password = property(_get_password, _set_password)

    @property
    def is_valid(self):
        """See `IAccount`."""
        if self.status != AccountStatus.ACTIVE:
            return False
        return self.preferredemail is not None


class AccountSet:
    """See `IAccountSet`."""
    implements(IAccountSet)

    def new(self, rationale, displayname, password=None,
            password_is_encrypted=False, openid_identifier=None):
        """See `IAccountSet`."""

        account = Account(
            displayname=displayname, creation_rationale=rationale)

        # Create an OpenIdIdentifier record if requested.
        if openid_identifier is not None:
            assert isinstance(openid_identifier, unicode)
            identifier = OpenIdIdentifier()
            identifier.account = account
            identifier.identifier = openid_identifier
            IMasterStore(OpenIdIdentifier).add(identifier)

        # Create the password record.
        if password is not None:
            if not password_is_encrypted:
                password = getUtility(IPasswordEncryptor).encrypt(password)
            AccountPassword(account=account, password=password)

        return account

    def get(self, id):
        """See `IAccountSet`."""
        account = IStore(Account).get(Account, id)
        if account is None:
            raise LookupError(id)
        return account

    def getByEmail(self, email):
        """See `IAccountSet`."""
        from lp.registry.model.person import Person
        store = IStore(Account)
        try:
            email = email.decode('US-ASCII')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Non-ascii email addresses are not legal, so assume there are no
            # matching addresses in Launchpad.
            raise LookupError(repr(email))
        account = store.find(
            Account,
            Person.account == Account.id,
            EmailAddress.person == Person.id,
            EmailAddress.email.lower()
                == email.strip().lower()).one()
        if account is None:
            raise LookupError(email)
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


class AccountPassword(SQLBase):
    """SQLObject wrapper to the AccountPassword table.

    Note that this class is not exported, as the existence of the
    AccountPassword table only needs to be known by this module.
    """
    account = ForeignKey(
        dbName='account', foreignKey='Account', alternateID=True)
    password = StringCol(dbName='password', notNull=True)

# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for Account and associates."""

__metaclass__ = type
__all__ = ['Account', 'AccountPassword', 'AccountSet']

import random

from zope.component import getUtility
from zope.interface import implements

from storm.expr import Desc
from storm.references import Reference
from storm.store import Store

from sqlobject import ForeignKey, StringCol
from sqlobject.sqlbuilder import OR

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase, sqlvalues
from canonical.launchpad.database.openidserver import OpenIDRPSummary
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale, AccountStatus, IAccount, IAccountSet)
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddressSet)
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.launchpad.interfaces.openidserver import IOpenIDRPSummarySet
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, DEFAULT_FLAVOR)
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
        enum=AccountStatus, default=AccountStatus.NOACCOUNT, notNull=True)
    date_status_set = UtcDateTimeCol(notNull=True, default=UTC_NOW)
    status_comment = StringCol(dbName='status_comment', default=None)

    openid_identifier = StringCol(
        dbName='openid_identifier', notNull=True, default=DEFAULT)

    # XXX sinzui 2008-09-04 bug=264783:
    # Remove this attribute, in the DB, drop openid_identifier, then
    # rename new_openid_identifier => openid_identifier.
    new_openid_identifier = StringCol(
        dbName='old_openid_identifier', notNull=False, default=DEFAULT)

    person = Reference("id", "Person.account", on_remote=True)

    @property
    def preferredemail(self):
        """See `IAccount`."""
        from canonical.launchpad.database.emailaddress import EmailAddress
        return Store.of(self).find(
            EmailAddress, account=self,
            status=EmailAddressStatus.PREFERRED).one()

    @property
    def recently_authenticated_rps(self):
        """See `IAccount`."""
        result = Store.of(self).find(OpenIDRPSummary, account=self)
        result.order_by(Desc(OpenIDRPSummary.date_last_used))
        return result.config(limit=10)

    def reactivate(self, comment, password, preferred_email):
        """See `IAccountSpecialRestricted`.

        :raise AssertionError: if the password is not valid.
        :raise AssertionError: if the preferred email address is None.
        """
        if password in (None, ''):
            raise AssertionError(
                "Account %s cannot be reactivated without a "
                "password." % self.id)
        if preferred_email is None:
            raise AssertionError(
                "Account %s cannot be reactivated without a "
                "preferred email address." % self.id)
        self.status = AccountStatus.ACTIVE
        self.status_comment = comment
        self.password = password

        # XXX: salgado, 2009-02-26: Instead of doing what we do below, we
        # should just provide a hook for callsites to do other stuff that's
        # not directly related to the account itself.
        person = self.person
        if person is not None:
            # Since we have a person associated with this account, it may be
            # used to log into Launchpad, and so it may not have a preferred
            # email address anymore.  We need to ensure it does have one.
            person.validateAndEnsurePreferredEmail(preferred_email)

            if '-deactivatedaccount' in person.name:
                # The name was changed by deactivateAccount(). Restore the
                # name, but we must ensure it does not conflict with a current
                # user.
                name_parts = person.name.split('-deactivatedaccount')
                base_new_name = name_parts[0]
                person.name = person._ensureNewName(base_new_name)

    # The password is actually stored in a separate table for security
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

    @property
    def is_valid(self):
        """See `IAccount`."""
        if self.status != AccountStatus.ACTIVE:
            return False
        return self.preferredemail is not None

    def createPerson(self, rationale):
        """See `IAccount`."""
        # Need a local import because of circular dependencies.
        from canonical.launchpad.database.person import (
            generate_nick, Person, PersonSet)
        assert self.preferredemail is not None, (
            "Can't create a Person for an account which has no email.")
        store = Store.of(self)
        assert store.find(Person, account=self).one() is None, (
            "Can't create a Person for an account which already has one.")
        name = generate_nick(self.preferredemail.email)
        person = PersonSet()._newPerson(
            name, self.displayname, hide_email_addresses=True,
            rationale=rationale, account=self)
        self.preferredemail.person = person
        return person


class AccountSet:
    """See `IAccountSet`."""
    implements(IAccountSet)

    def new(self, rationale, displayname, openid_mnemonic=None,
            password=None, password_is_encrypted=False):
        """See `IAccountSet`."""

        # Create the openid_identifier for the OpenID identity URL.
        if openid_mnemonic is not None:
            new_openid_identifier = self.createOpenIDIdentifier(
                openid_mnemonic)
        else:
            new_openid_identifier = None

        account = Account(
                displayname=displayname, creation_rationale=rationale,
                new_openid_identifier=new_openid_identifier)

        # Create the password record.
        if password is not None:
            if not password_is_encrypted:
                password = getUtility(IPasswordEncryptor).encrypt(password)
            AccountPassword(account=account, password=password)

        return account

    def get(self, id):
        """See `IAccountSet`."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        return store.find(Account, Account.id == id).one()

    def createAccountAndEmail(self, email, rationale, displayname, password,
                              password_is_encrypted=False):
        """See `IAccountSet`."""
        from canonical.launchpad.database.person import generate_nick
        openid_mnemonic = generate_nick(email)
        # Convert the PersonCreationRationale to an AccountCreationRationale.
        account_rationale = getattr(AccountCreationRationale, rationale.name)
        account = self.new(
            account_rationale, displayname, openid_mnemonic,
            password=password, password_is_encrypted=password_is_encrypted)
        account.status = AccountStatus.ACTIVE
        email = getUtility(IEmailAddressSet).new(
            email, status=EmailAddressStatus.PREFERRED, account=account)
        return account, email

    def getByEmail(self, email):
        """See `IAccountSet`."""
        return Account.selectOne('''
            EmailAddress.account = Account.id
            AND lower(EmailAddress.email) = lower(trim(%s))
            ''' % sqlvalues(email),
            clauseTables=['EmailAddress'])

    def getByOpenIDIdentifier(self, openid_identifier):
        """See `IAccountSet`."""
        # XXX sinzui 2008-09-09 bug=264783:
        # Remove the OR clause, only openid_identifier should be used.
        return Account.selectOne(
            OR(
                Account.q.openid_identifier == openid_identifier,
                Account.q.new_openid_identifier == openid_identifier),)

    _MAX_RANDOM_TOKEN_RANGE = 1000

    def createOpenIDIdentifier(self, mnemonic):
        """See `IAccountSet`.

        The random component of the identifier is a number between 000 and
        999.
        """
        assert isinstance(mnemonic, (str, unicode)) and mnemonic is not '', (
            'The mnemonic must be a non-empty string.')
        identity_url_root = allvhosts.configs['id'].rooturl
        openidrpsummaryset = getUtility(IOpenIDRPSummarySet)
        tokens = range(0, self._MAX_RANDOM_TOKEN_RANGE)
        random.shuffle(tokens)
        # This method might be faster by collecting all accounts and summaries
        # that end with the mnemonic. The chances of collision seem minute,
        # given that the intended mnemonic is a unique user name.
        for token in tokens:
            openid_identifier = '%03d/%s' % (token, mnemonic)
            account = self.getByOpenIDIdentifier(openid_identifier)
            if account is not None:
                continue
            summaries = openidrpsummaryset.getByIdentifier(
                identity_url_root + openid_identifier)
            if summaries.count() == 0:
                return openid_identifier.encode('ascii')
        raise AssertionError(
            'An openid_identifier could not be created with the mnemonic '
            "'%s'." % mnemonic)


class AccountPassword(SQLBase):
    """SQLObject wrapper to the AccountPassword table.

    Note that this class is not exported, as the existence of the
    AccountPassword table only needs to be known by this module.
    """
    account = ForeignKey(
        dbName='account', foreignKey='Account', alternateID=True)
    password = StringCol(dbName='password', notNull=True)


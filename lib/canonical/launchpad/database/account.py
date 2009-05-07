# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Implementation classes for Account and associates."""

__metaclass__ = type
__all__ = ['Account', 'AccountPassword', 'AccountSet']

import random

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy
from zope.interface import implements

from storm.expr import Desc, Or
from storm.store import Store

from sqlobject import ForeignKey, StringCol

from canonical.database.constants import UTC_NOW, DEFAULT
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.authtoken import AuthToken
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.ssoserver.model.openidserver import OpenIDRPSummary
from canonical.launchpad.interfaces import IMasterObject, IMasterStore, IStore
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale, AccountStatus, IAccount, IAccountSet)
from canonical.launchpad.interfaces.authtoken import LoginTokenType
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus, IEmailAddress, IEmailAddressSet)
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from canonical.ssoserver.interfaces.openidserver import IOpenIDRPSummarySet
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

    def _getEmails(self, status):
        """Get related `EmailAddress` objects with the given status."""
        result = IStore(EmailAddress).find(
            EmailAddress, accountID=self.id, status=status)
        result.order_by(EmailAddress.email.lower())
        return result

    @property
    def preferredemail(self):
        """See `IAccount`."""
        return self._getEmails(EmailAddressStatus.PREFERRED).one()

    @property
    def validated_emails(self):
        """See `IAccount`."""
        return self._getEmails(EmailAddressStatus.VALIDATED)

    @property
    def guessed_emails(self):
        """See `IAccount`."""
        return self._getEmails(EmailAddressStatus.NEW)

    def getUnvalidatedEmails(self):
        """See `IAccount`."""
        result = IMasterStore(AuthToken).find(
            AuthToken, requester_account=self,
            tokentype=LoginTokenType.VALIDATEEMAIL, date_consumed=None)
        return sorted(set(result.values(AuthToken.email)))

    def setPreferredEmail(self, email):
        """See `IAccount`."""
        if email is None:
            # Mark preferred email address as validated, if it exists.
            # XXX 2009-03-30 jamesh bug=349482: we should be able to
            # use ResultSet.set() here :(
            for address in self._getEmails(EmailAddressStatus.PREFERRED):
                address.status = EmailAddressStatus.VALIDATED
            return

        if not IEmailAddress.providedBy(email):
            raise TypeError("Any person's email address must provide the "
                            "IEmailAddress Interface. %r doesn't." % email)

        email = IMasterObject(removeSecurityProxy(email))
        assert email.accountID == self.id

        # If we have the preferred email address here, we're done.
        if email.status == EmailAddressStatus.PREFERRED:
            return

        existing_preferred_email = self.preferredemail
        if existing_preferred_email is not None:
            assert Store.of(email) is Store.of(existing_preferred_email), (
                "Store of %r is not the same as store of %r" %
                (email, existing_preferred_email))
            existing_preferred_email.status = EmailAddressStatus.VALIDATED
            # Make sure the old preferred email gets flushed before
            # setting the new preferred email.
            Store.of(email).add_flush_order(existing_preferred_email, email)

        email.status = EmailAddressStatus.PREFERRED

        # XXX 2009-03-30 jamesh bug=356092: SSO server can't write to
        # HWDB tables
        # getUtility(IHWSubmissionSet).setOwnership(email)

    def validateAndEnsurePreferredEmail(self, email):
        """See `IAccount`."""
        if not IEmailAddress.providedBy(email):
            raise TypeError, (
                "Any person's email address must provide the IEmailAddress "
                "interface. %s doesn't." % email)

        assert email.accountID == self.id, 'Wrong account! %r, %r' % (
            email.accountID, self.id)

        # This email is already validated and is this person's preferred
        # email, so we have nothing to do.
        if email.status == EmailAddressStatus.PREFERRED:
            return

        email = IMasterObject(email)

        if self.preferredemail is None:
            # This branch will be executed only in the first time a person
            # uses Launchpad. Either when creating a new account or when
            # resetting the password of an automatically created one.
            self.setPreferredEmail(email)
        else:
            email.status = EmailAddressStatus.VALIDATED

            # XXX 2009-03-30 jamesh bug=356092: SSO server can't write
            # to HWDB tables
            # getUtility(IHWSubmissionSet).setOwnership(email)

        # Now that we have validated the email, see if this can be
        # matched to an existing RevisionAuthor.
        # XXX 2009-03-30 jamesh bug=356092: SSO server can't write to
        # revision tables
        # getUtility(IRevisionSet).checkNewVerifiedEmail(email)

    @property
    def recently_authenticated_rps(self):
        """See `IAccount`."""
        result = Store.of(self).find(OpenIDRPSummary, account=self)
        result.order_by(Desc(OpenIDRPSummary.date_last_used))
        return result.config(limit=10)

    def activate(self, comment, password, preferred_email):
        """See `IAccountSpecialRestricted`."""
        if preferred_email is None:
            raise AssertionError(
                "Account %s cannot be activated without a "
                "preferred email address." % self.id)
        self.status = AccountStatus.ACTIVE
        self.status_comment = comment
        self.password = password
        self.validateAndEnsurePreferredEmail(preferred_email)

    def reactivate(self, comment, password, preferred_email):
        """See `IAccountSpecialRestricted`."""
        if password in (None, ''):
            raise AssertionError(
                "Account %s cannot be reactivated without a "
                "password." % self.id)
        self.activate(comment, password, preferred_email)

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

    def createPerson(self, rationale):
        """See `IAccount`."""
        # Need a local import because of circular dependencies.
        from lp.registry.model.person import (
            generate_nick, Person, PersonSet)
        assert self.preferredemail is not None, (
            "Can't create a Person for an account which has no email.")
        assert IMasterStore(Person).find(
            Person, accountID=self.id).one() is None, (
            "Can't create a Person for an account which already has one.")
        name = generate_nick(self.preferredemail.email)
        person = PersonSet()._newPerson(
            name, self.displayname, hide_email_addresses=True,
            rationale=rationale, account=self)

        # Update all associated email addresses to point at the new person.
        result = IMasterStore(EmailAddress).find(
            EmailAddress, accountID=self.id)
        # XXX 2009-03-30 jamesh bug=349482: we should be able to
        # use ResultSet.set() here :(
        for email in result:
            email.personID = person.id

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
        account = IStore(Account).get(Account, id)
        if account is None:
            raise LookupError(id)
        return account

    def createAccountAndEmail(self, email, rationale, displayname, password,
                              password_is_encrypted=False):
        """See `IAccountSet`."""
        from lp.registry.model.person import generate_nick
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
        conditions = [EmailAddress.account == Account.id,
                      EmailAddress.email.lower() == email.lower().strip()]
        store = IStore(Account)
        account = store.find(Account, *conditions).one()
        if account is None:
            raise LookupError(email)
        return account

    def getByOpenIDIdentifier(self, openid_identifier):
        """See `IAccountSet`."""
        store = IStore(Account)
        # XXX sinzui 2008-09-09 bug=264783:
        # Remove the OR clause, only openid_identifier should be used.
        conditions = Or(Account.openid_identifier == openid_identifier,
                        Account.new_openid_identifier == openid_identifier)
        account = store.find(Account, conditions).one()
        if account is None:
            raise LookupError(openid_identifier)
        return account

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
            try:
                account = self.getByOpenIDIdentifier(openid_identifier)
            except LookupError:
                # The identifier is free, so we'll just use it.
                pass
            else:
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


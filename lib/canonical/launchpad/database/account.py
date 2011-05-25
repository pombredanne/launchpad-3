# Copyright 2009 Canonical Ltd.  This software is licensed under the
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
from storm.store import Store
from zope.component import getUtility
from zope.interface import implements
from zope.security.proxy import removeSecurityProxy

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase
from canonical.launchpad.database.emailaddress import EmailAddress
from canonical.launchpad.interfaces.lpstorm import (
    IMasterObject,
    IMasterStore,
    IStore,
    )
from canonical.launchpad.interfaces.account import (
    AccountCreationRationale,
    AccountStatus,
    IAccount,
    IAccountSet,
    )
from canonical.launchpad.interfaces.emailaddress import (
    EmailAddressStatus,
    IEmailAddress,
    IEmailAddressSet,
    )
from canonical.launchpad.interfaces.launchpad import IPasswordEncryptor
from lp.services.openid.model.openididentifier import OpenIdIdentifier


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

    def validateAndEnsurePreferredEmail(self, email):
        """See `IAccount`."""
        if not IEmailAddress.providedBy(email):
            raise TypeError(
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

    def createPerson(self, rationale, name=None, comment=None):
        """See `IAccount`."""
        # Need a local import because of circular dependencies.
        from lp.registry.model.person import (
            generate_nick, Person, PersonSet)
        assert self.preferredemail is not None, (
            "Can't create a Person for an account which has no email.")
        person = IMasterStore(Person).find(Person, accountID=self.id).one()
        assert person is None, (
            "Can't create a Person for an account which already has one.")
        if name is None:
            name = generate_nick(self.preferredemail.email)
        person = PersonSet()._newPerson(
            name, self.displayname, hide_email_addresses=True,
            rationale=rationale, account=self, comment=comment)

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

    def createAccountAndEmail(self, email, rationale, displayname, password,
                              password_is_encrypted=False,
                              openid_identifier=None):
        """See `IAccountSet`."""
        # Convert the PersonCreationRationale to an AccountCreationRationale.
        account_rationale = getattr(AccountCreationRationale, rationale.name)
        account = self.new(
            account_rationale, displayname, password=password,
            password_is_encrypted=password_is_encrypted,
            openid_identifier=openid_identifier)
        account.status = AccountStatus.ACTIVE
        email = getUtility(IEmailAddressSet).new(
            email, status=EmailAddressStatus.PREFERRED, account=account)
        return account, email

    def getByEmail(self, email):
        """See `IAccountSet`."""
        store = IStore(Account)
        try:
            email = email.decode('US-ASCII')
        except (UnicodeDecodeError, UnicodeEncodeError):
            # Non-ascii email addresses are not legal, so assume there are no
            # matching addresses in Launchpad.
            raise LookupError(repr(email))
        account = store.find(
            Account,
            EmailAddress.account == Account.id,
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

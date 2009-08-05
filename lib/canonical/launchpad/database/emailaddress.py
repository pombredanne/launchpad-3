# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = [
    'EmailAddress',
    'EmailAddressSet',
    'HasOwnerMixin',
    'UndeletableEmailAddress',
    ]

import operator
import sha

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.sqlbase import quote, SQLBase, sqlvalues
from canonical.database.enumcol import EnumCol

from canonical.launchpad.interfaces import (
    EmailAddressAlreadyTaken, IEmailAddress, IEmailAddressSet,
    EmailAddressStatus, InvalidEmailAddress)
from canonical.launchpad.validators.email import valid_email


class HasOwnerMixin:
    """A mixing providing an 'owner' property which returns self.person.

    This is to be used on content classes who want to provide IHasOwner but
    have the owner stored in an attribute named 'person' rather than 'owner'.
    """
    owner = property(operator.attrgetter('person'))


class EmailAddress(SQLBase, HasOwnerMixin):
    implements(IEmailAddress)

    _table = 'EmailAddress'
    _defaultOrder = ['email']

    email = StringCol(
            dbName='email', notNull=True, unique=True, alternateID=True)
    status = EnumCol(dbName='status', schema=EmailAddressStatus, notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=False)
    account = ForeignKey(
            dbName='account', foreignKey='Account', notNull=False,
            default=None)

    def __repr__(self):
        return '<EmailAddress at 0x%x <%s> [%s]>' % (
            id(self), self.email, self.status)

    def destroySelf(self):
        """See `IEmailAddress`."""
        # Import this here to avoid circular references.
        from lp.registry.model.mailinglist import (
            MailingListSubscription)

        if self.status == EmailAddressStatus.PREFERRED:
            raise UndeletableEmailAddress(
                "This is a person's preferred email, so it can't be deleted.")
        mailing_list = self.person and self.person.mailing_list
        if mailing_list is not None and mailing_list.address == self.email:
            raise UndeletableEmailAddress(
                "This is the email address of a team's mailing list, so it "
                "can't be deleted.")

        # XXX 2009-05-04 jamesh bug=371567: This function should not
        # be responsible for removing subscriptions, since the SSO
        # server can't write to that table.
        for subscription in MailingListSubscription.selectBy(
            email_address=self):
            subscription.destroySelf()
        super(EmailAddress, self).destroySelf()

    @property
    def rdf_sha1(self):
        """See `IEmailAddress`."""
        return sha.new('mailto:' + self.email).hexdigest().upper()


class EmailAddressSet:
    implements(IEmailAddressSet)

    def getByPerson(self, person):
        """See `IEmailAddressSet`."""
        return EmailAddress.selectBy(person=person, orderBy='email')

    def getPreferredEmailForPeople(self, people):
        """See `IEmailAddressSet`."""
        return EmailAddress.select("""
            EmailAddress.status = %s AND
            EmailAddress.person IN %s
            """ % sqlvalues(EmailAddressStatus.PREFERRED,
                            [person.id for person in people]))

    def getByEmail(self, email):
        """See `IEmailAddressSet`."""
        return EmailAddress.selectOne(
            "lower(email) = %s" % quote(email.strip().lower()))

    def new(self, email, person=None, status=EmailAddressStatus.NEW,
            account=None):
        """See IEmailAddressSet."""
        email = email.strip()

        if not valid_email(email):
            raise InvalidEmailAddress(
                "%s is not a valid email address." % email)

        if self.getByEmail(email) is not None:
            raise EmailAddressAlreadyTaken(
                "The email address '%s' is already registered." % email)
        assert status in EmailAddressStatus.items
        if person is None:
            personID = None
        else:
            personID = person.id
            accountID = account and account.id
            assert person.accountID == accountID, (
                "Email address '%s' must be linked to same account as "
                "person '%s'.  Expected %r (%s), got %r (%s)" % (
                    email, person.name, person.account, person.accountID,
                    account, accountID))
        # We use personID instead of just person, as in some cases the
        # Person record will not yet be replicated from the main
        # Store to the auth master Store.
        return EmailAddress(
            email=email,
            status=status,
            personID=personID,
            account=account)


class UndeletableEmailAddress(Exception):
    """User attempted to delete an email address which can't be deleted."""

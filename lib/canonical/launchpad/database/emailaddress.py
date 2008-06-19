# Copyright 2006 Canonical Ltd.  All rights reserved.
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

from canonical.launchpad.database.mailinglist import MailingListSubscription
from canonical.launchpad.interfaces import (
    EmailAddressAlreadyTaken, IEmailAddress, IEmailAddressSet,
    EmailAddressStatus)


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

    email = StringCol(dbName='email', notNull=True, unique=True)
    status = EnumCol(dbName='status', schema=EmailAddressStatus, notNull=True)
    person = ForeignKey(dbName='person', foreignKey='Person', notNull=True)

    def destroySelf(self):
        """See `IEmailAddress`."""
        if self.status == EmailAddressStatus.PREFERRED:
            raise UndeletableEmailAddress(
                "This is a person's preferred email, so it can't be deleted.")
        mailing_list = self.person.mailing_list
        if mailing_list is not None and mailing_list.address == self.email:
            raise UndeletableEmailAddress(
                "This is the email address of a team's mailing list, so it "
                "can't be deleted.")

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

    def new(self, email, person, status=EmailAddressStatus.NEW):
        """See `IEmailAddressSet`."""
        email = email.strip()
        if self.getByEmail(email) is not None:
            raise EmailAddressAlreadyTaken(
                "The email address '%s' is already registered." % email)
        assert status in EmailAddressStatus.items
        return EmailAddress(email=email, status=status, person=person)


class UndeletableEmailAddress(Exception):
    """User attempted to delete an email address which can't be deleted."""

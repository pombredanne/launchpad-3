# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

__metaclass__ = type
__all__ = ['EmailAddress', 'EmailAddressSet']

from zope.interface import implements

from sqlobject import ForeignKey, StringCol

from canonical.database.sqlbase import quote, SQLBase
from canonical.database.enumcol import EnumCol

from canonical.launchpad.database.mailinglist import MailingListSubscription
from canonical.launchpad.interfaces import (
    EmailAddressAlreadyTaken, IEmailAddress, IEmailAddressSet,
    EmailAddressStatus, InvalidEmailAddress)
from canonical.launchpad.validators.email import valid_email


class EmailAddress(SQLBase):
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

    @property
    def statusname(self):
        return self.status.title

    def destroySelf(self):
        """Destroy this email address and any associated subscriptions."""
        for subscription in MailingListSubscription.selectBy(
            email_address=self):
            subscription.destroySelf()
        super(EmailAddress, self).destroySelf()


class EmailAddressSet:
    implements(IEmailAddressSet)

    def getByPerson(self, person):
        """See IEmailAddressSet."""
        return EmailAddress.selectBy(person=person, orderBy='email')

    def getByEmail(self, email):
        """See IEmailAddressSet."""
        return EmailAddress.selectOne(
            "lower(email) = %s" % quote(email.strip().lower()))

    def new(
            self, email, person=None, status=EmailAddressStatus.NEW,
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
        return EmailAddress(
                email=email, status=status, person=person, account=account)



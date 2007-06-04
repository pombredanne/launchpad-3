# Copyright 2006 Canonical Ltd.  All rights reserved.

"""EmailAddress interfaces."""

__metaclass__ = type
__all__ = ['IEmailAddress', 'IEmailAddressSet', 'EmailAddressAlreadyTaken']

from zope.schema import Int, TextLine
from zope.interface import Interface, Attribute

from canonical.launchpad import _
from canonical.lp.dbschema import EmailAddressStatus


class EmailAddressAlreadyTaken(Exception):
    """The email address is already registered in Launchpad."""


class IEmailAddress(Interface):
    """The object that stores the IPerson's emails."""

    id = Int(title=_('ID'), required=True, readonly=True)
    email = TextLine(title=_('Email Address'), required=True, readonly=False)
    status = Int(title=_('Email Address Status'), required=True, readonly=False)
    person = Int(title=_('Person'), required=True, readonly=False)
    personID = Int(title=_('PersonID'), required=True, readonly=True)
    statusname = Attribute("StatusName")

    def destroySelf():
        """Delete this email from the database."""

    def syncUpdate():
        """Write updates made on this object to the database.

        This should be used when you can't wait until the transaction is
        committed to have some updates actually written to the database.
        """


class IEmailAddressSet(Interface):
    """The set of EmailAddresses."""

    def new(email, person, status=EmailAddressStatus.NEW):
        """Create a new EmailAddress with the given email, pointing to person.

        The given status must be an item of dbschema.EmailAddressStatus.
        """

    def getByPerson(person):
        """Return all email addresses for the given person."""

    def getByEmail(email):
        """Return the EmailAddress object for the given email.

        Return None if there is no such email address.
        """


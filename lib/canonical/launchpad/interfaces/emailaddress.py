# Copyright 2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""EmailAddress interfaces."""

__metaclass__ = type
__all__ = [
    'EmailAddressAlreadyTaken',
    'EmailAddressStatus',
    'IEmailAddress',
    'IEmailAddressSet',
    'InvalidEmailAddress']

from zope.schema import Choice, Int, Object, TextLine
from zope.interface import Interface

from canonical.launchpad import _
from canonical.launchpad.interfaces.account import IAccount
from canonical.lazr import DBEnumeratedType, DBItem
from canonical.lazr.rest.declarations import (
    export_as_webservice_entry, exported)
from canonical.lazr.rest.schema import Reference


class InvalidEmailAddress(Exception):
    """The email address is not valid."""


class EmailAddressAlreadyTaken(Exception):
    """The email address is already registered in Launchpad."""


class EmailAddressStatus(DBEnumeratedType):
    """Email Address Status

    Launchpad keeps track of email addresses associated with a person. They
    can be used to login to the system, or to associate an Arch changeset
    with a person, or to associate a bug system email message with a person,
    for example.
    """

    NEW = DBItem(1, """
        New Email Address

        This email address has had no validation associated with it. It
        has just been created in the system, either by a person claiming
        it as their own, or because we have stored an email message or
        arch changeset including that email address and have created
        a phantom person and email address to record it. WE SHOULD
        NEVER EMAIL A "NEW" EMAIL.
        """)

    VALIDATED = DBItem(2, """
        Validated Email Address

        We have proven that the person associated with this email address
        can read email sent to this email address, by sending a token
        to that address and getting the appropriate response from that
        person.
        """)

    OLD = DBItem(3, """
        Old Email Address

        The email address was validated for this person, but is now no
        longer accessible or in use by them. We should not use this email
        address to login that person, nor should we associate new incoming
        content from that email address with that person.
        """)

    PREFERRED = DBItem(4, """
        Preferred Email Address

        The email address was validated and is the person's choice for
        receiving notifications from Launchpad.
        """)


class IEmailAddress(Interface):
    """The object that stores the `IPerson`'s emails."""
    export_as_webservice_entry()

    id = Int(title=_('ID'), required=True, readonly=True)
    email = exported(
        TextLine(title=_('Email Address'), required=True, readonly=True))
    status = Choice(
        title=_('Email Address Status'), required=True, readonly=False,
        vocabulary=EmailAddressStatus)
    account = Object(title=_('Account'), schema=IAccount, required=False)
    accountID = Int(title=_('AccountID'), required=False, readonly=True)
    person = exported(
        Reference(title=_('Person'), required=True, readonly=True,
                  schema=Interface))
    personID = Int(title=_('PersonID'), required=True, readonly=True)

    def destroySelf():
        """Delete this email from the database."""

    def syncUpdate():
        """Write updates made on this object to the database.

        This should be used when you can't wait until the transaction is
        committed to have some updates actually written to the database.
        """


class IEmailAddressSet(Interface):
    """The set of EmailAddresses."""

    def new(email, person=None, status=EmailAddressStatus.NEW, account=None):
        """Create a new EmailAddress with the given email.
        
        The newly created EmailAddress will point to the person
        and/or account.

        The given status must be an item of EmailAddressStatus.

        :raises InvalidEmailAddress: If the email address is invalid.
        """

    def getByPerson(person):
        """Return all email addresses for the given person."""

    def getByEmail(email):
        """Return the EmailAddress object for the given email.

        Return None if there is no such email address.
        """


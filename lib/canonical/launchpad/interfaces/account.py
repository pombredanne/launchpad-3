# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Account interfaces."""

__metaclass__ = type

__all__ = [
        'AccountStatus',
        'AccountCreationRationale',
        'IAccount',
        'IAccountSet',
        'INACTIVE_ACCOUNT_STATUSES',
        ]


from zope.interface import Interface
from zope.schema import Choice, Datetime, Object, Text, TextLine

from canonical.launchpad import _
from canonical.launchpad.fields import StrippedTextLine, PasswordField
from canonical.launchpad.interfaces import IPerson, PersonCreationRationale
from canonical.lazr import DBEnumeratedType, DBItem


class AccountStatus(DBEnumeratedType):
    """The status of an account."""

    ACTIVE = DBItem(20, """
        Active Launchpad account

        The account is active.
        """)

    DEACTIVATED = DBItem(30, """
        Deactivated Launchpad account

        The account has been deactivated by the account's owner.
        """)

    SUSPENDED = DBItem(40, """
        Suspended Launchpad account

        The account has been suspended by a Launchpad admin.
        """)


INACTIVE_ACCOUNT_STATUSES = [
    AccountStatus.DEACTIVATED, AccountStatus.SUSPENDED]


# At the moment, these two are linked. When we trim out the unnnecessary
# Person records we can seperate these two rationales.
AccountCreationRationale = PersonCreationRationale


class IAccount(Interface):
    """Interface describing an Account."""
    date_created = Datetime(
            title=_('Date Created'), required=True, readonly=True)

    displayname = StrippedTextLine(
            title=_('Display Name'), required=True, readonly=False,
                description=_("Your name as you would like it displayed."))

    person = Object(schema=IPerson, title=_('Person'), required=False)

    creation_rationale = Choice(
            title=_("Rationale for this account's creation."), required=True,
            readonly=True, values=AccountCreationRationale.items)

    status = Choice(
        title=_("The status of this account"), required=True,
        readonly=False, vocabulary=AccountStatus)
    date_status_set = Datetime(
            title=_('Date status last modified.'),
            required=True, readonly=False)
    status_comment = Text(
        title=_("Why are you deactivating your account?"),
        required=False, readonly=False)

    openid_identifier = TextLine(
            title=_("Key used to generate opaque OpenID identities."),
            readonly=True, required=True)

    password = PasswordField(
            title=_("Password."), readonly=False, required=True)


class IAccountSet(Interface):
    """Creation of and access to IAccount providers."""

    def new():
        """Create a new IAccount."""

    def getByEmail(email):
        """Return the IAccount linked to the given email address.

        :param email: A string, not an IEmailAddress provider.

        :return: An IAccount, or None if the given email address does nto
        exist in the database or is not linked to an IAccount.
        """

    def getByPerson(person):
        """Return the IAccount linked to the given IPerson.

        :param person: An IPerson provider.

        :return: An IAccount or None
        """

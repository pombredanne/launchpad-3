# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0211,E0213
"""Account interfaces."""

__metaclass__ = type

__all__ = [
    'AccountStatus',
    'AccountSuspendedError',
    'AccountCreationRationale',
    'IAccount',
    'IAccountPrivate',
    'IAccountPublic',
    'IAccountSet',
    'IAccountSpecialRestricted',
    'INACTIVE_ACCOUNT_STATUSES',
    ]


from lazr.enum import (
    DBEnumeratedType,
    DBItem,
    )
from lazr.restful.fields import (
    CollectionField,
    Reference,
    )
from zope.interface import Attribute, Interface
from zope.schema import (
    Bool,
    Choice,
    Datetime,
    Int,
    Text,
    TextLine,
    )

from canonical.launchpad import _
from lp.services.fields import (
    PasswordField,
    StrippedTextLine,
    )


class AccountSuspendedError(Exception):
    """The account being accessed has been suspended."""


class AccountStatus(DBEnumeratedType):
    """The status of an account."""

    NOACCOUNT = DBItem(10, """
        Unactivated account

        The account has not yet been activated.
        """)

    ACTIVE = DBItem(20, """
        Active account

        The account is active.
        """)

    DEACTIVATED = DBItem(30, """
        Deactivated account

        The account has been deactivated by the account's owner.
        """)

    SUSPENDED = DBItem(40, """
        Suspended Launchpad account

        The account has been suspended by a Launchpad admin.
        """)


INACTIVE_ACCOUNT_STATUSES = [
    AccountStatus.DEACTIVATED, AccountStatus.SUSPENDED]


class AccountCreationRationale(DBEnumeratedType):
    """The rationale for the creation of a given account.

    These statuses are seeded from PersonCreationRationale, as our
    initial accounts where split from the Person table. A number of the
    creation rationales only make sense in this historical context (eg.
    importing bugs into Launchpad no longer needs to create Account records).
    """

    UNKNOWN = DBItem(1, """
        Unknown

        The reason for the creation of this account is unknown.
        """)

    BUGIMPORT = DBItem(2, """
        Existing user in another bugtracker from which we imported bugs.

        A bugzilla import or sf.net import, for instance. The bugtracker from
        which we were importing should be described in
        Person.creation_comment.
        """)

    SOURCEPACKAGEIMPORT = DBItem(3, """
        This person was mentioned in a source package we imported.

        When gina imports source packages, it has to create Person entries for
        the email addresses that are listed as maintainer and/or uploader of
        the package, in case they don't exist in Launchpad.
        """)

    POFILEIMPORT = DBItem(4, """
        This person was mentioned in a POFile imported into Rosetta.

        When importing POFiles into Rosetta, we need to give credit for the
        translations on that POFile to its last translator, which may not
        exist in Launchpad, so we'd need to create it.
        """)

    KEYRINGTRUSTANALYZER = DBItem(5, """
        Created by the keyring trust analyzer.

        The keyring trust analyzer is responsible for scanning GPG keys
        belonging to the strongly connected set and assign all email addresses
        registered on those keys to the people representing their owners in
        Launchpad. If any of these people doesn't exist, it creates them.
        """)

    FROMEMAILMESSAGE = DBItem(6, """
        Created when parsing an email message.

        Sometimes we parse email messages and want to associate them with the
        sender, which may not have a Launchpad account. In that case we need
        to create a Person entry to associate with the email.
        """)

    SOURCEPACKAGEUPLOAD = DBItem(7, """
        This person was mentioned in a source package uploaded.

        Some uploaded packages may be uploaded with a maintainer that is not
        registered in Launchpad, and in these cases, soyuz may decide to
        create the new Person instead of complaining.
        """)

    OWNER_CREATED_LAUNCHPAD = DBItem(8, """
        Created by the owner himself, coming from Launchpad.

        Somebody was navigating through Launchpad and at some point decided to
        create an account.
        """)

    OWNER_CREATED_SHIPIT = DBItem(9, """
        Created by the owner himself, coming from Shipit.

        Somebody went to one of the shipit sites to request Ubuntu CDs and was
        directed to Launchpad to create an account.
        """)

    OWNER_CREATED_UBUNTU_WIKI = DBItem(10, """
        Created by the owner himself, coming from the Ubuntu wiki.

        Somebody went to the Ubuntu wiki and was directed to Launchpad to
        create an account.
        """)

    USER_CREATED = DBItem(11, """
        Created by a user to represent a person which does not use Launchpad.

        A user wanted to reference a person which is not a Launchpad user, so
        he created this "placeholder" profile.
        """)

    OWNER_CREATED_UBUNTU_SHOP = DBItem(12, """
        Created by the owner himself, coming from the Ubuntu Shop.

        Somebody went to the Ubuntu Shop and was directed to Launchpad to
        create an account.
        """)

    OWNER_CREATED_UNKNOWN_TRUSTROOT = DBItem(13, """
        Created by the owner himself, coming from unknown OpenID consumer.

        Somebody went to an OpenID consumer we don't know about and was
        directed to Launchpad to create an account.
        """)

    OWNER_SUBMITTED_HARDWARE_TEST = DBItem(14, """
        Created by a submission to the hardware database.

        Somebody without a Launchpad account made a submission to the
        hardware database.
        """)

    BUGWATCH = DBItem(15, """
        Created by the updating of a bug watch.

        A watch was made against a remote bug that the user submitted or
        commented on.
        """)

    SOFTWARE_CENTER_PURCHASE = DBItem(16, """
        Created by purchasing commercial software through Software Center.

        A purchase of commercial software (ie. subscriptions to a private
        and commercial archive) was made via Software Center.
        """)


class IAccountPublic(Interface):
    """Public information on an `IAccount`."""
    id = Int(title=_('ID'), required=True, readonly=True)

    displayname = StrippedTextLine(
        title=_('Display Name'), required=True, readonly=False,
        description=_("Your name as you would like it displayed."))

    status = Choice(
        title=_("The status of this account"), required=True,
        readonly=False, vocabulary=AccountStatus)

    is_valid = Bool(
        title=_("True if this account is active and has a valid email."),
        required=True, readonly=True)

    # We should use schema=IEmailAddress here, but we can't because that would
    # cause circular dependencies.
    preferredemail = Reference(
        title=_("Preferred email address"),
        description=_("The preferred email address for this person. "
                      "The one we'll use to communicate with them."),
        readonly=True, required=False, schema=Interface)

    validated_emails = CollectionField(
        title=_("Confirmed e-mails of this account."),
        description=_(
            "Confirmed e-mails are the ones in the VALIDATED state.  The "
            "user has confirmed that they are active and that they control "
            "them."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))

    guessed_emails = CollectionField(
        title=_("Guessed e-mails of this account."),
        description=_(
            "Guessed e-mails are the ones in the NEW state.  We believe "
            "that the user owns the address, but they have not confirmed "
            "the fact."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))

    def setPreferredEmail(email):
        """Set the given email address as this account's preferred one.

        If ``email`` is None, the preferred email address is unset, which
        will make the account invalid.
        """

    def validateAndEnsurePreferredEmail(email):
        """Ensure this account has a preferred email.

        If this account doesn't have a preferred email, <email> will be set as
        this account's preferred one. Otherwise it'll be set as VALIDATED and
        this account will keep their old preferred email.

        This method is meant to be the only one to change the status of an
        email address, but as we all know the real world is far from ideal
        and we have to deal with this in one more place, which is the case
        when people explicitly want to change their preferred email address.
        On that case, though, all we have to do is use
        account.setPreferredEmail().
        """


class IAccountPrivate(Interface):
    """Private information on an `IAccount`."""
    date_created = Datetime(
        title=_('Date Created'), required=True, readonly=True)

    creation_rationale = Choice(
        title=_("Rationale for this account's creation."), required=True,
        readonly=True, values=AccountCreationRationale.items)

    openid_identifiers = Attribute(_("Linked OpenId Identifiers"))

    password = PasswordField(
        title=_("Password."), readonly=False, required=True)

    def createPerson(rationale, name=None, comment=None):
        """Create and return a new `IPerson` associated with this account.

        :param rationale: A member of `AccountCreationRationale`.
        :param name: Specify a name for the `IPerson` instead of
            using an automatically generated one.
        :param comment: Populate `IPerson.creation_comment`. See
            `IPerson`.
        """


class IAccountSpecialRestricted(Interface):
    """Attributes of `IAccount` protected with launchpad.Special."""

    date_status_set = Datetime(
        title=_('Date status last modified.'),
        required=True, readonly=False)

    status_comment = Text(
        title=_("Why are you deactivating your account?"),
        required=False, readonly=False)

    # XXX sinzui 2008-07-14 bug=248518:
    # This method would assert the password is not None, but
    # setPreferredEmail() passes the Person's current password, which may
    # be None.  Once that callsite is fixed, we will be able to check that the
    # password is not None here and get rid of the reactivate() method below.
    def activate(comment, password, preferred_email):
        """Activate this account.

        Set the account status to ACTIVE, the account's password to the given
        one and its preferred email address.

        :param comment: An explanation of why the account status changed.
        :param password: The user's password.
        :param preferred_email: The `EmailAddress` to set as the account's
            preferred email address. It cannot be None.
        """

    def reactivate(comment, password, preferred_email):
        """Reactivate this account.

        Just like `IAccountSpecialRestricted`.activate() above, but here the
        password can't be None or the empty string.
        """


class IAccount(IAccountPublic, IAccountPrivate, IAccountSpecialRestricted):
    """Interface describing an `Account`."""


class IAccountSet(Interface):
    """Creation of and access to `IAccount` providers."""

    def new(rationale, displayname, password=None,
            password_is_encrypted=False):
        """Create a new `IAccount`.

        :param rationale: An `AccountCreationRationale` value.
        :param displayname: The user's display name.
        :param password: A password.
        :param password_is_encrypted: If True, the password parameter has
            already been encrypted using the `IPasswordEncryptor` utility.
            If False, the password will be encrypted automatically.

        :return: The newly created `IAccount` provider.
        """

    def get(id):
        """Return the `IAccount` with the given id.

        :raises LookupError: If the account is not found.
        """

    def createAccountAndEmail(email, rationale, displayname, password,
                              password_is_encrypted=False):
        """Create and return both a new `IAccount` and `IEmailAddress`.

        The account will be in the ACTIVE state, with the email address set as
        its preferred email address.
        """

    def getByEmail(email):
        """Return the `IAccount` linked to the given email address.

        :param email: A string, not an `IEmailAddress` provider.

        :return: An `IAccount`.

        :raises LookupError: If the account is not found.
        """

    def getByOpenIDIdentifier(openid_identity):
        """Return the `IAccount` with the given OpenID identifier.

         :param open_identifier: An ascii compatible string that is either
             the old or new openid_identifier that belongs to an account.
         :return: An `IAccount`
         :raises LookupError: If the account is not found.
         """


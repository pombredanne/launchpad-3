# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Login token interfaces."""

__metaclass__ = type

__all__ = [
    'LoginTokenType',
    'IAuthToken',
    'IAuthTokenSet',
    ]

from zope.schema import Choice, Datetime, Int, Text, TextLine
from zope.interface import Attribute, Interface

from canonical.launchpad import _
from canonical.launchpad.fields import PasswordField
from lazr.enum import DBEnumeratedType, DBItem


class LoginTokenType(DBEnumeratedType):
    """Login token type

    Tokens are emailed to users in workflows that require email address
    validation, such as forgotten password recovery or account merging.
    We need to identify the type of request so we know what workflow
    is being processed.
    """

    PASSWORDRECOVERY = DBItem(1, """
        Password Recovery

        User has forgotten or never known their password and need to
        reset it.
        """)

    ACCOUNTMERGE = DBItem(2, """
        Account Merge

        User has requested that another account be merged into their
        current one.
        """)

    NEWACCOUNT = DBItem(3, """
        New Account

        A new account is being setup. They need to verify their email address
        before we allow them to set a password and log in.
        """)

    VALIDATEEMAIL = DBItem(4, """
        Validate Email

        A user has added more email addresses to their account and they
        need to be validated.
        """)

    VALIDATETEAMEMAIL = DBItem(5, """
        Validate Team Email

        One of the team administrators is trying to add a contact email
        address for the team, but this address need to be validated first.
        """)

    VALIDATEGPG = DBItem(6, """
        Validate GPG key

        A user has submited a new GPG key to his account and it need to
        be validated.
        """)

    VALIDATESIGNONLYGPG = DBItem(7, """
        Validate a sign-only GPG key

        A user has submitted a new sign-only GPG key to his account and it
        needs to be validated.
        """)

    PROFILECLAIM = DBItem(8, """
        Claim an unvalidated Launchpad profile

        A user has found an unvalidated profile in Launchpad and is trying
        to claim it.
        """)

    NEWPROFILE = DBItem(9, """
        A user created a new Launchpad profile for another person.

        Any Launchpad user can create new "placeholder" profiles to represent
        people who don't use Launchpad. The person that a given profile
        represents has to first use the token to finish the registration
        process in order to be able to login with that profile.
        """)

    TEAMCLAIM = DBItem(10, """
        Turn an unvalidated Launchpad profile into a team.

        A user has found an unvalidated profile in Launchpad and is trying
        to turn it into a team.
        """)

    BUGTRACKER = DBItem(11, """
        Launchpad is authenticating itself with a remote bug tracker.

        The remote bug tracker will use the LoginToken to authenticate
        Launchpad.
        """)

    NEWPERSONLESSACCOUNT = DBItem(12, """
        New Personless Account

        A new personless account is being setup. They need to verify their
        email address before we allow them to set a password and log in.  At
        the end, this account will not have a Person associated with.
        """)


class IAuthToken(Interface):
    """The object that stores one time tokens used for validating email
    addresses and other tasks that require verifying if an email address is
    valid such as password recovery, account merging and registration of new
    accounts. All LoginTokens must be deleted once they are "consumed"."""
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    date_created = Datetime(
        title=_('The timestamp that this request was made.'), required=True,
        )
    date_consumed = Datetime(
        title=_('Date and time this was consumed'),
        required=False, readonly=False
        )

    tokentype = Choice(
        title=_('The type of request.'), required=True,
        vocabulary=LoginTokenType
        )
    token = Text(
        title=_('The token (not the URL) emailed used to uniquely identify '
                'this request.'),
        required=True,
        )

    requester = Int(
        title=_('The Person that made this request.'), required=True,
        )
    requester_account = Int(
        title=_('The account that made this request.'), required=True)
    requesteremail = Text(
        title=_('The email address that was used to login when making this '
                'request.'),
        required=False,
        )

    email = TextLine(
        title=_('Email address'),
        required=True,
        )

    redirection_url = Text(
        title=_('The URL to where we should redirect the user after '
                'processing his request'),
        required=False,
        )

    # used for launchpad page layout
    title = Attribute('Title')

    # Quick fix for Bug #2481
    password = PasswordField(
        title=_('Password'), required=True, readonly=False)

    def consume():
        """Mark this token as consumed by setting date_consumed.

        As a consequence of a token being consumed, all tokens requested by
        the same person and with the same requester email will also be marked
        as consumed.
        """

    def sendEmailValidationRequest():
        """Send an email message with a magic URL to validate self.email."""

    def sendPasswordResetEmail():
        """Send an email message to the requester with a magic URL that allows
        him to reset his password.
        """

    def sendNewUserEmail():
        """Send an email message to the requester with a magic URL that allows
        him to finish the Launchpad registration process.
        """


class IAuthTokenSet(Interface):
    """The set of AuthTokens."""

    title = Attribute('Title')

    def get(id, default=None):
        """Return the AuthToken object with the given id.

        Return the default value if there's no such AuthToken.
        """

    def searchByEmailAccountAndType(email, account, type, consumed=None):
        """Return all AuthTokens for the given email, account and type.

        :param email: The email address to search for.
        :param account: The Account object representing the requester
            to search for.
        :param type: The AuthTokenType to search for.
        :param consumed: A flag indicating whether to return consumed tokens.
            If False, only unconsumed tokens will be returned.
            If True, only consumed tokens will be returned.
            If None, this parameter will be ignored and all tokens will be
            returned.
        """

    def deleteByEmailAccountAndType(email, account, type):
        """Delete all AuthToken entries with the given email,
        requester account and type."""

    def new(requester, requesteremail, email, tokentype, redirection_url):
        """Create a new AuthToken object.

        :param requester: a Person object or None (in case of a new
            account)
        :param requesteremail: the email address used to login on the
            system. Can also be None in case of a new account
        :param email: the email address that this request will be sent
            to.  It should be previously validated by valid_email()
        :param tokentype: the type of the request, according to
            LoginTokenType.
        :param redirection_url: the URL the user will be forwarded to
            after consuming the token.  May be None.
        """

    def __getitem__(id):
        """Returns the AuthToken with the given id.

        Raises KeyError if there is no such AuthToken.
        """


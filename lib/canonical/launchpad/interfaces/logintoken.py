# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Login token interfaces."""

__metaclass__ = type

__all__ = [
    'ILoginToken',
    'ILoginTokenSet',
    'IGPGKeyValidationForm',
    'LoginTokenType',
    ]

from zope.schema import Choice, Datetime, Int, Text, TextLine
from zope.interface import Attribute, Interface

from canonical.lazr import DBEnumeratedType, DBItem
from canonical.launchpad import _
from canonical.launchpad.fields import PasswordField


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


class ILoginToken(Interface):
    """The object that stores one time tokens used for validating email
    addresses and other tasks that require verifying if an email address is
    valid such as password recovery, account merging and registration of new
    accounts. All LoginTokens must be deleted once they are "consumed"."""
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = TextLine(
        title=_('Email address'),
        required=True,
        )
    requester = Int(
        title=_('The Person that made this request.'), required=True,
        )
    requesteremail = Text(
        title=_('The email address that was used to login when making this '
                'request.'),
        required=False,
        )
    redirection_url = Text(
        title=_('The URL to where we should redirect the user after processing '
                'his request'),
        required=False,
        )
    created = Datetime(
        title=_('The timestamp that this request was made.'), required=True,
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
    fingerprint = Text(
        title=_('OpenPGP key fingerprint used to retrive key information when necessary.'),
        required=False,
        )
    date_consumed = Datetime(
        title=_('Date and time this was consumed'),
        required=False, readonly=False
        )

    # used for launchpad page layout
    title = Attribute('Title')

    # Quick fix for Bug #2481
    password = PasswordField(
            title=_('Password'), required=True, readonly=False,
            description=_("Enter the same password in each field.")
            )

    def consume():
        """Mark this token as consumed by setting date_consumed.

        As a consequence of a token being consumed, all tokens requested by
        the same person and with the same requester email will also be marked
        as consumed.
        """

    def destroySelf():
        """Remove this LoginToken from the database.

        We need this because once the token is used (either when registering a
        new user, validating an email address or reseting a password), we have
        to delete it so nobody can use that token again.
        """

    def sendEmailValidationRequest(appurl):
        """Send an email message with a magic URL to validate self.email."""

    def sendGPGValidationRequest(key):
        """Send an email message with a magic URL to confirm the OpenPGP key.
        If fingerprint is set, send the message encrypted.
        """

    def sendPasswordResetEmail():
        """Send an email message to the requester with a magic URL that allows
        him to reset his password.
        """

    def sendNewUserEmail():
        """Send an email message to the requester with a magic URL that allows
        him to finish the Launchpad registration process.
        """

    def sendPasswordResetNeutralEmail():
        """Identical to ILoginToken.sendPasswordResetEmail but in this case
        the email sent is neutral --it doesn't mention Launchpad.

        This is needed when Launchpad is acting as an OpenID provider for the
        Ubuntu Shop/Wiki.
        """

    def sendNewUserNeutralEmail():
        """Identical to ILoginToken.sendNewUserEmail but in this case
        the email sent is neutral --it doesn't mention Launchpad.

        This is needed when Launchpad is acting as an OpenID provider for the
        Ubuntu Shop/Wiki.
        """

    def sendProfileCreatedEmail(profile, comment):
        """Notify the profile's email owner that a new profile was created.

        Send an email message to this token's email address explaining that
        another user has created a launchpad profile for him and providing
        a link where he can finish the registration process.
        """

    def sendMergeRequestEmail():
        """Send an email to self.email (the dupe account's email address)
        with the URL of a page to finish the merge of Launchpad accounts.
        """

    def sendTeamEmailAddressValidationEmail(user):
        """Send an email to self.email containing a URL to the page where it
        can be set as the requester's (the team) contact address.

        The message also includes the team administrator who made this
        request on behalf of the team.
        """

    def sendClaimProfileEmail():
        """Send an email to self.email with instructions on how to finish
        claiming the profile that owns self.email.
        """


class ILoginTokenSet(Interface):
    """The set of LoginTokens."""

    title = Attribute('Title')

    def get(id, default=None):
        """Return the LoginToken object with the given id.

        Return the default value if there's no such LoginToken.
        """

    def searchByEmailRequesterAndType(email, requester, type):
        """Return all LoginTokens for the given email, requester and type."""

    def deleteByEmailRequesterAndType(email, requester, type):
        """Delete all LoginToken entries with the given email, requester and
        type."""

    def searchByFingerprintRequesterAndType(fingerprint, requester, type):
        """Return all LoginTokens for the given fingerprint, requester and
        type."""

    def deleteByFingerprintRequesterAndType(fingerprint, requester, type):
        """Delete all LoginToken entries with the given fingerprint,
        requester and type.
        """

    def getPendingGPGKeys(requesterid=None):
        """Return tokens for OpenPGP keys pending validation, optionally for
        a single user.
        """

    def new(requester, requesteremail, email, tokentype, fingerprint=None,
            redirection_url=None):
        """Create a new LoginToken object. Parameters must be:
        requester: a Person object or None (in case of a new account)

        requesteremail: the email address used to login on the system. Can
                        also be None in case of a new account

        email: the email address that this request will be sent to.
        It should be previosly validated by valid_email()

        tokentype: the type of the request, according to LoginTokenType.

        fingerprint: The OpenPGP key fingerprint used to retrieve key
        information from the key server if necessary. This can be None if
        not required to process the 'request' in question.
        """

    def __getitem__(id):
        """Returns the LoginToken with the given id.

        Raises KeyError if there is no such LoginToken.
        """

    def get(id, default=None):
        """Returns the LoginToken with the given id.

        Returns the default value if there is no such LoginToken.
        """


class IGPGKeyValidationForm(Interface):
    """The schema used by ILoginToken's +validategpg form."""

    text_signature = Text(
        title=_('Signed text'), required=True,
        description=_('The validation text, signed with your key.'))


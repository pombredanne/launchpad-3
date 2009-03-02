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

from canonical.launchpad import _
from canonical.launchpad.fields import PasswordField
from canonical.launchpad.interfaces.authtoken import AuthTokenType, IAuthToken
from canonical.lazr import DBItem


class LoginTokenType(AuthTokenType):
    """Login token type

    This extends AuthTokenType to cover the additional types of
    workflows that Launchpad deals with.
    """

    ACCOUNTMERGE = DBItem(2, """
        Account Merge

        User has requested that another account be merged into their
        current one.
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



class ILoginToken(IAuthToken):
    """The object that stores one time tokens used for validating email
    addresses and other tasks that require verifying if an email address is
    valid such as password recovery, account merging and registration of new
    accounts. All LoginTokens must be deleted once they are "consumed"."""

    tokentype = Choice(
        title=_('The type of request.'), required=True,
        vocabulary=LoginTokenType
        )

    fingerprint = Text(
        title=_('OpenPGP key fingerprint used to retrieve key information '
                'when necessary.'),
        required=False,
        )

    def sendGPGValidationRequest(key):
        """Send an email message with a magic URL to confirm the OpenPGP key.
        If fingerprint is set, send the message encrypted.
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

    def sendClaimTeamEmail():
        """E-mail instructions for claiming a team to self.email."""


class ILoginTokenSet(Interface):
    """The set of LoginTokens."""

    title = Attribute('Title')

    def get(id, default=None):
        """Return the LoginToken object with the given id.

        Return the default value if there's no such LoginToken.
        """

    def searchByEmailRequesterAndType(email, requester, type, consumed=None):
        """Return all LoginTokens for the given email, requester and type.

        :param email: The email address to search for.
        :param requester: The Person object representing the requester
            to search for.
        :param type: The LoginTokenType to search for.
        :param consumed: A flag indicating whether to return consumed tokens.
            If False, only unconsumed tokens will be returned.
            If True, only consumed tokens will be returned.
            If None, this parameter will be ignored and all tokens will be
            returned.
        """

    def deleteByEmailRequesterAndType(email, requester, type):
        """Delete all LoginToken entries with the given email, requester and
        type."""

    def searchByFingerprintRequesterAndType(fingerprint, requester, type,
                                            consumed=None):
        """Return all LoginTokens for the given fingerprint, requester and
        type.

        :param fingerprint: The LoginToken fingerprint to search for.
        :param requester: The Person object representing the requester
            to search for.
        :param type: The LoginTokenType to search for.
        :param consumed: A flag indicating whether to return consumed tokens.
            If False, only unconsumed tokens will be returned.
            If True, only consumed tokens will be returned.
            If None, this parameter will be ignored and all tokens will be
            returned.
        """

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
        It should be previously validated by valid_email()

        tokentype: the type of the request, according to LoginTokenType.

        fingerprint: The OpenPGP key fingerprint used to retrieve key
        information from the key server if necessary. This can be None if
        not required to process the 'request' in question.
        """

    def __getitem__(id):
        """Returns the LoginToken with the given id.

        Raises KeyError if there is no such LoginToken.
        """


class IGPGKeyValidationForm(Interface):
    """The schema used by ILoginToken's +validategpg form."""

    text_signature = Text(
        title=_('Signed text'), required=True,
        description=_('The validation text, signed with your key.'))


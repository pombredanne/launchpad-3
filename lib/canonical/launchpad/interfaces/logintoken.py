# Imports from zope
from zope.schema import Bool, Bytes, Choice, Datetime, Int, Text, \
                        TextLine, Password
from zope.interface import Interface, Attribute
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')


class ILoginToken(Interface):
    """The object that stores one time tokens used for validating email
    addresses and other tasks that require verifying if an email address is
    valid such as password recovery, account merging and registration of new
    accounts. All LoginTokens must be deleted once they are "consumed"."""
    id = Int(
        title=_('ID'), required=True, readonly=True,
        )
    email = Text(
        title=_('The email address that this request was sent to.'),
                required=True,
        )
    requester = Int(
        title=_('The Person that made this request.'), required=True,
        )
    requesteremail = Text(
        title=_('The email address that was used to login when making this request.'),
                required=True,
        )
    created = Datetime(
        title=_('The timestamp that this request was made.'), required=True,
        )
    tokentype = Text(
        title=_('The type of request, as per dbschema.TokenType.'),
                required=True,
        )
    token = Text(
        title=_('The token (not the URL) emailed used to uniquely identify this request.'),
                required=True,
        )

    # used for launchpad page layout
    title = Attribute('Title')

    def destroySelf():
        """Remove this LoginToken from the database.

        We need this because once the token is used (either when registering a
        new user, validating an email address or reseting a password), we have
        to delete it so nobody can use that token again.
        """


class ILoginTokenSet(Interface):
    """The set of LoginTokens."""

    title = Attribute('Title')

    def get(id, default=None):
        """Return the LoginToken object with the given id.

        Return the default value if there's no such LoginToken.
        """

    def new(requester, requesteremail, email, tokentype):
        """ Create a new LoginToken object. Parameters must be:
        requester: a Person object or None (in case of a new account)

        requesteremail: the email address used to login on the system. Can
        also be None in case of a new account
        
        email: the email address that this request will be sent to
        
        tokentype: the type of the request, according to
        dbschema.LoginTokenType
        """

    def __getitem__(id):
        """Returns the LoginToken with the given id.

        Raises KeyError if there is no such LoginToken.
        """

    def get(id, default=None):
        """Returns the LoginToken with the given id.

        Returns the default value if there is no such LoginToken.
        """



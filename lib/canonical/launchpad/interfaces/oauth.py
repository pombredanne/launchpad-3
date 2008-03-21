# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""OAuth interfaces."""

__metaclass__ = type

__all__ = [
    'OAUTH_REALM',
    'OAUTH_CHALLENGE',
    'IOAuthAccessToken',
    'IOAuthConsumer',
    'IOAuthConsumerSet',
    'IOAuthNonce',
    'IOAuthRequestToken',
    'IOAuthRequestTokenSet',
    'NonceAlreadyUsed',
    'OAuthPermission']

from zope.schema import Bool, Choice, Datetime, Object, TextLine
from zope.interface import Interface

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson


# The challenge included in responses with a 401 status.
OAUTH_REALM = 'https://api.launchpad.net'
OAUTH_CHALLENGE = 'OAuth realm="%s"' % OAUTH_REALM


class OAuthPermission(DBEnumeratedType):
    """The permission granted by the user to the OAuth consumer."""

    UNAUTHORIZED = DBItem(10, """
        No Access

        The application will not be allowed to access Launchpad on your
        behalf.
        """)

    READ_PUBLIC = DBItem(20, """
        Read Non-Private Data

        The application will be able to access Launchpad on your behalf
        but only for reading non-private data.
        """)

    WRITE_PUBLIC = DBItem(30, """
        Change Non-Private Data

        The application will be able to access Launchpad on your behalf
        for reading and changing non-private data.
        """)

    READ_PRIVATE = DBItem(40, """
        Read Anything

        The application will be able to access Launchpad on your behalf
        for reading anything, including private data.
        """)

    WRITE_PRIVATE = DBItem(50, """
        Change Anything

        The application will be able to access Launchpad on your behalf
        for reading and changing anything, including private data.
        """)


class IOAuthConsumer(Interface):
    """An application which acts on behalf of a Launchpad user."""

    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    disabled = Bool(
        title=_('Disabled?'), required=False, readonly=False,
        description=_('Disabled consumers are not allowed to access any '
                      'protected resources.'))
    key = TextLine(
        title=_('Key'), required=True, readonly=True,
        description=_('The unique key which identifies a consumer. It is '
                      'included by the consumer in each request made.'))
    secret = TextLine(
        title=_('Secret'), required=False, readonly=False,
        description=_('The secret which, if not empty, should be used by the '
                      'consumer to sign its requests.'))

    def newRequestToken():
        """Return a new `IOAuthRequestToken` with a random key and secret.

        Also sets the token's date_expires to `REQUEST_TOKEN_VALIDITY` hours
        from the creation date (now).

        The other attributes of the token are supposed to be set whenever the
        user logs into Launchpad and grants (or not) access to this consumer.
        """

    def getAccessToken(key):
        """Return the `IOAuthAccessToken` with the given key.

        If the token with the given key does not exist or is associated with
        another consumer, return None.
        """

    def getRequestToken(key):
        """Return the `IOAuthRequestToken` with the given key.

        If the token with the given key does not exist or is associated with
        another consumer, return None.
        """


class IOAuthConsumerSet(Interface):
    """The set of OAuth consumers."""

    def new(key, secret=''):
        """Return the newly created consumer.

        You must make sure the given `key` is not already in use by another
        consumer before trying to create a new one.

        The `secret` defaults to an empty string because most consumers will
        be open source desktop applications for which it wouldn't be actually
        secret.

        :param key: The unique key which will be associated with the new
            consumer.
        :param secret: A secret which should be used by the consumer to sign
            its requests.
        """

    def getByKey(key):
        """Return the consumer with the given key.

        If there's no consumer with the given key, return None.

        :param key: The unique key associated with a consumer.
        """


class IOAuthToken(Interface):
    """Base class for `IOAuthRequestToken` and `IOAuthAccessToken`.

    This class contains the commonalities of the two token classes we actually
    care about and shall not be used on its own.
    """

    consumer = Object(
        schema=IOAuthConsumer, title=_('The consumer.'),
        description=_("The consumer which will access Launchpad on the "
                      "user's behalf."))
    person = Object(
        schema=IPerson, title=_('Person'), required=False, readonly=False,
        description=_('The user on whose behalf the consumer is accessing.'))
    permission = Choice(
        title=_('Access level'), required=True, readonly=False,
        vocabulary=OAuthPermission,
        description=_('The level of access given to the application acting '
                      'on your behalf.'))
    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    date_expires = Datetime(
        title=_('Date expires'), required=False, readonly=False,
        description=_('From this date onwards this token can not be used '
                      'by the consumer to access protected resources.'))
    key = TextLine(
        title=_('Key'), required=True, readonly=True,
        description=_('The key used to identify this token.  It is included '
                      'by the consumer in each request.'))
    secret = TextLine(
        title=_('Secret'), required=True, readonly=True,
        description=_('The secret associated with this token.  It is used '
                      'by the consumer to sign its requests.'))


class IOAuthAccessToken(IOAuthToken):
    """A token used by a consumer to access protected resources in LP.

    It's created automatically once a user logs in and grants access to a
    consumer.  The consumer then exchanges an `IOAuthRequestToken` for it.
    """

    def ensureNonce(nonce, timestamp):
        """Ensure the nonce hasn't been used with a different timestamp.

        :raises NonceAlreadyUsed: If the nonce has been used before with a
            timestamp not in the accepted range (+/- `NONCE_TIME_WINDOW`
            seconds from the timestamp stored in the database).

        If the nonce has never been used together with this token before,
        we store it in the database with the given timestamp and associated
        with this token.
        """


class IOAuthRequestToken(IOAuthToken):
    """A token used by a consumer to ask the user to authenticate on LP.

    After the user has authenticated and granted access to that consumer, the
    request token is exchanged for an access token and is then destroyed.
    """

    date_reviewed = Datetime(
        title=_('Date reviewed'), required=True, readonly=True,
        description=_('The date in which the user authorized (or not) the '
                      'consumer to access his protected resources on '
                      'Launchpad.'))
    is_reviewed = Bool(
        title=_('Has this token been reviewed?'),
        required=False, readonly=True,
        description=_('A reviewed request token can only be exchanged for an '
                      'access token (in case the user granted access).'))

    def review(user, permission):
        """Grant `permission` as `user` to this token's consumer.

        Set this token's person, permission and date_reviewed.  This will also
        cause this token to be marked as used, meaning it can only be
        exchanged for an access token with the same permission, consumer and
        person.
        """

    def createAccessToken():
        """Create an `IOAuthAccessToken` identical to this request token.

        After the access token is created, this one is deleted as it can't be
        used anymore.

        You must not attempt to create an access token if the request token
        hasn't been reviewed or if its permission is UNAUTHORIZED.
        """


class IOAuthRequestTokenSet(Interface):
    """The set of `IOAuthRequestToken`s."""

    def getByKey(key):
        """Return the IOAuthRequestToken with the given key.

        If it doesn't exist, return None.
        """


class IOAuthNonce(Interface):
    """The unique (nonce,timestamp) for requests using a given access token.

    The nonce value (which is unique for all requests with that timestamp)
    is generated by the consumer and included, together with the timestamp,
    in each request made.  It's used to prevent replay attacks.
    """

    request_timestamp = Datetime(
        title=_('Date issued'), required=True, readonly=True)
    access_token = Object(schema=IOAuthAccessToken, title=_('The token'))
    nonce = TextLine(title=_('Nonce'), required=True, readonly=True)


class NonceAlreadyUsed(Exception):
    """Nonce has been used together with same token but another timestamp."""

# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0213

"""OAuth interfaces."""

__metaclass__ = type

__all__ = ['IOAuthAccessToken', 'IOAuthConsumer', 'IOAuthConsumerSet', 
           'IOAuthNonce', 'IOAuthRequestToken', 'OAuthPermission']

from zope.schema import Bool, Choice, Datetime, Object, TextLine
from zope.interface import Interface

from canonical.lazr import DBEnumeratedType, DBItem

from canonical.launchpad import _
from canonical.launchpad.interfaces.person import IPerson


class OAuthPermission(DBEnumeratedType):
    """The permission granted by the user to the OAuth consumer."""

    UNAUTHORIZED = DBItem(10, """
        Not authorized

        User didn't authorize the consumer to act on his behalf.
        """)

    READ_PUBLIC = DBItem(20, """
        Read public data

        Consumer can act on the user's behalf but only for reading public
        data.
        """)

    WRITE_PUBLIC = DBItem(30, """
        Read and write public data

        Consumer can act on the user's behalf but only for reading/writing
        public data.
        """)

    READ_PRIVATE = DBItem(40, """
        Read public and private data

        Consumer can act on the user's behalf but only for reading
        public/private data.
        """)

    WRITE_PRIVATE = DBItem(50, """
        Read/write public and private data

        Consumer can act on the user's behalf for reading and writing
        public/private data.
        """)


class IOAuthConsumer(Interface):
    """An application which acts on behalf of a Launchpad user."""
    
    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    disabled = Bool(title=_('Disabled?'), required=False, readonly=False)
    key = TextLine(title=_('Key'), required=True, readonly=True)
    secret = TextLine(title=_('Secret'), required=False, readonly=False)


class IOAuthConsumerSet(Interface):
    """The set of OAuth consumers."""

    def new(key, secret=''):
        """Return the newly created consumer."""

    def getByKey(key):
        """Return the consumer for the given key."""
    

class IOAuthToken(Interface):
    """Base class for IOAuthRequestToken and IOAuthAccessToken."""

    consumer = Object(schema=IOAuthConsumer, title=_('The consumer.'))
    person = Object(
        schema=IPerson, title=_('Person'), required=False, readonly=False)
    permission = Choice(
        title=_('Permission'), required=False, readonly=False,
        vocabulary=OAuthPermission)
    date_created = Datetime(
        title=_('Date created'), required=True, readonly=True)
    date_expires = Datetime(
        title=_('Date expires'), required=False, readonly=False)
    key = TextLine(title=_('Key'), required=True, readonly=True)
    secret = TextLine(title=_('Secret'), required=True, readonly=True)


class IOAuthAccessToken(IOAuthToken):
    """A token used by a consumer to access protected resources in LP."""


class IOAuthRequestToken(IOAuthToken):
    """A token used by a consumer to ask the user to authenticate on LP.

    After the user has authenticated and granted access to that consumer, the
    request token is exchanged for an access token and is then destroyed.
    """

    date_reviewed = Datetime(
        title=_('Date reviewed'), required=True, readonly=True)


class IOAuthNonce(Interface):
    """The unique (nonce,timestamp) for requests from a given consumer.

    This is used to prevent replay attacks.
    """

    request_timestamp = Datetime(
        title=_('Date issued'), required=True, readonly=True)
    consumer = Object(schema=IOAuthConsumer, title=_('The consumer.'))
    nonce = TextLine(title=_('Nonce'), required=True, readonly=True)



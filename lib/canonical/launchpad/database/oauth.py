# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthAccessToken',
    'OAuthConsumer',
    'OAuthConsumerSet',
    'OAuthNonce',
    'OAuthRequestToken']

import random
import pytz
from datetime import datetime, timedelta

from zope.interface import implements

from sqlobject import BoolCol, ForeignKey, StringCol

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IOAuthAccessToken, IOAuthConsumer, IOAuthConsumerSet, IOAuthNonce,
    IOAuthRequestToken, OAuthPermission)


# How many hours should a request token be valid for?
REQUEST_TOKEN_VALIDITY = 12
# How many days should an access token be valid for, by default?
ACCESS_TOKEN_VALIDITY = 30


class OAuthConsumer(SQLBase):
    """See `IOAuthConsumer`."""
    implements(IOAuthConsumer)

    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    disabled = BoolCol(notNull=True, default=False)
    key = StringCol(notNull=True)
    secret = StringCol(notNull=False, default='')

    def newRequestToken(self):
        """See `IOAuthConsumer`."""
        characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
        key_length = 20
        key = ''.join(
            random.choice(characters) for count in range(key_length))
        while OAuthRequestToken.selectOneBy(key=key) is not None:
            key = ''.join(
                random.choice(characters) for count in range(key_length))
        secret_length = 80
        secret = ''.join(
            random.choice(characters) for count in range(secret_length))
        date_expires = (datetime.now(pytz.timezone('UTC'))
                        + timedelta(hours=REQUEST_TOKEN_VALIDITY))
        return OAuthRequestToken(
            consumer=self, key=key, secret=secret, date_expires=date_expires)

    def getRequestToken(self, key):
        """See `IOAuthConsumer`."""
        return OAuthRequestToken.selectOneBy(key=key, consumer=self)


class OAuthConsumerSet:
    """See `IOAuthConsumerSet`."""
    implements(IOAuthConsumerSet)

    def new(self, key, secret=''):
        """See `IOAuthConsumerSet`."""
        assert self.getByKey(key) is None, (
            "The key '%s' is already in use by another consumer." % key)
        return OAuthConsumer(key=key, secret=secret)

    def getByKey(self, key):
        """See `IOAuthConsumerSet`."""
        return OAuthConsumer.selectOneBy(key=key)


class OAuthToken(SQLBase):
    """See `IOAuthToken`."""

    consumer = ForeignKey(
        dbName='consumer', foreignKey='OAuthConsumer', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=False, default=None)
    permission = EnumCol(
        enum=OAuthPermission, notNull=False, default=None)
    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    date_expires = UtcDateTimeCol(notNull=False, default=None)
    key = StringCol(notNull=True)
    secret = StringCol(notNull=False, default='')


class OAuthAccessToken(OAuthToken):
    """See `IOAuthAccessToken`."""
    implements(IOAuthAccessToken)


class OAuthRequestToken(OAuthToken):
    """See `IOAuthAccessToken`."""
    implements(IOAuthRequestToken)

    date_reviewed = UtcDateTimeCol(default=None, notNull=False)

    def review(self, user, permission):
        """See `IOAuthConsumer`."""
        assert not self.is_reviewed, (
            "Request tokens can be reviewed only once.")
        self.date_reviewed = datetime.now(pytz.timezone('UTC'))
        self.person = user
        self.permission = permission

    def createAccessToken(self):
        """See `IOAuthConsumer`."""
        assert self.is_reviewed, (
            'Cannot create an access token from an unreviewed request token.')
        assert self.permission != OAuthPermission.UNAUTHORIZED, (
            'The user did not grant access to this consumer.')
        key, secret = create_token_key_and_secret(table=OAuthAccessToken)
        date_expires = datetime.now(pytz.timezone('UTC')) + timedelta(
            days=ACCESS_TOKEN_VALIDITY)
        access_token = OAuthAccessToken(
            consumer=self.consumer, person=self.person, key=key,
            secret=secret, permission=self.permission,
            date_expires=date_expires)
        self.destroySelf()
        return access_token

    @property
    def is_reviewed(self):
        """See `IOAuthConsumer`."""
        return self.date_reviewed is not None


class OAuthNonce(SQLBase):
    """See `IOAuthNonce`."""
    implements(IOAuthNonce)

    consumer = ForeignKey(
        dbName='consumer', foreignKey='OAuthConsumer', notNull=True)
    request_timestamp = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    nonce = StringCol(notNull=True)


# XXX: Use this in OAuthConsumer.newRequestToken() as well.
def create_token_key_and_secret(table):
    """Create a key and secret for an OAuth token.

    :table: The table in which the key/secret are going to be used. Must be
        one of OAuthAccessToken or OAuthRequestToken.

    The key will have a lenght of 20 and we'll make sure it's not yet in the
    given table.  The secret will have a length of 80.
    """
    characters = '0123456789bcdfghjklmnpqrstvwxzBCDFGHJKLMNPQRSTVWXZ'
    key_length = 20
    key = ''.join(
        random.choice(characters) for count in range(key_length))
    while table.selectOneBy(key=key) is not None:
        key = ''.join(
            random.choice(characters) for count in range(key_length))
    secret_length = 80
    secret = ''.join(
        random.choice(characters) for count in range(secret_length))
    return key, secret

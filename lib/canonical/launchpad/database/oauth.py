# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthAccessToken',
    'OAuthConsumer',
    'OAuthConsumerSet',
    'OAuthNonce',
    'OAuthRequestToken']

from zope.interface import implements

from sqlobject import BoolCol, ForeignKey, StringCol

from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.sqlbase import SQLBase

from canonical.launchpad.interfaces import (
    IOAuthAccessToken, IOAuthConsumer, IOAuthConsumerSet, IOAuthNonce,
    IOAuthRequestToken, OAuthPermission)


class OAuthConsumer(SQLBase):
    """See `IOAuthConsumer`."""
    implements(IOAuthConsumer)

    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    disabled = BoolCol(notNull=True, default=False)
    key = StringCol(notNull=True)
    secret = StringCol(notNull=False, default='')


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

    consumer = ForeignKey(dbName='consumer', notNull=True)
    person = ForeignKey(dbName='person', notNull=False, default=None)
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


class OAuthNonce(SQLBase):
    """See `IOAuthNonce`."""
    implements(IOAuthNonce)

    consumer = ForeignKey(dbName='consumer', notNull=True)
    request_timestamp = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    nonce = StringCol(notNull=True)

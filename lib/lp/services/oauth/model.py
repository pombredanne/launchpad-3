# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'OAuthAccessToken',
    'OAuthConsumer',
    'OAuthConsumerSet',
    'OAuthRequestToken',
    'OAuthRequestTokenSet',
    'OAuthValidationError',
    ]

from datetime import (
    datetime,
    timedelta,
    )
import re

import pytz
from sqlobject import (
    BoolCol,
    ForeignKey,
    StringCol,
    )
from zope.interface import implements

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.services.database.constants import UTC_NOW
from lp.services.database.datetimecol import UtcDateTimeCol
from lp.services.database.enumcol import EnumCol
from lp.services.database.interfaces import IMasterStore
from lp.services.database.sqlbase import SQLBase
from lp.services.librarian.model import LibraryFileAlias
from lp.services.oauth.interfaces import (
    IOAuthAccessToken,
    IOAuthConsumer,
    IOAuthConsumerSet,
    IOAuthRequestToken,
    IOAuthRequestTokenSet,
    )
from lp.services.tokens import (
    create_token,
    create_unique_token_for_table,
    )
from lp.services.webapp.interfaces import (
    AccessLevel,
    OAuthPermission,
    )

# How many hours should a request token be valid for?
REQUEST_TOKEN_VALIDITY = 2


class OAuthValidationError(Exception):
    """Raised when the OAuth token cannot be validated."""


class OAuthBase:
    """Base class for all OAuth database classes."""

    @staticmethod
    def _get_store():
        """See `SQLBase`.

        We want all OAuth classes to be retrieved from the master flavour.  If
        they are retrieved from the slave, there will be problems in the
        authorization exchange, since it will be done across applications that
        won't share the session cookies.
        """
        return IMasterStore(LibraryFileAlias)

    getStore = _get_store


class OAuthConsumer(OAuthBase, SQLBase):
    """See `IOAuthConsumer`."""
    implements(IOAuthConsumer)

    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    disabled = BoolCol(notNull=True, default=False)
    key = StringCol(notNull=True)
    _secret = StringCol(dbName="secret", notNull=False, default='')

    # This regular expression singles out a consumer key that
    # represents any and all apps running on a specific computer. The
    # regular expression identifies the system type (eg. the OS) and
    # the name of the computer (eg. the hostname).
    #
    # A client can send whatever string they want, as long as it
    # matches the regular expression, but here are some values we've
    # seen from the lazr.restfulclient code for generating this
    # string.
    #
    # System-wide: Ubuntu (hostname)
    #  - An Ubuntu computer called "hostname"
    # System-wide: debian (hostname)
    #  - A Debian computer called "hostname"
    #    (A Nokia N900 phone also sends this string.)
    # System-wide: Windows (hostname)
    #  - A Windows computer called "hostname"
    # System-wide: Microsoft (hostname)
    #  - A Windows computer called "hostname", running an old version
    #    of Python
    # System-wide: Darwin (hostname)
    #  - A Mac OS X computer called "hostname"
    #    (Presumably an iPhone will also send this string,
    #     but we're not sure.)
    integrated_desktop_re = re.compile("^System-wide: (.*) \(([^)]*)\)$")

    def _integrated_desktop_match_group(self, position):
        """Return information about a desktop integration token.

        A convenience method that runs the desktop integration regular
        expression against the consumer key.

        :param position: The match group to return if the regular
        expression matches.

        :return: The value of one of the match groups, or None.
        """
        match = self.integrated_desktop_re.match(self.key)
        if match is None:
            return None
        return match.groups()[position]

    @property
    def is_integrated_desktop(self):
        """See `IOAuthConsumer`."""
        return self.integrated_desktop_re.match(self.key) is not None

    @property
    def integrated_desktop_type(self):
        """See `IOAuthConsumer`."""
        return self._integrated_desktop_match_group(0)

    @property
    def integrated_desktop_name(self):
        """See `IOAuthConsumer`."""
        return self._integrated_desktop_match_group(1)

    def isSecretValid(self, secret):
        """See `IOAuthConsumer`."""
        return secret == self._secret

    def newRequestToken(self):
        """See `IOAuthConsumer`."""
        key, secret = create_token_key_and_secret(table=OAuthRequestToken)
        return (
            OAuthRequestToken(consumer=self, key=key, _secret=secret), secret)

    def getAccessToken(self, key):
        """See `IOAuthConsumer`."""
        return OAuthAccessToken.selectOneBy(key=key, consumer=self)

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
        return OAuthConsumer(key=key, _secret=secret)

    def getByKey(self, key):
        """See `IOAuthConsumerSet`."""
        return OAuthConsumer.selectOneBy(key=key)


class OAuthAccessToken(OAuthBase, SQLBase):
    """See `IOAuthAccessToken`."""
    implements(IOAuthAccessToken)

    consumer = ForeignKey(
        dbName='consumer', foreignKey='OAuthConsumer', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=False, default=None)
    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    date_expires = UtcDateTimeCol(notNull=False, default=None)
    key = StringCol(notNull=True)
    _secret = StringCol(dbName="secret", notNull=False, default='')

    permission = EnumCol(enum=AccessLevel, notNull=True)

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    project = ForeignKey(
        dbName='project', foreignKey='ProjectGroup', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution',
        notNull=False, default=None)

    @property
    def context(self):
        """See `IOAuthToken`."""
        if self.product:
            return self.product
        elif self.project:
            return self.project
        elif self.distribution:
            if self.sourcepackagename:
                return self.distribution.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distribution
        else:
            return None

    @property
    def is_expired(self):
        now = datetime.now(pytz.timezone('UTC'))
        return self.date_expires is not None and self.date_expires <= now

    def isSecretValid(self, secret):
        """See `IOAuthConsumer`."""
        return secret == self._secret


class OAuthRequestToken(OAuthBase, SQLBase):
    """See `IOAuthRequestToken`."""
    implements(IOAuthRequestToken)

    consumer = ForeignKey(
        dbName='consumer', foreignKey='OAuthConsumer', notNull=True)
    person = ForeignKey(
        dbName='person', foreignKey='Person', notNull=False, default=None)
    date_created = UtcDateTimeCol(default=UTC_NOW, notNull=True)
    date_expires = UtcDateTimeCol(notNull=False, default=None)
    key = StringCol(notNull=True)
    _secret = StringCol(dbName="secret", notNull=False, default='')

    permission = EnumCol(enum=OAuthPermission, notNull=False, default=None)
    date_reviewed = UtcDateTimeCol(default=None, notNull=False)

    product = ForeignKey(
        dbName='product', foreignKey='Product', notNull=False, default=None)
    project = ForeignKey(
        dbName='project', foreignKey='ProjectGroup', notNull=False,
        default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution',
        notNull=False, default=None)

    @property
    def context(self):
        """See `IOAuthToken`."""
        if self.product:
            return self.product
        elif self.project:
            return self.project
        elif self.distribution:
            if self.sourcepackagename:
                return self.distribution.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distribution
        else:
            return None

    @property
    def is_expired(self):
        now = datetime.now(pytz.timezone('UTC'))
        expires = self.date_created + timedelta(hours=REQUEST_TOKEN_VALIDITY)
        return expires <= now

    def isSecretValid(self, secret):
        """See `IOAuthConsumer`."""
        return secret == self._secret

    def review(self, user, permission, context=None, date_expires=None):
        """See `IOAuthRequestToken`."""
        if self.is_reviewed:
            raise OAuthValidationError(
                "Request tokens can be reviewed only once.")
        if self.is_expired:
            raise OAuthValidationError(
                'This request token has expired and can no longer be '
                'reviewed.')
        self.date_reviewed = datetime.now(pytz.timezone('UTC'))
        self.date_expires = date_expires
        self.person = user
        self.permission = permission
        if IProduct.providedBy(context):
            self.product = context
        elif IProjectGroup.providedBy(context):
            self.project = context
        elif IDistribution.providedBy(context):
            self.distribution = context
        elif IDistributionSourcePackage.providedBy(context):
            self.sourcepackagename = context.sourcepackagename
            self.distribution = context.distribution
        else:
            assert context is None, ("Unknown context type: %r." % context)

    def createAccessToken(self):
        """See `IOAuthRequestToken`."""
        if not self.is_reviewed:
            raise OAuthValidationError(
                'Cannot create an access token from an unreviewed request '
                'token.')
        if self.permission == OAuthPermission.UNAUTHORIZED:
            raise OAuthValidationError(
                'The user did not grant access to this consumer.')
        if self.is_expired:
            raise OAuthValidationError(
                'This request token has expired and can no longer be '
                'exchanged for an access token.')

        key, secret = create_token_key_and_secret(table=OAuthAccessToken)
        access_level = AccessLevel.items[self.permission.name]
        access_token = OAuthAccessToken(
            consumer=self.consumer, person=self.person, key=key,
            _secret=secret, permission=access_level,
            date_expires=self.date_expires, product=self.product,
            project=self.project, distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)

        # We want to notify the user that this oauth token has been generated
        # for them for security reasons.
        self.person.security_field_changed(
            "OAuth token generated in Launchpad",
            "A new OAuth token consumer was enabled in Launchpad.")

        self.destroySelf()
        return access_token, secret

    @property
    def is_reviewed(self):
        """See `IOAuthRequestToken`."""
        return self.date_reviewed is not None


class OAuthRequestTokenSet:
    """See `IOAuthRequestTokenSet`."""
    implements(IOAuthRequestTokenSet)

    def getByKey(self, key):
        """See `IOAuthRequestTokenSet`."""
        return OAuthRequestToken.selectOneBy(key=key)


def create_token_key_and_secret(table):
    """Create a key and secret for an OAuth token.

    :table: The table in which the key/secret are going to be used. Must be
        one of OAuthAccessToken or OAuthRequestToken.

    The key will have a length of 20 and we'll make sure it's not yet in the
    given table.  The secret will have a length of 80.
    """
    key_length = 20
    key = create_unique_token_for_table(key_length, getattr(table, "key"))
    secret_length = 80
    secret = create_token(secret_length)
    return key, secret

# Copyright 2009-2016 Canonical Ltd.  This software is licensed under the
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
import hashlib
import re
from storm.locals import (
    Bool,
    DateTime,
    Int,
    Reference,
    Unicode,
    )

import pytz
from zope.interface import implementer

from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.services.database.constants import UTC_NOW
from lp.services.database.enumcol import DBEnum
from lp.services.database.interfaces import IMasterStore
from lp.services.database.stormbase import StormBase
from lp.services.oauth.interfaces import (
    IOAuthAccessToken,
    IOAuthConsumer,
    IOAuthConsumerSet,
    IOAuthRequestToken,
    IOAuthRequestTokenSet,
    )
from lp.services.tokens import create_token
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

    @classmethod
    def _getStore(cls):
        """Return the correct store for this class.

        We want all OAuth classes to be retrieved from the master flavour.  If
        they are retrieved from the slave, there will be problems in the
        authorization exchange, since it will be done across applications that
        won't share the session cookies.
        """
        return IMasterStore(cls)


def sha256_digest(data):
    """Return the SHA-256 hash of some data.

    The returned string is always Unicode, to satisfy Storm.  In Python 3,
    this is straightforward because hexdigest() returns that anyway, but in
    Python 2 we must decode.
    """
    digest = hashlib.sha256(data).hexdigest()
    if isinstance(digest, bytes):
        digest = digest.decode('ASCII')
    return digest


@implementer(IOAuthConsumer)
class OAuthConsumer(OAuthBase, StormBase):
    """See `IOAuthConsumer`."""

    __storm_table__ = 'OAuthConsumer'

    id = Int(primary=True)
    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    disabled = Bool(allow_none=False, default=False)
    key = Unicode(allow_none=False)
    _secret = Unicode(name='secret', allow_none=True, default=u'')

    def __init__(self, key, secret):
        super(OAuthConsumer, self).__init__()
        self.key = key
        self._secret = sha256_digest(secret)

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
        return sha256_digest(secret) == self._secret

    def newRequestToken(self):
        """See `IOAuthConsumer`."""
        key, secret = create_token_key_and_secret(table=OAuthRequestToken)
        token = OAuthRequestToken(consumer=self, key=key, secret=secret)
        OAuthRequestToken._getStore().add(token)
        return token, secret

    def getAccessToken(self, key):
        """See `IOAuthConsumer`."""
        return OAuthAccessToken._getStore().find(
            OAuthAccessToken,
            OAuthAccessToken.key == key,
            OAuthAccessToken.consumer == self).one()

    def getRequestToken(self, key):
        """See `IOAuthConsumer`."""
        return OAuthRequestToken._getStore().find(
            OAuthRequestToken,
            OAuthRequestToken.key == key,
            OAuthRequestToken.consumer == self).one()


@implementer(IOAuthConsumerSet)
class OAuthConsumerSet:
    """See `IOAuthConsumerSet`."""

    def new(self, key, secret=u''):
        """See `IOAuthConsumerSet`."""
        assert self.getByKey(key) is None, (
            "The key '%s' is already in use by another consumer." % key)
        consumer = OAuthConsumer(key=key, secret=secret)
        OAuthConsumer._getStore().add(consumer)
        return consumer

    def getByKey(self, key):
        """See `IOAuthConsumerSet`."""
        return OAuthConsumer._getStore().find(
            OAuthConsumer, OAuthConsumer.key == key).one()


@implementer(IOAuthAccessToken)
class OAuthAccessToken(OAuthBase, StormBase):
    """See `IOAuthAccessToken`."""

    __storm_table__ = 'OAuthAccessToken'

    id = Int(primary=True)
    consumer_id = Int(name='consumer', allow_none=False)
    consumer = Reference(consumer_id, 'OAuthConsumer.id')
    person_id = Int(name='person', allow_none=False)
    person = Reference(person_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    date_expires = DateTime(tzinfo=pytz.UTC, allow_none=True, default=None)
    key = Unicode(allow_none=False)
    _secret = Unicode(name='secret', allow_none=True, default=u'')

    permission = DBEnum(enum=AccessLevel, allow_none=False)

    product_id = Int(name='product', allow_none=True, default=None)
    product = Reference(product_id, 'Product.id')
    projectgroup_id = Int(name='project', allow_none=True, default=None)
    projectgroup = Reference(projectgroup_id, 'ProjectGroup.id')
    sourcepackagename_id = Int(
        name='sourcepackagename', allow_none=True, default=None)
    sourcepackagename = Reference(sourcepackagename_id, 'SourcePackageName.id')
    distribution_id = Int(name='distribution', allow_none=True, default=None)
    distribution = Reference(distribution_id, 'Distribution.id')

    def __init__(self, consumer, permission, key, secret=u'', person=None,
                 date_expires=None, product=None, projectgroup=None,
                 distribution=None, sourcepackagename=None):
        super(OAuthAccessToken, self).__init__()
        self.consumer = consumer
        self.permission = permission
        self.key = key
        self._secret = sha256_digest(secret)
        self.person = person
        self.date_expires = date_expires
        self.product = product
        self.projectgroup = projectgroup
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename

    @property
    def context(self):
        """See `IOAuthToken`."""
        if self.product:
            return self.product
        elif self.projectgroup:
            return self.projectgroup
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
        now = datetime.now(pytz.UTC)
        return self.date_expires is not None and self.date_expires <= now

    def isSecretValid(self, secret):
        """See `IOAuthToken`."""
        return sha256_digest(secret) == self._secret


@implementer(IOAuthRequestToken)
class OAuthRequestToken(OAuthBase, StormBase):
    """See `IOAuthRequestToken`."""

    __storm_table__ = 'OAuthRequestToken'

    id = Int(primary=True)
    consumer_id = Int(name='consumer', allow_none=False)
    consumer = Reference(consumer_id, 'OAuthConsumer.id')
    person_id = Int(name='person', allow_none=True, default=None)
    person = Reference(person_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC, allow_none=False, default=UTC_NOW)
    date_expires = DateTime(tzinfo=pytz.UTC, allow_none=True, default=None)
    key = Unicode(allow_none=False)
    _secret = Unicode(name='secret', allow_none=True, default=u'')

    permission = DBEnum(enum=OAuthPermission, allow_none=True, default=None)
    date_reviewed = DateTime(tzinfo=pytz.UTC, allow_none=True, default=None)

    product_id = Int(name='product', allow_none=True, default=None)
    product = Reference(product_id, 'Product.id')
    projectgroup_id = Int(name='project', allow_none=True, default=None)
    projectgroup = Reference(projectgroup_id, 'ProjectGroup.id')
    sourcepackagename_id = Int(
        name='sourcepackagename', allow_none=True, default=None)
    sourcepackagename = Reference(sourcepackagename_id, 'SourcePackageName.id')
    distribution_id = Int(name='distribution', allow_none=True, default=None)
    distribution = Reference(distribution_id, 'Distribution.id')

    def __init__(self, consumer, key, secret=u'', permission=None, person=None,
                 date_expires=None, product=None, projectgroup=None,
                 distribution=None, sourcepackagename=None):
        super(OAuthRequestToken, self).__init__()
        self.consumer = consumer
        self.permission = permission
        self.key = key
        self._secret = sha256_digest(secret)
        self.person = person
        self.date_expires = date_expires
        self.product = product
        self.projectgroup = projectgroup
        self.distribution = distribution
        self.sourcepackagename = sourcepackagename

    @property
    def context(self):
        """See `IOAuthToken`."""
        if self.product:
            return self.product
        elif self.projectgroup:
            return self.projectgroup
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
        now = datetime.now(pytz.UTC)
        expires = self.date_created + timedelta(hours=REQUEST_TOKEN_VALIDITY)
        return expires <= now

    def isSecretValid(self, secret):
        """See `IOAuthToken`."""
        return sha256_digest(secret) == self._secret

    def review(self, user, permission, context=None, date_expires=None):
        """See `IOAuthRequestToken`."""
        if self.is_reviewed:
            raise OAuthValidationError(
                "Request tokens can be reviewed only once.")
        if self.is_expired:
            raise OAuthValidationError(
                'This request token has expired and can no longer be '
                'reviewed.')
        self.date_reviewed = datetime.now(pytz.UTC)
        self.date_expires = date_expires
        self.person = user
        self.permission = permission
        if IProduct.providedBy(context):
            self.product = context
        elif IProjectGroup.providedBy(context):
            self.projectgroup = context
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
            secret=secret, permission=access_level,
            date_expires=self.date_expires, product=self.product,
            projectgroup=self.projectgroup, distribution=self.distribution,
            sourcepackagename=self.sourcepackagename)
        OAuthAccessToken._getStore().add(access_token)

        # We want to notify the user that this oauth token has been generated
        # for them for security reasons.
        self.person.security_field_changed(
            "OAuth token generated in Launchpad",
            "A new OAuth token consumer was enabled in Launchpad.")

        self._getStore().remove(self)
        return access_token, secret

    @property
    def is_reviewed(self):
        """See `IOAuthRequestToken`."""
        return self.date_reviewed is not None


@implementer(IOAuthRequestTokenSet)
class OAuthRequestTokenSet:
    """See `IOAuthRequestTokenSet`."""

    def getByKey(self, key):
        """See `IOAuthRequestTokenSet`."""
        return OAuthRequestToken._getStore().find(
            OAuthRequestToken, OAuthRequestToken.key == key).one()


def create_token_key_and_secret(table):
    """Create a key and secret for an OAuth token.

    :table: The table in which the key/secret are going to be used. Must be
        one of OAuthAccessToken or OAuthRequestToken.

    The key will have a length of 20. The secret will have a length of 80.
    """
    # Even a length of 20 has 112 bits of entropy, so uniqueness is a
    # good assumption. If we generate a duplicate then the DB insertion
    # will crash, which is desirable because it indicates an RNG issue.
    key_length = 20
    key = create_token(key_length)
    secret_length = 80
    secret = create_token(secret_length)
    return key, secret

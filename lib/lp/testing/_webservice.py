# Copyright 2010-2018 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'launchpadlib_credentials_for',
    'launchpadlib_for',
    'oauth_access_token_for',
    ]


import shutil
import tempfile

from launchpadlib.credentials import (
    AccessToken,
    AnonymousAccessToken,
    Credentials,
    )
from launchpadlib.launchpad import Launchpad
import six
import transaction
from zope.component import getUtility
import zope.testing.cleanup

from lp.registry.interfaces.person import IPersonSet
from lp.services.oauth.interfaces import IOAuthConsumerSet
from lp.services.webapp.interaction import ANONYMOUS
from lp.services.webapp.interfaces import OAuthPermission
from lp.services.webapp.publisher import canonical_url
from lp.testing._login import (
    login,
    logout,
    )


def api_url(obj):
    """Find the web service URL of a data model object.

    This makes it easy to load up the factory object you just created
    in launchpadlib.

    :param: Which web service version to use.

    :return: A relative URL suitable for passing into Launchpad.load().
    """
    return canonical_url(obj, force_local_path=True)


def oauth_access_token_for(consumer_name, person, permission, context=None):
    """Find or create an OAuth access token for the given person.
    :param consumer_name: An OAuth consumer name.
    :param person: A person (or the name of a person) for whom to create
        or find credentials.
    :param permission: An OAuthPermission (or its token) designating
        the level of permission the credentials should have.
    :param context: The OAuth context for the credentials (or a string
        designating same).

    :return: A tuple of an OAuthAccessToken object and its secret.
    """
    if isinstance(person, basestring):
        # Look up a person by name.
        person = getUtility(IPersonSet).getByName(person)
    if isinstance(context, basestring):
        # Turn an OAuth context string into the corresponding object.
        # Avoid an import loop by importing from launchpad.browser here.
        from lp.services.oauth.browser import lookup_oauth_context
        context = lookup_oauth_context(context)
    if isinstance(permission, basestring):
        # Look up a permission by its token string.
        permission = OAuthPermission.items[permission]

    # Find or create the consumer object.
    consumer_set = getUtility(IOAuthConsumerSet)
    consumer = consumer_set.getByKey(consumer_name)
    if consumer is None:
        consumer = consumer_set.new(consumer_name)

    request_token, _ = consumer.newRequestToken()
    request_token.review(person, permission, context)
    access_token, access_secret = request_token.createAccessToken()
    return access_token, access_secret


def launchpadlib_credentials_for(
    consumer_name, person, permission=OAuthPermission.WRITE_PRIVATE,
    context=None):
    """Create launchpadlib credentials for the given person.

    :param consumer_name: An OAuth consumer name.
    :param person: A person (or the name of a person) for whom to create
        or find credentials.
    :param permission: An OAuthPermission (or its token) designating
        the level of permission the credentials should have.
    :param context: The OAuth context for the credentials.
    :return: A launchpadlib Credentials object.
    """
    # Start an interaction so that oauth_access_token_for will
    # succeed.  oauth_access_token_for may be called in any layer, but
    # launchpadlib_credentials_for is only called in the
    # PageTestLayer, when a Launchpad instance is running for
    # launchpadlib to use.
    login(ANONYMOUS)
    access_token, access_secret = oauth_access_token_for(
        consumer_name, person, permission, context)
    logout()
    launchpadlib_token = AccessToken(access_token.key, access_secret)
    return Credentials(consumer_name=consumer_name,
                       access_token=launchpadlib_token)


def _clean_up_cache(cache):
    """Clean up a temporary launchpadlib cache directory."""
    shutil.rmtree(cache, ignore_errors=True)


def launchpadlib_for(
    consumer_name, person=None, permission=OAuthPermission.WRITE_PRIVATE,
    context=None, version="devel", service_root="http://api.launchpad.dev/"):
    """Create a Launchpad object for the given person.

    :param consumer_name: An OAuth consumer name.
    :param person: A person (or the name of a person) for whom to create
        or find credentials.
    :param permission: An OAuthPermission (or its token) designating
        the level of permission the credentials should have.
    :param context: The OAuth context for the credentials.
    :param version: The version of the web service to access.
    :param service_root: The root URL of the web service to access.

    :return: A launchpadlib Launchpad object.
    """
    # XXX cjwatson 2016-01-22: Callers should be updated to pass Unicode
    # directly, but that's a big change.
    consumer_name = six.ensure_text(consumer_name)
    if person is None:
        token = AnonymousAccessToken()
        credentials = Credentials(consumer_name, access_token=token)
    else:
        credentials = launchpadlib_credentials_for(
            consumer_name, person, permission, context)
    transaction.commit()
    cache = tempfile.mkdtemp(prefix='launchpadlib-cache-')
    zope.testing.cleanup.addCleanUp(_clean_up_cache, (cache,))
    return Launchpad(credentials, None, None, service_root=service_root,
                     version=version, cache=cache)

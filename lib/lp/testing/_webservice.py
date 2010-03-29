# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# We like global statements!
# pylint: disable-msg=W0602,W0603
__metaclass__ = type

__all__ = [
    'oauth_access_token_for'
    ]

from zope.component import getUtility
from launchpadlib.credentials import AccessToken, Credentials
from launchpadlib.launchpad import Launchpad

from canonical.launchpad.webapp.interfaces import OAuthPermission
from canonical.launchpad.interfaces import (
    IOAuthConsumerSet, IPersonSet)
from lp.testing._login import ANONYMOUS, login, logout

def oauth_access_token_for(consumer_name, person, permission, context=None):
    """Find or create an OAuth access token for the given person.

    :return: An OAuthAccessToken object.
    """
    # Allow the permission to be specified by its token string.
    if isinstance(permission, basestring):
        permission = OAuthPermission.items[permission]

    # Find or create the consumer object.
    consumer_set = getUtility(IOAuthConsumerSet)
    consumer = consumer_set.getByKey(consumer_name)
    if consumer is None:
        consumer = consumer_set.new(consumer_name)
    else:
        # We didn't have to create the consumer. Maybe this user
        # already has an access token for this
        # consumer+person+permission?
        existing_token = [token for token in person.oauth_access_tokens
                          if (token.consumer == consumer
                              and token.permission == permission
                              and token.context == context)]
        if len(existing_token) >= 1:
            return existing_token[0]

    # There is no existing access token for this
    # consumer+person+permission+context. Create one and review it.
    request_token = consumer.newRequestToken()
    request_token.review(person, permission, context)
    access_token = request_token.createAccessToken()
    return access_token


def launchpadlib_credentials_for(
    consumer_name, person, permission=OAuthPermission.WRITE_PRIVATE,
    context=None):
    """Create launchpadlib credentials for the given person.

    :return: A launchpadlib Credentials object.
    """
    login(ANONYMOUS)
    if isinstance(person, basestring):
        # Look up a person by their username.
        person = getUtility(IPersonSet).getByName(person)
    access_token = oauth_access_token_for(
        consumer_name, person, permission, context)
    logout()
    launchpadlib_token = AccessToken(
        access_token.key, access_token.secret)
    return Credentials(consumer_name=consumer_name,
                       access_token=launchpadlib_token)


def launchpadlib_for(
    consumer_name, person, permission=OAuthPermission.WRITE_PRIVATE,
    context=None, version=None, service_root="http://api.launchpad.dev/"):
    """Create a Launchpad object for the given person.

    :return: A launchpadlib Launchpad object.
    """
    credentials = launchpadlib_credentials_for(
        consumer_name, person, permission, context)
    version = version or Launchpad.DEFAULT_VERSION
    return Launchpad(credentials, service_root, version=version)

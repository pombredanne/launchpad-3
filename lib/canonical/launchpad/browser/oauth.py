# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthAccessTokenView',
    'OAuthRequestTokenView']

from zope.component import getUtility

from canonical.launchpad.interfaces import IOAuthConsumerSet, OAuthPermission
from canonical.launchpad.webapp import LaunchpadView


# The challenge included in responses with a 401 status.
CHALLENGE = 'OAuth realm="https://api.launchpad.net"'


class OAuthRequestTokenView(LaunchpadView):
    """Where consumers can ask for a request token."""

    def __call__(self):
        """Create a request token and include its key/secret in the response.

        First checks that the consumer is registered and, if not, respond
        with a 401.
        """
        form = self.request.form
        consumer = getUtility(IOAuthConsumerSet).getByKey(
            form.get('oauth_consumer_key'))

        if consumer is None:
            self.request.unauthorized(CHALLENGE)
            return u''
        # XXX: 2008-02-27, salgado: We should verify the signature here, but
        # for now it doesn't make much sense since in the beginning all our
        # consumer secrets will be empty.
        assert consumer.secret == '', (
            'We should not have any consumers with non-empty keys.')
        token = consumer.newRequestToken()
        body = u'oauth_token=%s&oauth_token_secret=%s' % (
            token.key, token.secret)
        return body


class OAuthAccessTokenView(LaunchpadView):
    """Where consumers exchange a request token for an access token."""

    def __call__(self):
        """Create an access token and include its key/secret in the response.

        If the consumer is not registered, the given token key doesn't exist
        (or is not associated with the consumer), the signature does not match
        or no permission has been granted by the user, respond with a 401.
        """
        form = self.request.form
        consumer = getUtility(IOAuthConsumerSet).getByKey(
            form.get('oauth_consumer_key'))

        if consumer is None:
            self.request.unauthorized(CHALLENGE)
            return u''

        token = consumer.getRequestToken(form.get('oauth_token'))
        if token is None:
            self.request.unauthorized(CHALLENGE)
            return u''

        consumer_secret, token_secret = form.get('oauth_signature').split('&')
        if consumer_secret != consumer.secret or token_secret != token.secret:
            self.request.unauthorized(CHALLENGE)
            return u''

        if (not token.is_reviewed
            or token.permission == OAuthPermission.UNAUTHORIZED):
            self.request.unauthorized(CHALLENGE)
            return u''

        access_token = token.createAccessToken()
        body = u'oauth_token=%s&oauth_token_secret=%s' % (
            access_token.key, access_token.secret)
        return body

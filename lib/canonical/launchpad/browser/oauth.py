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

        If the consumer key is empty or the signature doesn't match, respond
        with a 401 status.  If the key is not empty but there's no consumer
        with it, we register a new consumer.
        """
        form = self.request.form
        consumer_key = form.get('oauth_consumer_key')
        if not consumer_key:
            self.request.unauthorized(CHALLENGE)
            return u''

        consumer_set = getUtility(IOAuthConsumerSet)
        consumer = consumer_set.getByKey(consumer_key)
        if consumer is None:
            consumer = consumer_set.new(key=consumer_key)

        if form.get('oauth_signature_method') != 'PLAINTEXT':
            # XXX: 2008-03-04, salgado: Only the PLAINTEXT method is supported
            # now. Others will be implemented later.
            self.request.response.setStatus(400)
            return u''

        expected_signature = "&%s" % consumer.secret
        if expected_signature != form.get('oauth_signature'):
            self.request.unauthorized(CHALLENGE)
            return u''

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

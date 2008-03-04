# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthRequestTokenView']

from zope.component import getUtility

from canonical.launchpad.interfaces import IOAuthConsumerSet
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

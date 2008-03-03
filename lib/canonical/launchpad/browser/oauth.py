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

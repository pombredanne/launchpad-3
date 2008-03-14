# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthAccessTokenView',
    'OAuthAuthorizeTokenView',
    'OAuthRequestTokenView',
    'OAuthTokenAuthorizedView']

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IOAuthConsumerSet, IOAuthRequestToken, IOAuthRequestTokenSet,
    OAuthPermission, OAUTH_CHALLENGE)
from canonical.launchpad.webapp import (
    action, LaunchpadFormView, LaunchpadView)
from canonical.launchpad.webapp.authentication import check_oauth_signature


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
            self.request.unauthorized(OAUTH_CHALLENGE)
            return u''

        consumer_set = getUtility(IOAuthConsumerSet)
        consumer = consumer_set.getByKey(consumer_key)
        if consumer is None:
            consumer = consumer_set.new(key=consumer_key)

        if not check_oauth_signature(self.request, consumer, None):
            return u''

        token = consumer.newRequestToken()
        body = u'oauth_token=%s&oauth_token_secret=%s' % (
            token.key, token.secret)
        return body


class OAuthAuthorizeTokenView(LaunchpadFormView):
    """Where users authorize consumers to access Launchpad on their behalf."""

    label = "Authorize programs to access Launchpad on your behalf"
    schema = IOAuthRequestToken
    field_names = ['permission']

    def initialize(self):
        key = self.request.form.get('oauth_token')
        if not key:
            self.request.response.setStatus(400)
            self.render = lambda : u'Missing oauth_token parameter'
            return
        self.token = getUtility(IOAuthRequestTokenSet).getByKey(key)
        if self.token is None or self.token.is_reviewed:
            self.request.unauthorized(OAUTH_CHALLENGE)
            self.render = lambda : (
                u'Token does not exist or has been reviewed already')
        else:
            super(OAuthAuthorizeTokenView, self).initialize()

    @action(_("Continue"), name="continue")
    def continue_action(self, action, data):
        self.token.review(self.user, data['permission'])
        callback = self.request.form.get('oauth_callback')
        if callback:
            self.next_url = callback
        else:
            self.next_url = (
                '+token-authorized?oauth_token=%s' % self.token.key)


class OAuthTokenAuthorizedView(LaunchpadView):
    """Where users who reviewed tokens may get redirected to.

    If the consumer didn't include an oauth_callback when sending the user to
    Launchpad, this is the page the user is redirected to after he logs in and
    reviews the token.
    """

    def initialize(self):
        key = self.request.form.get('oauth_token')
        self.token = getUtility(IOAuthRequestTokenSet).getByKey(key)
        assert self.token.is_reviewed, (
            'Users should be directed to this page only if they already '
            'authorized the token.')


class OAuthAccessTokenView(LaunchpadView):
    """Where consumers may exchange a request token for an access token."""

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
            self.request.unauthorized(OAUTH_CHALLENGE)
            return u''

        token = consumer.getRequestToken(form.get('oauth_token'))
        if token is None:
            self.request.unauthorized(OAUTH_CHALLENGE)
            return u''

        if not check_oauth_signature(self.request, consumer, token):
            return u''

        if (not token.is_reviewed
            or token.permission == OAuthPermission.UNAUTHORIZED):
            self.request.unauthorized(OAUTH_CHALLENGE)
            return u''

        access_token = token.createAccessToken()
        body = u'oauth_token=%s&oauth_token_secret=%s' % (
            access_token.key, access_token.secret)
        return body

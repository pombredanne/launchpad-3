# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'OAuthAccessTokenView',
    'OAuthAuthorizeTokenView',
    'OAuthRequestTokenView',
    'OAuthTokenAuthorizedView']

from zope.component import getUtility
from zope.formlib.form import Action, Actions

from canonical.launchpad.interfaces.distribution import IDistributionSet
from canonical.launchpad.interfaces.oauth import (
    IOAuthConsumerSet, IOAuthRequestToken, IOAuthRequestTokenSet,
    OAUTH_CHALLENGE)
from canonical.launchpad.interfaces.product import IProductSet
from canonical.launchpad.interfaces.project import IProjectSet
from canonical.launchpad.webapp import LaunchpadFormView, LaunchpadView
from canonical.launchpad.webapp.authentication import (
    check_oauth_signature, get_oauth_authorization)
from canonical.launchpad.webapp.interfaces import (
    OAuthPermission, UnexpectedFormData)


class OAuthRequestTokenView(LaunchpadView):
    """Where consumers can ask for a request token."""

    def __call__(self):
        """Create a request token and include its key/secret in the response.

        If the consumer key is empty or the signature doesn't match, respond
        with a 401 status.  If the key is not empty but there's no consumer
        with it, we register a new consumer.
        """
        form = get_oauth_authorization(self.request)
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


def token_exists_and_is_not_reviewed(form, action):
    return form.token is not None and not form.token.is_reviewed


def create_oauth_permission_actions():
    """Return a list of `Action`s for each possible `OAuthPermission`."""
    actions = Actions()
    def success(form, action, data):
        form.reviewToken(action.permission)
    for permission in OAuthPermission.items:
        action = Action(
            permission.title, name=permission.name, success=success,
            condition=token_exists_and_is_not_reviewed)
        action.permission = permission
        actions.append(action)
    return actions


class OAuthAuthorizeTokenView(LaunchpadFormView):
    """Where users authorize consumers to access Launchpad on their behalf."""

    actions = create_oauth_permission_actions()
    label = "Authorize application to access Launchpad on your behalf"
    schema = IOAuthRequestToken
    field_names = []
    token = None

    def initialize(self):
        form = self.request.form
        self.storeTokenContext(form)
        # XXX: Just like in other OAuth requests, the parameters here may be
        # in the Authorization header, so we must use
        # get_oauth_authorization() here instead of getting the token from the
        # request's form.  I'm not sure it'd make sense to have the context in
        # the Authorization header, though.
        key = form.get('oauth_token')
        if key:
            self.token = getUtility(IOAuthRequestTokenSet).getByKey(key)
        super(OAuthAuthorizeTokenView, self).initialize()

    def storeTokenContext(self, form):
        """Store the context given by the consumer in this view.

        Also store a dict with the key/value of the context to be passed to
        OAuthRequestToken.review().
        """
        product = form.get('lp.product')
        project = form.get('lp.project')
        distro = form.get('lp.distribution')
        package = form.get('lp.sourcepackagename')
        if product:
            if project or distro or package:
                raise UnexpectedFormData("More than one context specified.")
            self.token_context = getUtility(IProductSet)[product]
            self.token_context_params = dict(product=self.token_context)
        elif project:
            if product or distro or package:
                raise UnexpectedFormData("More than one context specified.")
            self.token_context = getUtility(IProjectSet)[project]
            self.token_context_params = dict(project=self.token_context)
        elif package:
            if product or project:
                raise UnexpectedFormData("More than one context specified.")
            elif not distro:
                raise UnexpectedFormData(
                    "Must specify the package's distribution.")
            else:
                distro = getUtility(IDistributionSet)[distro]
                distro_source_package = distro.getSourcePackage(package)
                self.token_context = distro_source_package
                self.token_context_params = dict(
                    distribution=distro,
                    sourcepackagename=distro_source_package.sourcepackagename)
        elif distro:
            if product or project:
                raise UnexpectedFormData("More than one context specified.")
            self.token_context = getUtility(IDistributionSet)[distro]
            self.token_context_params = dict(distribution=self.token_context)
        else:
            # No context specified.
            self.token_context = None
            self.token_context_params = {}
    def reviewToken(self, permission):
        self.token.review(self.user, permission, **self.token_context_params)
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

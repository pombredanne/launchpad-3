# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'OAuthAccessTokenView',
    'OAuthAuthorizeTokenView',
    'OAuthRequestTokenView',
    'OAuthTokenAuthorizedView',
    'lookup_oauth_context']

from lazr.restful import HTTPResource
import simplejson
from zope.component import getUtility
from zope.formlib.form import (
    Action,
    Actions,
    )
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces.oauth import (
    IOAuthConsumerSet,
    IOAuthRequestToken,
    IOAuthRequestTokenSet,
    OAUTH_CHALLENGE,
    )
from canonical.launchpad.webapp import (
    LaunchpadFormView,
    LaunchpadView,
    )
from canonical.launchpad.webapp.authentication import (
    check_oauth_signature,
    get_oauth_authorization,
    )
from canonical.launchpad.webapp.interfaces import (
    ILaunchBag,
    OAuthPermission,
    )
from lp.app.errors import UnexpectedFormData
from lp.registry.interfaces.distribution import IDistributionSet
from lp.registry.interfaces.pillar import IPillarNameSet


class JSONTokenMixin:

    def getJSONRepresentation(self, permissions, token=None,
                              include_secret=False):
        """Return a JSON representation of the authorization policy.

        This includes a description of some subset of OAuthPermission,
        and may also include a description of a request token.
        """
        structure = {}
        if token is not None:
            structure['oauth_token'] = token.key
            structure['oauth_token_consumer'] = token.consumer.key
            if include_secret:
                structure['oauth_token_secret'] = token.secret
        access_levels = [{
                'value' : permission.name,
                'title' : permission.title
                }
                for permission in permissions]
        structure['access_levels'] = access_levels
        self.request.response.setHeader('Content-Type', HTTPResource.JSON_TYPE)
        return simplejson.dumps(structure)


class OAuthRequestTokenView(LaunchpadView, JSONTokenMixin):
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
        if self.request.headers.get('Accept') == HTTPResource.JSON_TYPE:
            # Don't show the client the GRANT_PERMISSIONS access
            # level. If they have a legitimate need to use it, they'll
            # already know about it.
            permissions = [permission for permission in OAuthPermission.items
                           if permission != OAuthPermission.GRANT_PERMISSIONS]
            return self.getJSONRepresentation(
                permissions, token, include_secret=True)
        return u'oauth_token=%s&oauth_token_secret=%s' % (
            token.key, token.secret)


def token_exists_and_is_not_reviewed(form, action):
    return form.token is not None and not form.token.is_reviewed


def create_oauth_permission_actions():
    """Return a list of `Action`s for each possible `OAuthPermission`."""
    actions = Actions()
    actions_excluding_grant_permissions = Actions()

    def success(form, action, data):
        form.reviewToken(action.permission)

    for permission in OAuthPermission.items:
        action = Action(
            permission.title, name=permission.name, success=success,
            condition=token_exists_and_is_not_reviewed)
        action.permission = permission
        actions.append(action)
        if permission != OAuthPermission.GRANT_PERMISSIONS:
            actions_excluding_grant_permissions.append(action)
    return actions, actions_excluding_grant_permissions


class OAuthAuthorizeTokenView(LaunchpadFormView, JSONTokenMixin):
    """Where users authorize consumers to access Launchpad on their behalf."""

    actions, actions_excluding_grant_permissions = (
        create_oauth_permission_actions())
    label = "Authorize application to access Launchpad on your behalf"
    schema = IOAuthRequestToken
    field_names = []
    token = None

    @property
    def visible_actions(self):
        """Restrict the actions to the subset the client can make use of.

        Not all client programs can function with all levels of
        access. For instance, a client that needs to modify the
        dataset won't work correctly if the end-user only gives it
        read access. By setting the 'allow_permission' query variable
        the client program can get Launchpad to show the end-user an
        acceptable subset of OAuthPermission.

        The user always has the option to deny the client access
        altogether, so it makes sense for the client to ask for the
        least access possible.

        If the client sends nonsensical values for allow_permissions,
        the end-user will be given a choice among all the permissions
        used by normal applications.
        """

        allowed_permissions = self.request.form_ng.getAll('allow_permission')
        if len(allowed_permissions) == 0:
            return self.actions_excluding_grant_permissions
        actions = Actions()

        # UNAUTHORIZED is always one of the options. If the client
        # explicitly requested UNAUTHORIZED, remove it from the list
        # to simplify the algorithm: we'll add it back later.
        if OAuthPermission.UNAUTHORIZED.name in allowed_permissions:
            allowed_permissions.remove(OAuthPermission.UNAUTHORIZED.name)

        # GRANT_PERMISSIONS cannot be requested as one of several
        # options--it must be the only option (other than
        # UNAUTHORIZED). If GRANT_PERMISSIONS is one of several
        # options, remove it from the list.
        if (OAuthPermission.GRANT_PERMISSIONS.name in allowed_permissions
            and len(allowed_permissions) > 1):
            allowed_permissions.remove(OAuthPermission.GRANT_PERMISSIONS.name)

        for action in self.actions:
            if (action.permission.name in allowed_permissions
                or action.permission is OAuthPermission.UNAUTHORIZED):
                actions.append(action)

        if len(list(actions)) == 1:
            # The only visible action is UNAUTHORIZED. That means the
            # client tried to restrict the permissions but didn't name
            # any actual permissions (except possibly
            # UNAUTHORIZED). Rather than present the end-user with an
            # impossible situation where their only option is to deny
            # access, we'll present the full range of actions (except
            # for GRANT_PERMISSIONS).
            return self.actions_excluding_grant_permissions
        return actions

    def initialize(self):
        user = getUtility(ILaunchBag).user
        if user is None:
            # The normal Launchpad code was not able to identify any
            # user, but we're going to try a little harder before
            # concluding that no one's logged in. If the incoming
            # request is signed by an OAuth access token with the
            # GRANT_PERMISSIONS access level, we will force a
            # temporary login with the user whose access token this
            # is.
            raise Unauthorized()
        self.storeTokenContext()
        form = get_oauth_authorization(self.request)
        key = form.get('oauth_token')
        if key:
            self.token = getUtility(IOAuthRequestTokenSet).getByKey(key)
        super(OAuthAuthorizeTokenView, self).initialize()

    def render(self):
        if self.request.headers.get('Accept') == HTTPResource.JSON_TYPE:
            permissions = [action.permission
                           for action in self.visible_actions]
            return self.getJSONRepresentation(permissions, self.token)
        return super(OAuthAuthorizeTokenView, self).render()

    def storeTokenContext(self):
        """Store the context given by the consumer in this view."""
        self.token_context = None
        # We have no guarantees that lp.context will be together with the
        # OAuth parameters, so we need to check in the Authorization header
        # and on the request's form if it's not in the former.
        oauth_data = get_oauth_authorization(self.request)
        context = oauth_data.get('lp.context')
        if not context:
            context = self.request.form.get('lp.context')
            if not context:
                return
        try:
            context = lookup_oauth_context(context)
        except ValueError:
            raise UnexpectedFormData("Unknown context.")
        self.token_context = context

    def reviewToken(self, permission):
        self.token.review(self.user, permission, self.token_context)
        callback = self.request.form.get('oauth_callback')
        if callback:
            self.next_url = callback
        else:
            self.next_url = (
                '+token-authorized?oauth_token=%s' % self.token.key)

def lookup_oauth_context(context):
    """Transform an OAuth context string into a context object.

    :param context: A string to turn into a context object.
    """
    if '/' in context:
        distro, package = context.split('/')
        distro = getUtility(IDistributionSet).getByName(distro)
        if distro is None:
            raise ValueError(distro)
        context = distro.getSourcePackage(package)
        if context is None:
            raise ValueError(package)
    else:
        context = getUtility(IPillarNameSet).getByName(context)
        if context is None:
            raise ValueError(context)
    return context


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
        """Create an access token and respond with its key/secret/context.

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
            return u'No request token specified.'

        if not check_oauth_signature(self.request, consumer, token):
            return u'Invalid OAuth signature.'

        if not token.is_reviewed:
            self.request.unauthorized(OAUTH_CHALLENGE)
            return u'Request token has not yet been reviewed. Try again later.'

        if token.permission == OAuthPermission.UNAUTHORIZED:
            # The end-user explicitly refused to authorize this
            # token. We send 403 ("Forbidden") instead of 401
            # ("Unauthorized") to distinguish this case and to
            # indicate that, as RFC2616 says, "authorization will not
            # help."
            self.request.response.setStatus(403)
            return u'End-user refused to authorize request token.'

        access_token = token.createAccessToken()
        context_name = None
        if access_token.context is not None:
            context_name = access_token.context.name
        body = u'oauth_token=%s&oauth_token_secret=%s&lp.context=%s' % (
            access_token.key, access_token.secret, context_name)
        return body

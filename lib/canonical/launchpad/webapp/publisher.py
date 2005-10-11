# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Publisher of objects as web pages.

XXX: Much stuff from canonical.publication needs to move here.
"""

__metaclass__ = type
__all__ = ['UserAttributeCache', 'LaunchpadView', 'canonical_url', 'nearest',
           'get_current_browser_request', 'canonical_url_iterator',
           'rootObject', 'Navigation', 'stepthrough', 'redirection', 'stepto']

from zope.interface import implements
from zope.exceptions import NotFoundError
from zope.component import getUtility, queryView, getDefaultViewName
from zope.interface.advice import addClassAdvisor
import zope.security.management
from zope.security.checker import ProxyFactory, NamesChecker
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.publisher.interfaces import NotFound
from canonical.launchpad.layers import setFirstLayer
from canonical.launchpad.interfaces import (
    ICanonicalUrlData, NoCanonicalUrl, ILaunchpadRoot, ILaunchpadApplication,
    ILaunchBag, IOpenLaunchBag)

# Import the launchpad.conf configuration object.
from canonical.config import config


class DecoratorAdvisor:
    """Base class for a function decorator that adds class advice.

    The advice stores information in a magic attribute in the class's dict.
    The magic attribute's value is a dict, which contains names and functions
    that were set in the function decorators.
    """

    magic_class_attribute = None

    def __init__(self, name):
        self.name = name

    def __call__(self, fn):
        self.fn = fn
        addClassAdvisor(self.advise)
        return fn

    def advise(self, cls):
        assert self.magic_class_attribute is not None, (
            'You must provide the magic_class_attribute to use')
        D = cls.__dict__.get(self.magic_class_attribute)
        if D is None:
            D = {}
            setattr(cls, self.magic_class_attribute, D)
        D[self.name] = self.fn
        return cls


class stepthrough(DecoratorAdvisor):

    magic_class_attribute = '__stepthrough_traversals__'


class stepto(DecoratorAdvisor):

    magic_class_attribute = '__stepto_traversals__'


class redirection:

    def __init__(self, fromname, toname):
        self.fromname = fromname
        self.toname = toname
        addClassAdvisor(self.advise)

    def advise(self, cls):
        redirections = cls.__dict__.get('__redirections__')
        if redirections is None:
            redirections = {}
            setattr(cls, '__redirections__', redirections)
        redirections[self.fromname] = self.toname
        return cls


class UserAttributeCache:
    """Mix in to provide self.user, cached."""

    _no_user = object()
    _user = _no_user

    @property
    def user(self):
        """The logged-in Person, or None if there is no one logged in."""
        if self._user is self._no_user:
            self._user = getUtility(ILaunchBag).user
        return self._user


class LaunchpadView(UserAttributeCache):
    """Base class for views in Launchpad.

    Available attributes and methods are:

    - context
    - request
    - initialize() <-- subclass this for specific initialization
    - template     <-- the template set from zcml, otherwise not present
    - user         <-- currently logged-in user
    - render()     <-- used to render the page.  override this if you have many
                       templates not set via zcml, or you want to do rendering
                       from Python.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def initialize(self):
        """Override this in subclasses."""
        pass

    @property
    def template(self):
        """The page's template, if configured in zcml."""
        return self.index

    def render(self):
        return self.template()

    def __call__(self):
        self.initialize()
        return self.render()


class LaunchpadRootUrlData:
    """ICanonicalUrlData for the ILaunchpadRoot object."""

    implements(ICanonicalUrlData)

    path = ''
    inside = None

    def __init__(self, context):
        self.context = context

def canonical_urldata_iterator(obj):
    """Iterate over the urldata for the object and each of its canonical url
    parents.

    Raises NoCanonicalUrl if canonical url data is not available.
    """
    current_object = obj
    # The while loop is to proceed the first time around because we're
    # on the initial object, and subsequent times, because there is an object
    # inside.
    while current_object is obj or urldata.inside is not None:
        urldata = ICanonicalUrlData(current_object, None)
        if urldata is None:
            raise NoCanonicalUrl(obj, current_object)
        yield urldata
        current_object = urldata.inside

def canonical_url_iterator(obj):
    """Iterate over the object and each of its canonical url parents.

    Raises NoCanonicalUrl if a canonical url is not available.
    """
    yield obj
    for urldata in canonical_urldata_iterator(obj):
        if urldata.inside is not None:
            yield urldata.inside

def canonical_url(obj, request=None):
    """Return the canonical URL string for the object.

    If the request is provided, then protocol, host and port are taken
    from the request.

    If a request is not provided, but a web-request is in progress,
    the protocol, host and port are taken from the current request.

    Otherwise, the protocol, host and port are taken from the root_url given in
    launchpad.conf.

    Raises NoCanonicalUrl if a canonical url is not available.
    """
    urlparts = [urldata.path
                for urldata in canonical_urldata_iterator(obj)
                if urldata.path]

    if request is None:
        # Look for a request from the interaction.  If there is none, fall
        # back to the root_url from the config file.
        current_request = get_current_browser_request()
        if current_request is not None:
            request = current_request

    if request is None:
        root_url = config.launchpad.root_url
    else:
        root_url = request.getApplicationURL() + '/'
    return root_url + '/'.join(reversed(urlparts))

def get_current_browser_request():
    """Return the current browser request, looked up from the interaction.

    If there is no suitable request, then return None.

    Returns only requests that provide IHTTPApplicationRequest.
    """
    interaction = zope.security.management.queryInteraction()
    requests = [
        participation
        for participation in interaction.participations
        if IHTTPApplicationRequest.providedBy(participation)
        ]
    if not requests:
        return None
    assert len(requests) == 1, (
        "We expect only one IHTTPApplicationRequest in the interaction."
        " Got %s." % len(requests))
    return requests[0]

def nearest(obj, *interfaces):
    """Return the nearest object up the canonical url chain that provides
    one of the interfaces given.

    The object returned might be the object given as an argument, if that
    object provides one of the given interfaces.

    Return None is no suitable object is found.
    """
    for current_obj in canonical_url_iterator(obj):
        for interface in interfaces:
            if interface.providedBy(current_obj):
                return current_obj
    return None


class RootObject:
    implements(ILaunchpadApplication, ILaunchpadRoot)

rootObject = ProxyFactory(RootObject(), NamesChecker(["__class__"]))


class Navigation:
    """Base class for writing browser navigation components.

    Note that the canonical_url part of Navigation is used outside of
    the browser context.

    Override or set these things:

        def traverse(name):

        namespace_traversals = {'+bug': traverse_bug}
        new_layer = ShipitLayer

    """
    implements(IBrowserPublisher)

    def __init__(self, context, request=None):
        """Initialize with context and maybe with a request."""
        self.context = context
        self.request = request

    # Set this if you want to set a new layer before doing any traversal.
    newlayer = None

    def traverse(self, name):
        """Override this method to handle traversal.

        Raise NotFoundError if the name cannot be traversed.
        """
        raise NotFoundError(name)

    # The next methods are for use by the Zope machinery.

    def publishTraverse(self, request, name):
        """Shim, to set objects in the launchbag when traversing them.

        This needs moving into the publication component, once it has been
        refactored.
        """
        nextobj = self._publishTraverse(request, name)
        getUtility(IOpenLaunchBag).add(nextobj)
        return nextobj

    def _combined_class_info(self, attrname):
        """Walk the class's __mro__ looking for attributes with the given
        name in class dicts.  Combine the values of these attributes into
        a single dict.  Return it.
        """
        combined_info = {}
        for cls in type(self).__mro__:
            value = cls.__dict__.get(attrname)
            if value is not None:
                combined_info.update(value)
        return combined_info

    def _publishTraverse(self, request, name):
        """Traverse, like zope wants."""

        # First, set a new layer if there is one.  This is important to do
        # first so that if there's an error, we get the error page for
        # this request.
        if self.newlayer is not None:
            setFirstLayer(request, self.newlayer)

        # Next, see if we're being asked to stepto somewhere.
        stepto_traversals = self._combined_class_info('__stepto_traversals__')
        if stepto_traversals is not None:
            if name in stepto_traversals:
                handler = stepto_traversals[name]
                return handler(self)

        # Next, see if we have at least two path steps in total to traverse;
        # that is, the current name and one on the request's traversal stack.
        # If so, see if the name is in the namespace_traversals, and if so,
        # dispatch to the appropriate function.  We can optimise by changing
        # the order of these checks around a bit.
        namespace_traversals = self._combined_class_info(
            '__stepthrough_traversals__')
        if namespace_traversals is not None:
            if name in namespace_traversals:
                stepstogo = request.stepstogo
                if stepstogo:
                    nextstep = stepstogo.consume()
                    handler = namespace_traversals[name]
                    return handler(self, nextstep)

        # Next, look up views on the context object.  If a view exists,
        # use it.
        view = queryView(self.context, name, request)
        if view is not None:
            return view

        # Next, look up redirections.  Note that registered views take
        # priority over redirections, because you can always make your
        # view redirect, but you can't make your redirection 'view'.
        redirections = self._combined_class_info('__redirections__')
        if redirections is not None:
            if name in redirections:
                return RedirectionView(redirections[name], request)

        # Finally, use the self.traverse() method.  This can return
        # an object to be traversed, or raise NotFoundError.  It must not
        # return None.
        try:
            nextobj = self.traverse(name)
        except NotFoundError:
            raise NotFound(self.context, name)
        if nextobj is None:
            raise NotFound(self.context, name)
        return nextobj

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name, )


class RedirectionView:
    implements(IBrowserPublisher)

    def __init__(self, target, request):
        self.target = target
        self.request = request

    def __call__(self):
        self.request.response.redirect(self.target)
        return ''

    def browserDefault(self, request):
        return self, ()


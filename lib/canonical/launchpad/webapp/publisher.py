# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Publisher of objects as web pages.

"""

__metaclass__ = type
__all__ = [
    'LaunchpadView',
    'LaunchpadXMLRPCView',
    'canonical_name',
    'canonical_url',
    'canonical_url_iterator',
    'get_current_browser_request',
    'nearest',
    'Navigation',
    'rootObject',
    'stepthrough',
    'redirection',
    'stepto',
    'RedirectionView',
    'RenamedView',
    'UserAttributeCache',
    ]

from zope.interface import implements
from zope.component import getUtility, queryMultiAdapter
from zope.app import zapi
from zope.interface.advice import addClassAdvisor
import zope.security.management
from zope.security.checker import ProxyFactory, NamesChecker
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces.http import IHTTPApplicationRequest
from zope.app.publisher.interfaces.xmlrpc import IXMLRPCView
from zope.app.publisher.xmlrpc import IMethodPublisher
from zope.publisher.interfaces import NotFound

from canonical.launchpad.layers import (
    setFirstLayer, ShipItUbuntuLayer, ShipItKUbuntuLayer, ShipItEdUbuntuLayer)
from canonical.launchpad.webapp.vhosts import allvhosts
from canonical.launchpad.webapp.interfaces import (
    ICanonicalUrlData, NoCanonicalUrl, ILaunchpadRoot, ILaunchpadApplication,
    ILaunchBag, IOpenLaunchBag, IBreadcrumb, NotFoundError)
from canonical.launchpad.webapp.url import urlappend


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

    def getValueToStore(self):
        return self.fn

    def advise(self, cls):
        assert self.magic_class_attribute is not None, (
            'You must provide the magic_class_attribute to use')
        D = cls.__dict__.get(self.magic_class_attribute)
        if D is None:
            D = {}
            setattr(cls, self.magic_class_attribute, D)
        D[self.name] = self.getValueToStore()
        return cls


class stepthrough(DecoratorAdvisor):

    magic_class_attribute = '__stepthrough_traversals__'

    def __init__(self, name, breadcrumb=None):
        """Register a stepthrough traversal with the name stepped through.

        You can optionally provide a breadcrumb function that is called
        with the argument 'self'.  So, a method will do.
        """
        DecoratorAdvisor.__init__(self, name)
        self.breadcrumb = breadcrumb

    def getValueToStore(self):
        return (self.fn, self.breadcrumb)


class stepto(DecoratorAdvisor):

    magic_class_attribute = '__stepto_traversals__'


class redirection:
    """A redirection is used for two related purposes.

    It is a class advisor in its two argument form or as a descriptor.
    It says what name is mapped to where.

    It is an object returned from a traversal method in its one argument
    form.  It says that the result of such traversal is a redirect.

    You can use the keyword argument 'status' to change the status code
    from the default of 303 (assuming http/1.1).
    """

    def __init__(self, arg1, arg2=None, status=None):
        if arg2 is None:
            self.fromname = None
            self.toname = arg1
        else:
            self.fromname = arg1
            self.toname = lambda self: arg2
            addClassAdvisor(self.advise)
        self.status = status

    def __call__(self, fn):
        # We are being used as a descriptor.
        assert self.fromname is None, (
            "redirection() can not be used as a descriptor in its "
            "two argument form")

        self.fromname = self.toname
        self.toname = fn
        addClassAdvisor(self.advise)

        return fn

    def advise(self, cls):
        redirections = cls.__dict__.get('__redirections__')
        if redirections is None:
            redirections = {}
            setattr(cls, '__redirections__', redirections)
        redirections[self.fromname] = (self.toname, self.status)
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

    _is_beta = None
    @property
    def isBetaUser(self):
        """Return True if the user is in the beta testers team."""
        if self._is_beta is not None:
            return self._is_beta

        # We cannot import ILaunchpadCelebrities here, so we will use the
        # hardcoded name of the beta testers team
        self._is_beta = self.user is not None and self.user.inTeam(
            'launchpad-beta-testers')
        return self._is_beta


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
    - isBetaUser   <-- whether the logged-in user is a beta tester
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def initialize(self):
        """Override this in subclasses.

        Default implementation does nothing.
        """
        pass

    @property
    def template(self):
        """The page's template, if configured in zcml."""
        return self.index

    def render(self):
        """Return the body of the response.

        If the mime type of request.response starts with text/, then
        the result of this method is encoded to the charset of
        request.response. If there is no charset, it is encoded to
        utf8. Otherwise, the result of this method is treated as bytes.

        XXX: Steve Alexander says this is a convenient lie. That is, its
        not quite right, but good enough for most uses.
        """
        return self.template()

    def _isRedirected(self):
        """Return True if a redirect was requested.

        Check if the response status is one of 301, 302, 303 or 307.
        """
        return self.request.response.getStatus() in [301, 302, 303, 307]

    def __call__(self):
        self.initialize()
        if self._isRedirected():
            # Don't render the page on redirects.
            return u''
        else:
            return self.render()


class LaunchpadXMLRPCView(UserAttributeCache):
    """Base class for writing XMLRPC view code."""

    implements(IXMLRPCView, IMethodPublisher)

    def __init__(self, context, request):
        self.context = context
        self.request = request


class LaunchpadRootUrlData:
    """ICanonicalUrlData for the ILaunchpadRoot object."""

    implements(ICanonicalUrlData)

    path = ''
    inside = None
    rootsite = None

    def __init__(self, context):
        self.context = context


def canonical_urldata_iterator(obj):
    """Iterate over the urldata for the object and each of its canonical url
    parents.

    Raises NoCanonicalUrl if canonical url data is not available.
    """
    current_object = obj
    urldata = None
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


def canonical_url(
    obj, request=None, rootsite=None, path_only_if_possible=False):
    """Return the canonical URL string for the object.

    If the canonical url configuration for the given object binds it to a
    particular root site, then we use that root URL.

    (There is an assumption here that traversal works the same way on
     different sites.  When that isn't so, we need to specify the url
     in full in the canonical url configuration.  We may want to
     register canonical url configuration *for* particular sites in the
     future, to allow more flexibility for traversal.
     I foresee a refactoring where we'll combine the concepts of
     sites, layers, URLs and so on.)

    Otherwise, we attempt to take the protocol, host and port from
    the request.  If a request is not provided, but a web-request is in
    progress, the protocol, host and port are taken from the current request.

    If there is no request available, the protocol, host and port are taken
    from the root_url given in launchpad.conf.

    Raises NoCanonicalUrl if a canonical url is not available.
    """
    urlparts = [urldata.path
                for urldata in canonical_urldata_iterator(obj)
                if urldata.path]

    if rootsite is None:
        obj_urldata = ICanonicalUrlData(obj, None)
        if obj_urldata is None:
            raise NoCanonicalUrl(obj, obj)
        rootsite = obj_urldata.rootsite

    # The request is needed when there's no rootsite specified and when
    # handling the different shipit sites.
    if request is None:
        # Look for a request from the interaction.
        current_request = get_current_browser_request()
        if current_request is not None:
            request = current_request

    if rootsite is None:
        # This means we should use the request, or fall back to the main site.

        # If there is no request, fall back to the root_url from the
        # config file.
        if request is None:
            root_url = allvhosts.configs['mainsite'].rooturl
        else:
            root_url = request.getApplicationURL() + '/'
    else:
        # We should use the site given.
        if rootsite in allvhosts.configs:
            root_url = allvhosts.configs[rootsite].rooturl
        elif rootsite == 'shipit':
            # Special case for shipit.  We need to take the request's layer
            # into account.
            if ShipItUbuntuLayer.providedBy(request):
                root_url = allvhosts.configs['shipitubuntu'].rooturl
            elif ShipItEdUbuntuLayer.providedBy(request):
                root_url = allvhosts.configs['shipitedubuntu'].rooturl
            elif ShipItKUbuntuLayer.providedBy(request):
                root_url = allvhosts.configs['shipitkubuntu'].rooturl
            elif request is None:
                # Fall back to shipitubuntu_root_url
                root_url = allvhosts.configs['shipitubuntu'].rooturl
            else:
                raise AssertionError(
                    "Shipit canonical urls must be used only with request "
                    "== None or a request providing one of the ShipIt Layers")
        else:
            raise AssertionError("rootsite is %s.  Must be in %r." % (
                    rootsite, sorted(allvhosts.configs.keys())
                    ))
    path = u'/'.join(reversed(urlparts))
    if (path_only_if_possible and
        request is not None and
        root_url.startswith(request.getApplicationURL())
        ):
        return unicode('/' + path)
    return unicode(root_url + path)


def canonical_name(name):
    """Return the canonical form of a name used in a URL.

    This helps us to deal with common mistypings of URLs.
    Currently only accounts for uppercase letters.

    >>> canonical_name('ubuntu')
    'ubuntu'
    >>> canonical_name('UbUntU')
    'ubuntu'

    """
    return name.lower()


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
    # These next two needed by the Z3 API browser
    __parent__ = None
    __name__ = 'Launchpad'


rootObject = ProxyFactory(RootObject(), NamesChecker(["__class__"]))


class Breadcrumb:
    implements(IBreadcrumb)

    def __init__(self, url, text, has_menu=False):
        self.url = url
        self.text = text
        self.has_menu = has_menu


class Navigation:
    """Base class for writing browser navigation components.

    Note that the canonical_url part of Navigation is used outside of
    the browser context.
    """
    implements(IBrowserPublisher)

    def __init__(self, context, request=None):
        """Initialize with context and maybe with a request."""
        self.context = context
        self.request = request

    # Set this if you want to set a new layer before doing any traversal.
    newlayer = None

    def breadcrumb(self):
        """Return the text of the context object's breadcrumb, or None for
        no breadcrumb.
        """
        return None

    def traverse(self, name):
        """Override this method to handle traversal.

        Raise NotFoundError if the name cannot be traversed.
        """
        raise NotFoundError(name)

    def redirectSubTree(self, target, status=301):
        """Redirect the subtree to the given target URL."""
        while True:
            nextstep = self.request.stepstogo.consume()
            if nextstep is None:
                break
            target = urlappend(target, nextstep)

        query_string = self.request.get('QUERY_STRING')
        if query_string:
            target = target + '?' + query_string

        return RedirectionView(target, self.request, status)

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
        # Note that we want to give info from more specific classes priority
        # over info from less specific classes.  We can do this by walking
        # the __mro__ backwards, and using dict.update(...)
        for cls in reversed(type(self).__mro__):
            value = cls.__dict__.get(attrname)
            if value is not None:
                combined_info.update(value)
        return combined_info

    def _append_breadcrumb(self, text):
        """Add a breadcrumb to the request, at the current URL with the given
        text.

        request.getURL(1) represents the path traversed so far, but without
        the step we're currently working out how to traverse.
        """
        # If self.context has a view called +menudata, it has a menu.
        menuview = queryMultiAdapter(
            (self.context, self.request), name="+menudata")
        if menuview is None:
            has_menu = False
        else:
            has_menu = menuview.submenuHasItems('')
        self.request.breadcrumbs.append(
            Breadcrumb(self.request.getURL(1, path_only=False), text, has_menu))

    def _handle_next_object(self, nextobj, request, name):
        """Do the right thing with the outcome of traversal.

        If we have a redirection object, then redirect accordingly.

        If we have None, issue a NotFound error.

        Otherwise, return the object.
        """
        if nextobj is None:
            raise NotFound(self.context, name)
        elif isinstance(nextobj, redirection):
            return RedirectionView(
                nextobj.toname, request, status=nextobj.status)
        else:
            return nextobj

    def _publishTraverse(self, request, name):
        """Traverse, like zope wants."""

        # First, set a new layer if there is one.  This is important to do
        # first so that if there's an error, we get the error page for
        # this request.
        if self.newlayer is not None:
            setFirstLayer(request, self.newlayer)

        # store the current context object in the request's
        # traversed_objects list:
        request.traversed_objects.append(self.context)

        # Next, if there is a breadcrumb for the context, add it to the
        # request's list of breadcrumbs.
        breadcrumb_text = self.breadcrumb()
        if breadcrumb_text is not None:
            self._append_breadcrumb(breadcrumb_text)

        # Next, see if we're being asked to stepto somewhere.
        stepto_traversals = self._combined_class_info('__stepto_traversals__')
        if stepto_traversals is not None:
            if name in stepto_traversals:
                handler = stepto_traversals[name]
                try:
                    nextobj = handler(self)
                except NotFoundError:
                    nextobj = None
                return self._handle_next_object(nextobj, request, name)

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
                    handler, breadcrumb_fn = namespace_traversals[name]
                    if breadcrumb_fn is not None:
                        breadcrumb_text = breadcrumb_fn(self)
                        if breadcrumb_text is not None:
                            self._append_breadcrumb(breadcrumb_text)
                    try:
                        nextobj = handler(self, nextstep)
                    except NotFoundError:
                        nextobj = None
                    return self._handle_next_object(nextobj, request, nextstep)

        # Next, look up views on the context object.  If a view exists,
        # use it.
        view = zapi.queryMultiAdapter((self.context, request), name=name)
        if view is not None:
            return view

        # Next, look up redirections.  Note that registered views take
        # priority over redirections, because you can always make your
        # view redirect, but you can't make your redirection 'view'.
        redirections = self._combined_class_info('__redirections__')
        if redirections is not None:
            if name in redirections:
                urlto, status = redirections[name]
                return RedirectionView(urlto(self), request, status=status)

        # Finally, use the self.traverse() method.  This can return
        # an object to be traversed, or raise NotFoundError.  It must not
        # return None.
        try:
            nextobj = self.traverse(name)
        except NotFoundError:
            nextobj = None
        return self._handle_next_object(nextobj, request, name)

    def browserDefault(self, request):
        view_name = zapi.getDefaultViewName(self.context, request)
        return self.context, (view_name, )


class RedirectionView:
    implements(IBrowserPublisher)

    def __init__(self, target, request, status=None):
        self.target = target
        self.request = request
        self.status = status

    def __call__(self):
        self.request.response.redirect(self.target, status=self.status)
        return u''

    def browserDefault(self, request):
        return self, ()


class RenamedView:
    """Redirect permanently to the new name of the view.

    This view should be used when pages are renamed.

    :param new_name: the new page name.
    :param rootsite: (optional) the virtual host to redirect to,
            e.g. 'answers'.
    """
    implements(IBrowserPublisher)

    def __init__(self, context, request, new_name, rootsite=None):
        self.context = context
        self.request = request
        self.new_name = new_name
        self.rootsite = rootsite

    def __call__(self):
        target_url = "%s/%s" % (
            canonical_url(self.context, rootsite=self.rootsite),
            self.new_name)

        query_string = self.request.get('QUERY_STRING', '')
        if query_string:
            target_url += '?' + query_string

        self.request.response.redirect(target_url, status=301)

        return u''

    def publishTraverse(self, request, name):
        """See zope.publisher.interfaces.browser.IBrowserPublisher."""
        raise NotFound(name)

    def browserDefault(self, request):
        """See zope.publisher.interfaces.browser.IBrowserPublisher."""
        return self, ()

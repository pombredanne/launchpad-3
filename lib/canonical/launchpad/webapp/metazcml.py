# (c) Canonical Software Ltd. 2004, all rights reserved.
"""Implementation of the browser:suburl and browser:traverser directives.
"""

__metaclass__ = type

import sets
import inspect
from zope.interface import Interface, Attribute, implements
from zope.interface.interfaces import IInterface
from zope.component import queryView, queryMultiView, getDefaultViewName
from zope.component import getUtility
from zope.component.interfaces import IDefaultViewName
from zope.schema import TextLine, Id
from zope.configuration.fields import (
    GlobalObject, PythonIdentifier, Path, Tokens
    )
from zope.security.checker import CheckerPublic, Checker
from zope.security.proxy import ProxyFactory
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound
from zope.app import zapi
from zope.app.component.metaconfigure import (
    handler, adapter, utility, view, PublicPermission
    )
from zope.app.component.contentdirective import ContentDirective
from zope.app.component.interface import provideInterface
from zope.app.security.fields import Permission
from zope.app.pagetemplate.engine import Engine
from zope.app.component.fields import LayerField
from zope.app.file.image import Image
from zope.app.publisher.browser.viewmeta import page
import zope.app.publisher.browser.metadirectives

from canonical.launchpad.layers import setAdditionalLayer
from canonical.launchpad.interfaces import (
    IAuthorization, IOpenLaunchBag, IBasicLink, ILink, IFacetList, ITabList,
    ICanonicalUrlData
    )

try:
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
except ImportError:
    # This code can go once we've upgraded Zope.
    from zope.publisher.interfaces.browser import IBrowserRequest
    IDefaultBrowserLayer = IBrowserRequest


class ILinkDirective(Interface):
    """Define a link."""

    id = PythonIdentifier(
        title=u'Id',
        description=u'Id as which this object will be known and used.',
        required=True)

    href = TextLine(
        title=u'HREF',
        description=u'Relative href for this facet.',
        required=True)

    title = TextLine(
        title=u'Title',
        description=u'Title, shown as the text of a link',
        required=True)

    summary = TextLine(
        title=u'Summary',
        description=u'Summary, shown as the tooltip of a link.',
        required=False)


class IFacetListDirective(Interface):
    """Say what facets apply for a particular interface."""

    for_ = GlobalObject(
        title=u'the interface this facet list is for',
        required=True)

    links = Tokens(
        title=u'Links',
        description=u'Link ids that will be rendered as main links.'
                     ' If this attribute is not given, one will be sought'
                     ' from a more general interface.',
        value_type=PythonIdentifier(),
        required=False)

    overflow = Tokens(
        title=u'Overflow',
        description=u'Link ids that will be rendered as overflow.',
        value_type=PythonIdentifier(),
        required=False)

    disabled = Tokens(
        title=u'disabled',
        description=u'Link ids that will be rendered as disabled for this'
                     ' kind of object, whether they are main links or'
                     ' overflow.',
        value_type=PythonIdentifier(),
        required=False)

class ITabListDirective(Interface):
    """Say what tabs apply for a particular interface."""

    for_ = GlobalObject(
        title=u'the interface this tab list is for',
        required=True)

    links = Tokens(
        title=u'Links',
        description=u'Link ids that will be rendered as main links.'
                     ' If this attribute is not given, one will be sought'
                     ' from a more general interface.',
        value_type=PythonIdentifier(),
        required=False)

    overflow = Tokens(
        title=u'Overflow',
        description=u'Link ids that will be rendered as overflow.',
        value_type=PythonIdentifier(),
        required=False)

    disabled = Tokens(
        title=u'disabled',
        description=u'Link ids that will be rendered as disabled for this'
                     ' kind of object, whether they are main links or'
                     ' overflow.',
        value_type=PythonIdentifier(),
        required=False)

    facet = PythonIdentifier(
        title=u"The facet id that this set of tabs applies to",
        required=True)


class BasicLink:
    implements(IBasicLink)
    def __init__(self, id, href, title, summary):
        self.id = id
        self.href = href
        self.title = title
        self.summary = summary


class Link:
    implements(ILink)
    def __init__(self, basiclink, enabled):
        self.id = basiclink.id
        self.href = basiclink.href
        self.title = basiclink.title
        self.summary = basiclink.summary
        self.enabled = enabled


class FacetList:
    implements(IFacetList)

    def __init__(self, links, overflow, disabled, lookuplinksfrom=None):
        """Set up self.links and self.overflow.

        links is a list of main link ids.
        overflow is a list of overflow link ids.
        disabled is a list of disabled link ids.

        lookuplinksfrom is an interface to use to find main and overflow
        'links' from its facet list, if links is not given.
        """
        # Check that disabled links actually exist.
        [getUtility(IBasicLink, id) for id in disabled]
        self._disabled = disabled
        if lookuplinksfrom is not None:
            class DummyClassToQueryRegistry:
                implements(lookuplinksfrom)
            dummyobject = DummyClassToQueryRegistry()
        if links is None:
            assert lookuplinksfrom is not None, (
                "You must define 'links' on a more general interface"
                " if you do not define 'links' explicitly.")
            self.links = [
                self._makelink(link.id)
                for link in IFacetList(dummyobject).links
                ]
        else:
            self.links = [self._makelink(id) for id in links]

        if overflow is None:
            assert lookuplinksfrom is not None, (
                "You must define 'overflow' on a more general interface"
                " if you do not define 'overflow' explicitly.")
            self.overflow = [
                self._makelink(link.id)
                for link in IFacetList(dummyobject).overflow
                ]
        else:
            self.overflow = [self._makelink(id) for id in overflow]

    def _makelink(self, id):
        basiclink = getUtility(IBasicLink, id)
        enabled = id not in self._disabled
        return Link(basiclink, enabled)


class TabList:
    implements(ITabList)

    def __init__(self, facet, links, overflow, disabled, lookuplinksfrom=None):
        """Set up self.links and self.overflow.

        links is a list of main link ids.
        overflow is a list of overflow link ids.
        disabled is a list of disabled link ids.

        lookuplinksfrom is an interface to use to find main and overflow
        'links' from its facet list, if links is not given.
        """
        # Check that disabled links actually exist.
        [getUtility(IBasicLink, id) for id in disabled]
        self._disabled = disabled
        self._facet = facet
        if lookuplinksfrom is not None:
            class DummyClassToQueryRegistry:
                implements(lookuplinksfrom)
            dummyobject = DummyClassToQueryRegistry()
        if links is None:
            assert lookuplinksfrom is not None, (
                "You must define 'links' on a more general interface"
                " if you do not define 'links' explicitly.")
            self.links = [
                self._makelink(link.id)
                for link in getAdapter(dummyobject, ITabList, facet).links
                ]
        else:
            self.links = [self._makelink(id) for id in links]

        if overflow is None:
            assert lookuplinksfrom is not None, (
                "You must define 'overflow' on a more general interface"
                " if you do not define 'overflow' explicitly.")
            self.overflow = [
                self._makelink(link.id)
                for link in getAdapter(dummyobject, ITabList, facet).overflow
                ]
        else:
            self.overflow = [self._makelink(id) for id in overflow]

    def _makelink(self, id):
        basiclink = getUtility(IBasicLink, id)
        enabled = id not in self._disabled
        return Link(basiclink, enabled)


class DeferedZcmlFactory:
    """Factory for an object we want to instantiate after the zcml actions
    have been processed.
    """
    def __init__(self, factory, *args):
        self.factory = factory
        self.args = args

    def __call__(self, context):
        return self.factory(*self.args)

def link(_context, id, href, title, summary):
    """A link directive is registered as an IBasicLink utility named after
    the id.
    """
    provides = IBasicLink
    component = BasicLink(id, href, title, summary)
    utility(_context, provides, component=component, name=id)


class FacetAndTabConfigProcessor:
    """Process configuration directives for facets and tabs."""
    def __init__(
        self, _context, for_, links=None, overflow=None, disabled=None):
        """Save the state for config processing."""
        if not IInterface.providedBy(for_):
            raise TypeError("for attribute must be an interface: %r"
                            % (for_, ))
        if links is None or overflow is None:
            iro = list(for_.__iro__)
            if len(iro) < 2:
                raise TypeError(
                    "No parent interface for 'for' attribute: %r" % (for_, ))
            self.lookuplinksfrom = iro[1]
        else:
            self.lookuplinksfrom = None

        if disabled is None:
            disabled = []
        for_ = [for_]

        self._context = _context
        self.for_ = for_
        self.links = links
        self.overflow = overflow
        self.disabled = disabled
        self.name = ""

    def facetFactory(self):
        """Get a Facet ZCML Factory."""
        return [DeferedZcmlFactory(
            FacetList, self.links, self.overflow,
            self.disabled, self.lookuplinksfrom)]

    def tabFactory(self, name):
        """Get a Tab ZCML Factory."""
        self.name = name
        return [DeferedZcmlFactory(
            TabList, self.name,
            self.links, self.overflow,
            self.disabled, self.lookuplinksfrom)]

    def makeAdapter(self, factory, provides):
        """Register an adapter for the provided factory that provides provides.
        """
        adapter(self._context, factory, provides, self.for_, name=self.name)

def facetlist(_context, for_, links=None, overflow=None, disabled=None):
    """A facetlist directive is registered as an IFacetList adapter.

    XXX: This really ought to be a view that provides IFacetList.
         -- SteveAlexander, 2005-04-26
    """
    processor = FacetAndTabConfigProcessor(
        _context, for_, links, overflow, disabled)
    factory = processor.facetFactory()
    provides = IFacetList
    processor.makeAdapter(factory, provides)

def tablist(_context, for_, facet, links=None, overflow=None, disabled=None):
    """A tablist directive is registered as an ITabList adapter.

    XXX: This really ought to be a view that provides ITabList.
        -- SteveAlexander, 2005-04-26
    """
    processor = FacetAndTabConfigProcessor(
        _context, for_, links, overflow, disabled)
    factory = processor.tabFactory(facet)
    provides = ITabList
    processor.makeAdapter(factory, provides)


class IAuthorizationsDirective(Interface):
    """Set up authorizations as given in a module."""

    module = GlobalObject(title=u'module', required=True)

def _isAuthorization(module_member):
    return (type(module_member) is type and
            IAuthorization.implementedBy(module_member))

def authorizations(_context, module):
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    provides = IAuthorization
    for nameinmodule, authorization in inspect.getmembers(module,
                                                          _isAuthorization):
        if (authorization.permission is not None and
            authorization.usedfor is not None):
            name = authorization.permission
            for_ = [authorization.usedfor]
            factory = [authorization]
            adapter(_context, factory, provides, for_, name=name)


class ISecuredUtilityDirective(Interface):
    """Configure a utility with security directives."""

    class_ = GlobalObject(title=u'class', required=True)

    provides = GlobalObject(
        title=u'interface this utility provides',
        required=True)


class PermissionCollectingContext:

    def __init__(self):
        self.get_permissions = {}
        self.set_permissions = {}

    def action(self, discriminator=None, callable=None, args=None):
        if isinstance(discriminator, tuple):
            if discriminator:
                discriminator_name = discriminator[0]
                cls, name, permission = args
                if discriminator_name == 'protectName':
                    self.get_permissions[name] = permission
                elif discriminator_name == 'protectSetAttribute':
                    self.set_permissions[name] = permission
                else:
                    raise RuntimeError("unrecognised discriminator name", name)

class SecuredUtilityDirective:

    def __init__(self, _context, class_, provides):
        self.component = class_()
        self._context = _context
        self.provides = provides
        self.permission_collector = PermissionCollectingContext()
        self.contentdirective = ContentDirective(
            self.permission_collector, class_)

    def require(self, _context, **kw):
        self.contentdirective.require(_context, **kw)

    def allow(self, _context, **kw):
        self.contentdirective.allow(_context, **kw)

    def __call__(self):
        # Set up the utility with an appropriate proxy.
        # Note that this does not take into account other security
        # directives on this content made later on during the execution
        # of the zcml.
        checker = Checker(
            self.permission_collector.get_permissions,
            self.permission_collector.set_permissions
            )
        component = ProxyFactory(self.component, checker=checker)
        utility(self._context, self.provides, component=component)
        return ()


class ISubURLDispatch(Interface):

    def __call__():
        """Returns the object at this suburl"""


class SubURLTraverser:
    implements(IBrowserPublisher)

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """Search for views, and if no view is found, look for subURLs."""
        view = queryView(self.context, name, request)
        # XXX I should be looking for views for normal publication here.
        # so, views providing ISubURLDispatch and not "normal publication"
        # shouldn't show up.
        if view is None or ISubURLDispatch.providedBy(view):
            if view is None:
                dispatcher = queryMultiView((self.context,), request,
                        providing=ISubURLDispatch, name=name)
                if dispatcher is None:
                    raise NotFound(self.context, name)
            else:
                dispatcher = view
            ob = dispatcher()
            getUtility(IOpenLaunchBag).add(ob)
            return ob
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)

class IDefaultViewDirective(
    zope.app.publisher.browser.metadirectives.IDefaultViewDirective):

    layer = LayerField(
        title=u"The layer to declare this default view for",
        required=False
        )

class ISubURLDirective(Interface):

    for_ = GlobalObject(
        title=u"Specification of the object that has this suburl",
        required=True
        )

    permission = Permission(
        title=u"Permission",
        required=False
        )

    class_ = GlobalObject(
        title=u"Class",
        required=False
        )

    utility = GlobalObject(
        title=u"Utility",
        required=False
        )

    name = TextLine(
        title=u"The name of the suburl.",
        required=True
        )

    adaptwith = GlobalObject(
        title=u"Adapter factory to use",
        required=False
        )

    newlayer = LayerField(
        title=u"New layer to use beneath this URL",
        required=False
        )


class ITraverseDirective(Interface):

    for_ = GlobalObject(
        title=u"Specification of the object that is traversed",
        required=True
        )

    permission = Permission(
        title=u"Permission",
        required=False
        )

    getter = PythonIdentifier(
        title=u"Name of the getter method to use",
        required=False
        )

    function = GlobalObject(
        title=u"function of the form func(obj, request, name) that traverses"
               " the object by the name, and returns the object traversed to.",
        required=False
        )

    adaptwith = GlobalObject(
        title=u"Adapter factory to use",
        required=False
        )

    layer = LayerField(
        title=u"The layer that this traversal applies to",
        required=False
        )


class IURLDirective(Interface):
    """Say how to compute canonical urls."""

    for_ = GlobalObject(
        title=u"Specification of the object that has this canonical url",
        required=True
        )

    path_expression = TextLine(
        title=u"TALES expression that evaluates to the path"
               " relative to the parent object.",
        required=True
        )

    attribute_to_parent = PythonIdentifier(
        title=u"Name of the attribute that gets you to the parent object",
        required=False
        )

    parent_utility = GlobalObject(
        title=u"Interface of the utility that is the parent of the object",
        required=False
        )


class IFaviconDirective(Interface):

    for_ = GlobalObject(
        title=u"Specification of the object that has this favicon",
        required=True
        )

    file = Path(
        title=u"Path to the image file",
        required=True
        )


class SubURLDispatcher:
    implements(ISubURLDispatch)

    newlayer = None

    def __init__(self, context, request):
        # In future, we may use the context to provide a __parent__ for
        # the app-level component.
        # Perhaps the zcml directive will allow us to specify an app-level
        # name too. yagni for now.
        self.context = context
        self.request = request

    def __call__(self):
        raise NotImplementedError


# The `for_` objects we have already seen, so we set their traverser to be
# the SubURLTraverser once only.  If we set it more than once, we get
# a configuration conflict error.
suburl_traversers = sets.Set()

def suburl(_context, for_, name, permission=None, utility=None, class_=None,
           adaptwith=None, newlayer=None):
    if utility is None and class_ is None:
        raise TypeError("Cannot specify both utility and class.")

    # So we can use "type" below, for documentation.
    type = IDefaultBrowserLayer

    global suburl_traversers
    if for_ not in suburl_traversers:
        view(_context, [SubURLTraverser], type, '', [for_],
             provides=IBrowserPublisher, permission=None)
        suburl_traversers.add(for_)


    # TODO: Move layer-setting into a handler for the BeforeTraverse event
    #       because that's actually what we want to handle.

    if class_ is not None:
        class Dispatcher(SubURLDispatcher):
            def __call__(self):
                # Note that `newlayer`, `class_` and `adaptwith` are bound
                # from the containing context.
                val = class_()
                if adaptwith is not None:
                    val = adaptwith(val)
                if newlayer is not None:
                    setAdditionalLayer(self.request, newlayer)
                #getUtility(IOpenLaunchBag).add(val)
                return val

    if utility is not None:
        class Dispatcher(SubURLDispatcher):
            def __call__(self):
                # Note that `newlayer`, `utility` and `adaptwith` are bound
                # from the containing context.
                val = getUtility(utility)
                if adaptwith is not None:
                    val = adaptwith(val)
                if newlayer is not None:
                    setAdditionalLayer(self.request, newlayer)
                #getUtility(IOpenLaunchBag).add(val)
                return val

    factory = [Dispatcher]
    if permission == PublicPermission:
        permission = CheckerPublic

    view(_context, factory, type, name, [for_], permission=permission)

class URLTraverse:
    """Use the operation named by _getter to traverse an app component."""

    implements(IBrowserPublisher)

    _getter = '__getitem__'
    _adaptwith = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        view = queryView(self.context, name, request)
        if view is None:
            try:
                traversed_to = getattr(self.context, self._getter)(name)
            except KeyError:
                raise NotFound(self.context, name)
            else:
                if self._adaptwith is not None:
                    traversed_to = self._adaptwith(traversed_to)
                getUtility(IOpenLaunchBag).add(traversed_to)
                return traversed_to
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


class URLTraverseByFunction:
    """Use the function in _function to traverse an app component.

    _function should have the signature (obj, request, name) and should return
    None to indicate NotFound.
    """

    implements(IBrowserPublisher)

    _function = None
    _adaptwith = None

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        view = queryView(self.context, name, request)
        if view is None:
            traversed_to = self._function(self.context, request, name)
            if traversed_to is None:
                raise NotFound(self.context, name)
            else:
                if self._adaptwith is not None:
                    traversed_to = self._adaptwith(traversed_to)
                getUtility(IOpenLaunchBag).add(traversed_to)
                return traversed_to
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


def traverse(_context, for_, getter=None, function=None, permission=None,
             adaptwith=None, layer=IDefaultBrowserLayer):
    if getter is not None and function is not None:
        raise TypeError("Cannot specify both getter and function")
    if getter is None and function is None:
        raise TypeError("Must specify either getter or function")

    name = ''
    provides = IBrowserPublisher

    if getter:
        class URLTraverseGetter(URLTraverse):
            __used_for__ = for_
            _getter = getter
            _adaptwith = adaptwith

        factory = [URLTraverseGetter]

    if function:
        class URLTraverseFunction(URLTraverseByFunction):
            __used_for__ = for_
            _function = staticmethod(function)
            _adaptwith = adaptwith

        factory = [URLTraverseFunction]

    view(_context, factory, layer, name, [for_], permission=permission,
         provides=provides)


class InterfaceInstanceDispatcher:
    """Dispatch getitem on names that appear in the interface to the instance.
    """
    def __init__(self, interface, instance):
        self.interface = interface
        self.instance = instance

    def __getitem__(self, name):
        if name in self.interface:
            return getattr(self.instance, name)
        else:
            raise KeyError(name)


class TALESContextForInterfaceInstance:

    def __init__(self, interface, instance):
        self.vars = InterfaceInstanceDispatcher(interface, instance)


class CanonicalUrlDataBase:

    # This is not true in this base class.  It will be true for subclasses
    # that provide an 'inside' property.
    implements(ICanonicalUrlData)

    # Filled in by subclass.
    _for = None
    _compiled_path_expression = None 

    def __init__(self, context):
        self.context = context
        self._expression_context = TALESContextForInterfaceInstance(
            self._for, context)

    @property
    def path(self):
        return self._compiled_path_expression(self._expression_context)

def url(_context, for_, path_expression, attribute_to_parent=None,
        parent_utility=None):
    """browser:url directive handler."""
    if not attribute_to_parent and not parent_utility:
        raise TypeError(
            'Must provide either attribute_to_parent or parent_utility.')
    if attribute_to_parent:
        if attribute_to_parent not in for_:
            raise AttributeError('The name "%s" is not in %s.%s'
                % (attribute_to_parent, for_.__module__, for_.__name__))
    else:
        # Check that parent_utility can be looked up.
        # can't do this, as the utility directive hasn't been processed yet
        #getUtility(parent_utility)
        pass
    compiled_path_expression = Engine.compile(path_expression)

    if attribute_to_parent:
        class CanonicalUrlData(CanonicalUrlDataBase):
            _for = for_
            _compiled_path_expression = compiled_path_expression
            @property
            def inside(self):
                return getattr(self.context, attribute_to_parent)
    else:
        class CanonicalUrlData(CanonicalUrlDataBase):
            _for = for_
            _compiled_path_expression = compiled_path_expression
            @property
            def inside(self):
                return getUtility(parent_utility)

    factory = [CanonicalUrlData]
    provides = ICanonicalUrlData
    adapter(_context, factory, provides, [for_])

class FaviconRendererBase:

    # subclasses must provide a 'fileobj' member that has 'contentType'
    # and 'data' attributes.

    def __call__(self):
        self.request.response.setHeader('Content-type',
                                        self.file.contentType)
        return self.file.data


def favicon(_context, for_, file):
    fileobj = Image(open(file, 'rb').read())
    class Favicon(FaviconRendererBase):
        file = fileobj

    name = "favicon.ico"
    permission = CheckerPublic
    page(_context, name, permission, for_, class_=Favicon)

# This is pretty much copied from the browser publisher's metaconfigure
# module, but with the `layer` as an argument rather than hard-coded.
# When zope has the same change, we can remove this code, and the related
# override-include.
def defaultView(_context, name, for_=None, layer=IDefaultBrowserLayer):

    _context.action(
        discriminator = ('defaultViewName', for_, layer, name),
        callable = handler,
        args = (zapi.servicenames.Adapters, 'register',
                (for_, layer), IDefaultViewName, '', name, _context.info)
        )

    if for_ is not None:
        _context.action(
            discriminator = None,
            callable = provideInterface,
            args = ('', for_)
            )

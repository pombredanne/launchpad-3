# (c) Canonical Software Ltd. 2004, all rights reserved.
"""Implementation of the browser:suburl and browser:traverser directives.
"""

__metaclass__ = type

import inspect
from zope.interface import Interface, Attribute, implements
from zope.interface.interfaces import IInterface
from zope.component import queryView, queryMultiView, getDefaultViewName
from zope.component import getUtility
import zope.component.servicenames
from zope.component.interfaces import IDefaultViewName
from zope.schema import TextLine, Id
from zope.configuration.fields import (
    GlobalObject, PythonIdentifier, Path, Tokens)

from zope.security.checker import CheckerPublic, Checker
from zope.security.proxy import ProxyFactory
from zope.publisher.interfaces.browser import (
    IBrowserPublisher, IBrowserRequest)
from zope.publisher.interfaces import NotFound
from zope.app.component.metaconfigure import (
    handler, adapter, utility, view, PublicPermission)

from zope.app.component.contentdirective import ContentDirective
from zope.app.component.interface import provideInterface
from zope.app.security.fields import Permission
from zope.app.pagetemplate.engine import Engine
from zope.app.component.fields import LayerField
from zope.app.file.image import Image
import zope.app.publisher.browser.metadirectives
import zope.app.form.browser.metaconfigure
import zope.app.form.browser.metadirectives
from zope.app.publisher.browser.viewmeta import (
    pages as original_pages,
    page as original_page)

from zope.app.publisher.browser.metaconfigure import (
    defaultView as original_defaultView)

from canonical.launchpad.layers import setAdditionalLayer
from canonical.launchpad.interfaces import (
    IAuthorization, IOpenLaunchBag, ICanonicalUrlData,
    IFacetMenu, IExtraFacetMenu, IApplicationMenu, IExtraApplicationMenu)

try:
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
except ImportError:
    # This code can go once we've upgraded Zope.
    IDefaultBrowserLayer = IBrowserRequest


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

    urldata = GlobalObject(
        title=u"Adapter to ICanonicalUrlData for this object.",
        required=False
        )

    path_expression = TextLine(
        title=u"TALES expression that evaluates to the path"
               " relative to the parent object.",
        required=False
        )

    attribute_to_parent = PythonIdentifier(
        title=u"Name of the attribute that gets you to the parent object",
        required=False
        )

    parent_utility = GlobalObject(
        title=u"Interface of the utility that is the parent of the object",
        required=False
        )


class IMenusDirective(Interface):
    """Hook up facets and menus."""

    module = GlobalObject(
        title=u"Module in which menu classes are found.",
        required=True
        )

    classes = Tokens(
        value_type=PythonIdentifier(),
        title=u"Space separated list of classes to be registered as menus.",
        required=True
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
suburl_traversers = set()

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

def menus(_context, module, classes):
    """Handler for the IMenusDirective."""
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    menutypes = [IFacetMenu, IExtraFacetMenu, IApplicationMenu,
                 IExtraApplicationMenu]
    applicationmenutypes = [IApplicationMenu, IExtraApplicationMenu]
    for menuname in classes:
        menuclass = getattr(module, menuname)
        implemented = None
        for menutype in menutypes:
            if menutype.implementedBy(menuclass):
                assert implemented is None, (
                    'The menu class %r implements more than one of %s' %
                    (menuclass, menutypes))
                provides = menutype
                name = ''
                if menutype in applicationmenutypes:
                    name = getattr(menuclass, 'facet', None)
                    if name is None:
                        raise AssertionError(
                            'The menu %r needs a "facet" attribute'
                            ' saying what facet it is to be used for.'
                            % menuclass)
                break
        else:
            raise TypeError('class %r is not one of %s' %
                (menuclass, menutypes))
        for_ = [menuclass.usedfor]
        factory = [menuclass]
        adapter(_context, factory, provides, for_, name=name,
                permission=PublicPermission)

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

    def __getitem__(self, name, _marker=object()):
        value = self.get(name, _marker)
        if value is _marker:
            raise KeyError(name)
        else:
            return value

    def get(self, name, default=None):
        if name in self.interface:
            return getattr(self.instance, name)
        else:
            return default


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

def url(_context, for_, path_expression=None, urldata=None,
        attribute_to_parent=None, parent_utility=None):
    """browser:url directive handler."""
    if (not attribute_to_parent
        and not parent_utility
        and not urldata):
        raise TypeError(
            'Must provide attribute_to_parent, urldata or parent_utility.')
    if attribute_to_parent:
        if attribute_to_parent not in for_:
            raise AttributeError('The name "%s" is not in %s.%s'
                % (attribute_to_parent, for_.__module__, for_.__name__))
    if path_expression is not None:
        compiled_path_expression = Engine.compile(path_expression)

    if urldata:
        CanonicalUrlData = urldata
    elif attribute_to_parent:
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
    original_page(_context, name, permission, for_, class_=Favicon)


# The original defaultView directive is defined in the browser publisher code.
# In it, the `layer` is hard-coded rather than available as an argument.
# See zope/app/publisher/browser/metaconfigure.py.
# `layer` here is called `type` there, but is not available as an argument.

def defaultView(_context, name, for_=None, layer=IDefaultBrowserLayer):
    type = layer
    _context.action(
        discriminator = ('defaultViewName', for_, type, name),
        callable = handler,
        args = (zope.component.servicenames.Adapters, 'register',
                (for_, type), IDefaultViewName, '', name, _context.info)
        )

    if for_ is not None:
        _context.action(
            discriminator = None,
            callable = provideInterface,
            args = ('', for_)
            )


class IAssociatedWithAFacet(Interface):
    """A zcml schema for something that can be associated with a facet."""

    facet = TextLine(
        title=u"The name of the facet this page is associated with.",
        required=False)


class IPageDirective(
    zope.app.publisher.browser.metadirectives.IPageDirective,
    IAssociatedWithAFacet):
    """Extended browser:page directive to have an extra 'facet' attribute."""


def page(_context, name, permission, for_,
         layer=IBrowserRequest, template=None, class_=None,
         allowed_interface=None, allowed_attributes=None,
         attribute='__call__', menu=None, title=None,
         facet=None
         ):
    """Like the standard 'page' directive, but with an added 'facet' optional
    argument.

    If a facet is specified, then it will be available from the view class
    as __launchpad_facetname__.
    """
    if facet is None:
        new_class = class_
    else:
        cdict = {'__launchpad_facetname__': facet}
        if class_ is None:
            new_class = type('SimpleLaunchpadViewClass', (), cdict)
        else:
            new_class = type(class_.__name__, (class_, object), cdict)

    original_page(_context, name, permission, for_,
        layer=layer, template=template, class_=new_class,
        allowed_interface=allowed_interface,
        allowed_attributes=allowed_attributes,
        attribute=attribute, menu=menu, title=title)


class IPagesPageSubdirective(
    zope.app.publisher.browser.metadirectives.IPagesPageSubdirective,
    IAssociatedWithAFacet):
    """Extended complex browser:pages directive to have an extra 'facet'
    attribute on the inner <browser:page> element."""


class IPagesDirective(
    zope.app.publisher.browser.metadirectives.IPagesDirective,
    IAssociatedWithAFacet):
    """Extend the complex browser:pages directive to have an extra 'facet'
    attribute on the outer <browser:pages> element."""


class pages(original_pages):

    def __init__(self, _context, for_, permission,
        layer=IBrowserRequest, class_=None,
        allowed_interface=None, allowed_attributes=None,
        facet=None):
        original_pages.__init__(self, _context, for_, permission,
            layer=layer, class_=class_,
            allowed_interface=allowed_interface,
            allowed_attributes=allowed_attributes)
        self.facet = facet

    def page(self, _context, name, attribute='__call__', template=None,
             menu=None, title=None, facet=None):
        if facet is None and self.facet is not None:
            facet = self.facet
        page(_context, name=name, attribute=attribute, template=template,
             menu=menu, title=title, facet=facet, **(self.opts))


class IEditFormDirective(
    zope.app.form.browser.metadirectives.IEditFormDirective,
    IAssociatedWithAFacet):
    """Edit form browser:editform directive, extended to have an extra
    'facet' attribute."""


class EditFormDirective(
    zope.app.form.browser.metaconfigure.EditFormDirective):

    # This makes 'facet' a valid attribute for the directive.
    facet = None

    def __call__(self):
        # self.bases will be a tuple of base classes for this view.
        # So, insert a new base-class containing the facet name attribute.
        if self.facet is not None:
            cdict = {'__launchpad_facetname__': self.facet}
            new_class = type('SimpleLaunchpadViewClass', (), cdict)
            self.bases += (new_class, )

        zope.app.form.browser.metaconfigure.EditFormDirective.__call__(self)


class IAddFormDirective(
    zope.app.form.browser.metadirectives.IAddFormDirective,
    IAssociatedWithAFacet):
    """Edit form browser:addform directive, extended to have an extra
    'facet' attribute."""


class AddFormDirective(
    zope.app.form.browser.metaconfigure.AddFormDirective):

    # This makes 'facet' a valid attribute for the directive.
    facet = None

    def __call__(self):
        # self.bases will be a tuple of base classes for this view.
        # So, insert a new base-class containing the facet name attribute.
        if self.facet is not None:
            cdict = {'__launchpad_facetname__': self.facet}
            new_class = type('SimpleLaunchpadViewClass', (), cdict)
            self.bases += (new_class, )

        zope.app.form.browser.metaconfigure.AddFormDirective.__call__(self)


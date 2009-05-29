# (c) Canonical Software Ltd. 2004-2007, all rights reserved.

__metaclass__ = type

import inspect

import zope.app.form.browser.metaconfigure
import zope.app.form.browser.metadirectives
import zope.app.publisher.browser.metadirectives
import zope.configuration.config
from zope.app.component.metaconfigure import (
    handler, PublicPermission, utility, view)
from zope.app.file.image import Image
from zope.app.pagetemplate.engine import TrustedEngine
from zope.app.publisher.browser.viewmeta import (
    page as original_page, pages as original_pages)
from zope.component import getUtility
from zope.component.zcml import adapter
from zope.configuration.fields import (
    GlobalInterface, GlobalObject, Path, PythonIdentifier, Tokens)
from zope.interface import Interface, implements
from zope.publisher.interfaces.browser import (
    IBrowserPublisher, IBrowserRequest, IDefaultBrowserLayer)
from zope.publisher.interfaces.xmlrpc import IXMLRPCRequest
from zope.schema import TextLine
from zope.security.checker import Checker, CheckerPublic
from zope.security.interfaces import IPermission
from zope.security.permission import Permission
from zope.security.proxy import ProxyFactory

from zope.app.component.contentdirective import ClassDirective

from zope.security.zcml import IPermissionDirective

from canonical.launchpad.layers import FeedsLayer
from canonical.launchpad.webapp.interfaces import (
    IApplicationMenu, IAuthorization, ICanonicalUrlData, IContextMenu,
    IFacetMenu, INavigationMenu)
from canonical.launchpad.webapp.publisher import RenamedView


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

    class_ = GlobalObject(title=u'class', required=False)

    provides = GlobalObject(
        title=u'interface this utility provides',
        required=True)

    component = GlobalObject(title=u'component', required=False)


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
                    raise RuntimeError(
                        "unrecognised discriminator name", name)

class SecuredUtilityDirective:

    def __init__(self, _context, provides, class_=None, component=None):
        if class_ is not None:
            assert component is None, "Both class and component specified"
            self.component = class_()
        else:
            assert component is not None, \
                    "Neither class nor component specified"
            self.component = component
        self._context = _context
        self.provides = provides
        self.permission_collector = PermissionCollectingContext()
        self.contentdirective = ClassDirective(
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

    rootsite = PythonIdentifier(
        title=u"Name of the site this URL has as its root."
               "None for 'use the request'.",
        required=False)


class IGlueDirective(Interface):
    """ZCML glue to register some classes perform an action.

    For each class in the classes list, found in the specified module, the
    handler will hookup the class to do something.  Since this is a fairly
    generic mechanism, what that 'something' is isn't important.
    """
    module = GlobalObject(
        title=u"Module in which the classes are found."
        )

    classes = Tokens(
        value_type=PythonIdentifier(),
        title=u"Space separated list of classes to register.",
        required=True
        )


class IMenusDirective(IGlueDirective):
    """Hook up facets and menus."""


class INavigationDirective(IGlueDirective):
    """Hook up traversal etc."""


class IFeedsDirective(IGlueDirective):
    """Hook up feeds."""


class IFaviconDirective(Interface):

    for_ = GlobalObject(
        title=u"Specification of the object that has this favicon",
        required=True
        )

    file = Path(
        title=u"Path to the image file",
        required=True
        )


def menus(_context, module, classes):
    """Handler for the `IMenusDirective`."""
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    menutypes = [IFacetMenu, IApplicationMenu, IContextMenu, INavigationMenu]
    applicationmenutypes = [IApplicationMenu, INavigationMenu]
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


def feeds(_context, module, classes):
    """Handler for the `IFeedsDirective`."""
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))

    for feedclassname in classes:
        feedclass = getattr(module, feedclassname)

        for_ = feedclass.usedfor

        feedname = feedclass.feedname

        atom_name = '%s.atom' % feedname
        html_fragment_name = '%s.html' % feedname
        javascript_name = '%s.js' % feedname

        layer = FeedsLayer

        for name in atom_name, html_fragment_name, javascript_name:
            original_page(_context, name, PublicPermission, for_,
                          layer=layer, class_=feedclass)


def navigation(_context, module, classes):
    """Handler for the `INavigationDirective`."""
    if not inspect.ismodule(module):
        raise TypeError("module attribute must be a module: %s, %s" %
                        module, type(module))
    for navclassname in classes:
        navclass = getattr(module, navclassname)

        # These are used for the various ways we register a navigation
        # component.
        factory = [navclass]
        for_ = [navclass.usedfor]

        # Register the navigation as the traversal component.
        layer = IDefaultBrowserLayer
        provides = IBrowserPublisher
        name = ''
        view(_context, factory, layer, name, for_,
                permission=PublicPermission, provides=provides,
                allowed_interface=[IBrowserPublisher])
        #view(_context, factory, layer, name, for_,
        #     permission=PublicPermission, provides=provides)

        # Also register the navigation as a traversal component for XMLRPC.
        xmlrpc_layer = IXMLRPCRequest
        view(_context, factory, xmlrpc_layer, name, for_,
             permission=PublicPermission, provides=provides)


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

    # Use the whatever is in the request.
    rootsite = None

    @property
    def path(self):
        return self._compiled_path_expression(self._expression_context)


def url(_context, for_, path_expression=None, urldata=None,
        attribute_to_parent=None, parent_utility=None, rootsite=None):
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
        compiled_path_expression = TrustedEngine.compile(path_expression)

    # Dead chicken for the namespace gods.
    rootsite_ = rootsite

    if urldata:
        CanonicalUrlData = urldata
    elif attribute_to_parent:
        class CanonicalUrlData(CanonicalUrlDataBase):
            _for = for_
            _compiled_path_expression = compiled_path_expression
            rootsite = rootsite_
            @property
            def inside(self):
                return getattr(self.context, attribute_to_parent)
    else:
        class CanonicalUrlData(CanonicalUrlDataBase):
            _for = for_
            _compiled_path_expression = compiled_path_expression
            rootsite = rootsite_
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
         layer=IDefaultBrowserLayer, template=None, class_=None,
         allowed_interface=None, allowed_attributes=None,
         attribute='__call__', menu=None, title=None,
         facet=None
         ):
    """Like the standard 'page' directive, but with an added 'facet' optional
    argument.

    If a facet is specified, then it will be available from the view class
    as __launchpad_facetname__.
    """
    facet = facet or getattr(_context, 'facet', None)
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
        layer=IDefaultBrowserLayer, class_=None,
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


class IRenamedPageDirective(Interface):
    """Schema for the browser:renamed-page directive.

    Use this directive to do redirects instead of the classic way of putting a
    redirect method in a view, hooked in by a browser:page directive.
    """

    for_ = GlobalObject(
        title=u"Specification of the object that has the renamed page",
        required=True )

    layer = GlobalInterface(
        title=u"The layer the renamed page is in.",
        description=u"""
        A skin is composed of layers. It is common to put skin
        specific views in a layer named after the skin. If the 'layer'
        attribute is not supplied, it defaults to 'default'.""",
        required=False)

    name = zope.schema.TextLine(
        title=u"The name of the old page.",
        description=u"The name shows up in URLs/paths. For example 'foo'.",
        required=True)

    new_name = zope.schema.TextLine(
        title=u"The name the page was renamed to.",
        description=u"The name shows up in URLs/paths. For example 'foo'.",
        required=True)

    rootsite = PythonIdentifier(
        title=u"Name of the site this URL has as its root."
               "None for 'use the request'.",
        required=False)


def renamed_page(_context, for_, name, new_name, layer=IDefaultBrowserLayer,
                 rootsite=None):
    """Will provide a `RedirectView` that will redirect to the new_name."""
    def renamed_factory(context, request):
        return RenamedView(
            context, request, new_name=new_name, rootsite=rootsite)

    _context.action(
        discriminator = ('view', for_, name, IBrowserRequest, layer),
        callable = handler,
        args = (
            'provideAdapter',
            (for_, layer), Interface, name, renamed_factory, _context.info))


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
        facet = self.facet or getattr(self._context, 'facet', None)
        if facet is not None:
            cdict = {'__launchpad_facetname__': facet}
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
        facet = self.facet or getattr(self._context, 'facet', None)
        if facet is not None:
            cdict = {'__launchpad_facetname__': facet}
            new_class = type('SimpleLaunchpadViewClass', (), cdict)
            self.bases += (new_class, )

        zope.app.form.browser.metaconfigure.AddFormDirective.__call__(self)


class IGroupingFacet(IAssociatedWithAFacet):
    """Grouping directive that just has a facet attribute."""


class GroupingFacet(zope.configuration.config.GroupingContextDecorator):
    """Grouping facet directive."""


class ISchemaDisplayDirective(
    zope.app.form.browser.metadirectives.ISchemaDisplayDirective,
    IAssociatedWithAFacet):
    """Schema display directive with added 'facet' attribute."""


class SchemaDisplayDirective(
    zope.app.form.browser.metaconfigure.SchemaDisplayDirective):

    # This makes 'facet' a valid attribute for the directive.
    facet = None

    def __call__(self):
        # self.bases will be a tuple of base classes for this view.
        # So, insert a new base-class containing the facet name attribute.
        facet = self.facet or getattr(self._context, 'facet', None)
        if facet is not None:
            cdict = {'__launchpad_facetname__': facet}
            new_class = type('SimpleLaunchpadViewClass', (), cdict)
            self.bases += (new_class, )

        zope.app.form.browser.metaconfigure.SchemaDisplayDirective.__call__(
            self)


class IDefineLaunchpadPermissionDirective(IPermissionDirective):

    access_level = TextLine(
        title=u"Access level", required=False,
        description=u"Either read or write")


class ILaunchpadPermission(IPermission):

    access_level = IDefineLaunchpadPermissionDirective['access_level']


class LaunchpadPermission(Permission):
    implements(ILaunchpadPermission)

    def __init__(self, id, title, access_level, description):
        assert access_level in ["read", "write"], (
            "Unknown access level (%s). Must be either read or write."
            % access_level)
        super(LaunchpadPermission, self).__init__(id, title, description)
        self.access_level = access_level


def definePermission(_context, id, title, access_level="write",
                     description=''):
    permission = LaunchpadPermission(id, title, access_level, description)
    utility(_context, ILaunchpadPermission, permission, name=id)

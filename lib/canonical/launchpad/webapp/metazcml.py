# (c) Canonical Software Ltd. 2004, all rights reserved.
#
"""Implementation of the browser:suburl and browser:traverser directives.
"""

__metaclass__ = type

import sets
from zope.interface import Interface, implements
from zope.component import queryView, getDefaultViewName, getUtility
from zope.component.interfaces import IDefaultViewName
from zope.schema import TextLine
from zope.configuration.fields import GlobalObject, PythonIdentifier, Path
from zope.security.checker import CheckerPublic
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound
from zope.app import zapi
from zope.app.component.metaconfigure import handler, adapter
from zope.app.component.interface import provideInterface
from zope.app.security.fields import Permission
from zope.app.component.fields import LayerField
from zope.app.component.metaconfigure import view, PublicPermission
from zope.app.publisher.browser.viewmeta import page
from zope.app.file.image import Image
import zope.app.publisher.browser.metadirectives

from canonical.publication import ISubURLDispatch, SubURLTraverser
from canonical.launchpad.layers import setAdditionalLayer
from canonical.launchpad.interfaces import IAuthorization
from canonical.launchpad.webapp.interfaces import ILaunchpadPrincipal

try:
    from zope.publisher.interfaces.browser import IDefaultBrowserLayer
except ImportError:
    # This code can go once we've upgraded Zope.
    from zope.publisher.interfaces.browser import IBrowserRequest
    IDefaultBrowserLayer = IBrowserRequest


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

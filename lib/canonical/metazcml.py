# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: ddc2fb34-7033-4867-8fb0-85d7f3da53d0
"""Implementation of the browser:suburl and browser:traverser directives.
"""

__metaclass__ = type

from zope.interface import Interface, implements
from zope.schema import TextLine
from zope.configuration.fields import GlobalObject, PythonIdentifier
from zope.app.security.fields import Permission

from zope.component import queryView, getDefaultViewName, getUtility
from zope.app.component.metaconfigure import view, PublicPermission
from zope.security.checker import CheckerPublic
from zope.publisher.interfaces.browser import IBrowserRequest
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound

from canonical.publication import ISubURLDispatch


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


class SubURLDispatcher:
    implements(ISubURLDispatch)

    def __init__(self, context, request):
        # We're not bothered about giving the app-level component any
        # context or request information.
        # In future, we may use the context to provide a __parent__ for
        # the app-level component.
        # Perhaps the zcml directive will allow us to specify an app-level
        # name too. yagni for now.
        pass

    def __call__(self):
        raise NotImplementedError

def suburl(_context, for_, name, permission=None, utility=None, class_=None):
    if utility is None and class_ is None:
        raise TypeError("Cannot specify both utility and class.")

    # XXX check that for_ implements IHasSuburls

    if class_ is not None:
        class Dispatcher(SubURLDispatcher):
            def __call__(self):
                return class_()

    if utility is not None:
        class Dispatcher(SubURLDispatcher):
            def __call__(self):
                return getUtility(utility)

    factory = [Dispatcher]
    if permission == PublicPermission:
        permission = CheckerPublic

    type = IBrowserRequest  # So we can use "type" below, for documentation.
    return view(_context, factory, type, name, [for_], permission=permission,
                provides=ISubURLDispatch)

class URLTraverse:
    """Use the operation named by _getter to traverse an app component."""

    implements(IBrowserPublisher)

    _getter = '__getitem__'

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
                return traversed_to
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


def traverse(_context, for_, getter=None, function=None, permission=None):
    if getter is not None and function is not None:
        raise TypeError("Cannot specify both getter and function")
    if getter is None and function is None:
        raise TypeError("Must specify either getter or function")

    type = IBrowserRequest
    name = ''
    provides = IBrowserPublisher

    if getter:
        class URLTraverseGetter(URLTraverse):
            __used_for__ = for_
            _getter = getter

        factory = [URLTraverseGetter]

    if function:
        class URLTraverseFunction(URLTraverseByFunction):
            __used_for__ = for_
            _function = staticmethod(function)

        factory = [URLTraverseFunction]

    return view(_context, factory, type, name, [for_], permission=permission,
                provides=provides)

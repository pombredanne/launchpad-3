from canonical.rosetta.interfaces import IProject
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.publisher.interfaces import NotFound
from zope.component import queryView, getDefaultViewName
from zope.interface import implements

class URLTraverseProject:
    implements(IBrowserPublisher)

    __used_for__ = IProject

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def publishTraverse(self, request, name):
        """Search for views, and if no view is found, PO templates."""
        # TODO: consider replacing this with a custom zcml directive.
        view = queryView(self.context, name, request)
        if view is None:
            try:
                template = self.context.poTemplate(name)
            except KeyError:
                raise NotFound(self.context, name)
            else:
                return template
        else:
            return view

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


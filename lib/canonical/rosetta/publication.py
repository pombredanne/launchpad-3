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
        if view is not None:
            return view

        # try a template
        # XXX: this has to go away after the conference
        #      (as it may silently hide templates with the same name)
        for product in self.context.products:
            try:
                template = product.poTemplate(name)
            except KeyError:
                continue
            else:
                return template

        # nay sir
        raise NotFound(self.context, name)

    def browserDefault(self, request):
        view_name = getDefaultViewName(self.context, request)
        return self.context, (view_name,)


__all__ = ['TraverseWithGet']


from urllib import unquote
from zope.component import adapts
from zope.interface import implements
from zope.publisher.interfaces import IPublishTraverse, NotFound
from zope.publisher.interfaces.browser import IDefaultBrowserLayer

from canonical.lazr.rest.example.interfaces import IHasGet


class TraverseWithGet:
    """A simple IPublishTraverse that uses the get() method."""
    implements(IPublishTraverse)
    adapts(IHasGet, IDefaultBrowserLayer)

    def __init__(self, context, request):
        self.context = context

    def publishTraverse(self, request, name):
        name = unquote(name)
        value = self.context.get(name)
        # Set __parent__ so that absoluteURL will work.
        value.__parent__ = self.context
        if value is None:
            raise NotFound(self, name)
        return value


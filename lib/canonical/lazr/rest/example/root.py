__all__ = ['Cookbook',
           'CookbookSet',
           'ExampleServiceRootResource',
           'TestWebServiceObject']

from zope.interface import implements
from zope.traversing.browser.interfaces import IAbsoluteURL

from canonical.lazr.rest import ServiceRootResource
from canonical.lazr.rest.example.interfaces import (
    ICookbook, ICookbookSet, IHasGet)


class TestWebServiceObject:
    pass

class Cookbook(TestWebServiceObject):
    implements(ICookbook, IAbsoluteURL)
    def __init__(self, name):
        self.name = name

    @property
    def __name__(self):
        return self.name


class CookbookSet(TestWebServiceObject):
    implements(ICookbookSet, IAbsoluteURL)

    def __init__(self, cookbooks):
        self.cookbooks = cookbooks

    def getCookbooks(self):
        return self.cookbooks

    def get(self, name):
        match = [c for c in self.cookbooks if c.name == name]
        if len(match) > 0:
            return match[0]
        return None

    __name__ = "cookbooks"


C1 = Cookbook(u"Mastering the Art of French Cooking")
C2 = Cookbook(u"The Joy of Cooking")
C3 = Cookbook(u"James Beard's American Cookery")
COOKBOOK_SET = CookbookSet([C1, C2, C3])


class RootAbsoluteURL:
     """A basic, extensible implementation of IAbsoluteURL."""
     implements(IAbsoluteURL)

     def __init__(self, context, request):
         self.context = context
         self.request = request

     def __str__(self):
         return "http://api.launchpad.dev/beta/"

     __call__ = __str__

class ExampleServiceRootResource(ServiceRootResource):
    implements(IHasGet, IAbsoluteURL)
    top_level_names = {
        'cookbooks': COOKBOOK_SET
        }

    def get(self, name):
        return self.top_level_names.get(name)

    __name__ = ''

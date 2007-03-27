# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import cgi

from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.launchpad.webapp.interfaces import IBreadcrumbProvider
from canonical.launchpad.webapp import canonical_url, LaunchpadView


class DynMenuLink:

    def __init__(self, context, name, text, submenu=None,
        contextsubmenu=False):
        self.baseurl = canonical_url(context)
        self.name = name
        self.text = text
        self.submenu = submenu
        self.contextsubmenu = contextsubmenu

    def render(self):
        basepath = self.baseurl
        L = []
        if self.submenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata/%s">' % (basepath, self.submenu))
        elif self.contextsubmenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata">' % self.baseurl)
        else:
            L.append('<li class="item">')
        L.append('<a href="%s/%s">' %  (basepath, self.name))
        L.append(self.renderText())
        L.append('</a>')
        L.append('</li>')
        return ''.join(L)

    def renderText(self):
        escaped_text = cgi.escape(self.text)
        escaped_text = escaped_text.replace('...', '&hellip;')
        return escaped_text


class DynMenu(LaunchpadView):

    implements(IBrowserPublisher)

    def __init__(self, context, request):
        self.names = []
        LaunchpadView.__init__(self, context, request)

    def getBreadcrumbText(self, obj):
        breadcrumbprovider = queryMultiAdapter(
            (obj, self.request), IBreadcrumbProvider, default=None)
        if breadcrumbprovider is None:
            return None
        else:
            return breadcrumbprovider.breadcrumb()

    def makeBreadcrumbLink(self, context):
        text = self.getBreadcrumbText(context)
        assert text is not None
        return DynMenuLink(context, '', text, contextsubmenu=True)

    def makeLink(self, text, context=None, page='', submenu=None,
        contextsubmenu=False):
        if context is None:
            context = self.context
        return DynMenuLink(context, page, text, submenu=submenu,
            contextsubmenu=contextsubmenu)

    def renderMenu(self, menu):
        L = []
        L.append('<ul class="menu">')
        for item in menu:
            L.append(item.render())
        L.append('</ul>')
        return u'\n'.join(L)

    def render(self):
        """Assume only one type of menu, and render it."""
        if self.names:
            raise NotFoundError(names[-1])
        return self.renderMenu(self.mainMenu())

    def mainMenu(self):
        raise NotImplementedError('Subclasses must provide mainMenu.')

    # The following two zope methods publishTraverse and browserDefault
    # allow this view class to take control of traversal from this point
    # onwards.  Traversed names just end up in self.names.

    def publishTraverse(self, request, name):
        """Traverse to the given name."""
        self.names.append(name)
        return self

    def browserDefault(self, request):
        return self, ()


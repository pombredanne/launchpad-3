# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type

import cgi

from zope.component import queryMultiAdapter
from zope.interface import implements
from zope.publisher.interfaces.browser import IBrowserPublisher

from canonical.launchpad.webapp.interfaces import (
    IBreadcrumbProvider, NotFoundError)
from canonical.launchpad.webapp import canonical_url, LaunchpadView


class DynMenuLink:

    def __init__(self, context, name, text, submenu=None,
        contextsubmenu=False, target=None):
        self.baseurl = canonical_url(context)
        if target is not None:
            self.targeturl = canonical_url(target)
        else:
            self.targeturl = self.baseurl
        self.name = name
        self.text = text
        self.submenu = submenu
        self.contextsubmenu = contextsubmenu

    def render(self):
        baseurl = self.baseurl
        L = []
        if self.submenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata/%s">' % (baseurl, self.submenu))
        elif self.contextsubmenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata">' % self.baseurl)
        else:
            L.append('<li class="item">')

        L.append('<a href="%s/%s">' %  (self.targeturl, self.name))
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

    menus = {'': 'mainMenu'}

    def render(self):
        if len(self.names) > 1:
            raise NotFoundError(self.names[-1])

        if self.names:
            [name] = self.names
        else:
            name = ''

        renderer_name = self.menus.get(name)
        if renderer_name is None:
            raise NotFoundError(name)
        else:
            renderer = getattr(self, renderer_name)
            return self.renderMenu(renderer())

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
        contextsubmenu=False, target=None):
        if context is None:
            context = self.context
        return DynMenuLink(context, page, text, submenu=submenu,
            contextsubmenu=contextsubmenu, target=target)

    def renderMenu(self, menu):
        L = []
        L.append('<ul class="menu">')
        for item in menu:
            L.append(item.render())
        L.append('</ul>')
        return u'\n'.join(L)

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


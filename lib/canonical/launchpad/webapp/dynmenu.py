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


def neverempty(fn):
    """Method decorator to declare that this menu will always have
    at least one item.
    """
    fn.__dynmenu_neverempty__ = True
    return fn


class DynMenuLink:

    no_target_given = object()

    def __init__(self, context, name, text, submenu=None,
            contextsubmenu=False, target=no_target_given):
        self.baseurl = canonical_url(context)
        is_linked = True
        if target is DynMenuLink.no_target_given:
            self.targeturl = self.baseurl
        elif target is None:
            self.targeturl = None
            is_linked = False
        elif isinstance(target, basestring):
            self.targeturl = target
        else:
            self.targeturl = canonical_url(target)
        self.is_linked =  is_linked
        self.name = name
        self.text = text
        self.submenu = submenu
        self.contextsubmenu = contextsubmenu

    def render(self):
        baseurl = self.baseurl
        L = []
        is_container = False
        if self.submenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata/%s">' % (baseurl, self.submenu))
            is_container = True
        elif self.contextsubmenu:
            L.append('<li class="item container" lpm:mid="%s/+menudata">' % self.baseurl)
            is_container = True
        else:
            L.append('<li class="item">')

        if self.is_linked:
            if is_container:
                L.append('<a href="%s/%s" class="container">'
                         % (self.targeturl, self.name))
            else:
                L.append('<a href="%s/%s">' %  (self.targeturl, self.name))
        else:
            if is_container:
                L.append('<span class="unlinked container">')
            else:
                L.append('<span class="unlinked">')
        L.append(self.renderText())
        if self.is_linked:
            L.append('</a>')
        else:
            L.append('</span>')
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
        renderer = self.getSubmenuMethod(name)
        if renderer is None:
            raise NotFoundError(name)
        else:
            return self.renderMenu(renderer())

    def getBreadcrumbText(self, obj):
        breadcrumbprovider = queryMultiAdapter(
            (obj, self.request), IBreadcrumbProvider,
            name='breadcrumb', default=None)
        if breadcrumbprovider is None:
            return None
        else:
            return breadcrumbprovider.breadcrumb()

    def getSubmenuMethod(self, submenu_name, context=None):
        """Return submenu method, or None if there isn't one."""
        if context is None or context is self.context:
            submenu = self
        else:
            submenu = queryMultiAdapter(
                (context, self.request), name='+menudata')
            if submenu is None:
                return None
        method_name = submenu.menus.get(submenu_name)
        if method_name is None:
            return None
        return getattr(submenu, method_name)

    def submenuHasItems(self, submenu_name, context=None):
        submenu_method = self.getSubmenuMethod(submenu_name, context=context)
        if submenu_method is None:
            return False
        if getattr(submenu_method, '__dynmenu_neverempty__', False):
            return True
        submenu = submenu_method()
        assert submenu is not None, "submenu must be a generator"
        try:
            submenu.next()
        except StopIteration:
            return False
        else:
            return True

    def makeBreadcrumbLink(self, context):
        text = self.getBreadcrumbText(context)
        assert text is not None
        contextsubmenu = self.submenuHasItems('', context)
        return DynMenuLink(
            context, '', text, contextsubmenu=contextsubmenu)

    def makeLink(self, text, context=None, page='', submenu=None,
            target=DynMenuLink.no_target_given):
        if context is None:
            context = self.context
        if submenu is not None:
            if not self.submenuHasItems(submenu, context):
                submenu = None
        return DynMenuLink(context, page, text, submenu=submenu, target=target)

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


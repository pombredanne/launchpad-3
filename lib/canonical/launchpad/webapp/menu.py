# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Menus and facets."""

__metaclass__ = type
__all__ = ['nearest_menu', 'FacetMenu', 'ExtraFacetMenu',
           'ApplicationMenu', 'ExtraApplicationMenu',
           'Link', 'DefaultLink']

import urlparse
from zope.interface import implements
from zope.component import getDefaultViewName
from canonical.launchpad.interfaces import (
    IMenuBase, IFacetMenu, IExtraFacetMenu, IApplicationMenu,
    IExtraApplicationMenu, ILink, IDefaultLink
    )
from canonical.launchpad.webapp.publisher import (
    canonical_url, canonical_url_iterator
    )

def nearest_menu(obj, menuinterface):
    """Return the menu adapter of the nearest object up the canonical url chain
    that has such a menu defined for it.

    This might be the menu for the object given as an argument.

    Return None if there is no object that has such a menu in the url chain.

    menuinterface will typically be one of IFacetMenu and IExtraFacetMenu.
    """
    for current_obj in canonical_url_iterator(obj):
        facetmenu = menuinterface(current_obj, None)
        if facetmenu is not None:
            return facetmenu
    return None


class Link:
    """General links that aren't default links."""
    implements(ILink)

    def __init__(self, target, text, summary=None, linked=True):
        """Create a new link to 'target' with 'text' as the link text.

        If the 'linked' argument is set to False, then the link will
        be disabled.

        If the 'linked' argument is set to True, then the link will be
        enabled, provided that it does not point to the current page.
        """
        self.target = target
        self.text = text
        self.summary = summary
        self.name = None
        self.selected = False
        self.linked = linked
        self.url = None


class DefaultLink(Link):
    """Link that is selected when no other links are."""
    implements(IDefaultLink)


class MenuBase:
    """Base class for facets and menus."""

    implements(IMenuBase)

    links = None
    _baseclassname = 'MenuBase'

    def __init__(self, context, request=None):
        # The attributes self.context and self.request are defined in
        # IFacetMenu.
        self.context = context
        self.request = request

    def __iter__(self):
        """See IFacetMenu."""
        assert self.links is not None, (
            'Subclasses of %s must provide self.links' % self._baseclassname)
        contexturlobj = Url(canonical_url(self.context, self.request))
        if self.request is None:
            requesturlobj = None
        else:
            requesturlobj = Url(self.request.getURL(),
                                self.request.get('QUERY_STRING'))
            # If the default view name is being used, we will want the url
            # without the default view name.
            defaultviewname = getDefaultViewName(self.context, self.request)
            if requesturlobj.pathnoslash.endswith(defaultviewname):
                requesturlobj = Url(self.request.getURL(1),
                                    self.request.get('QUERY_STRING'))

        output_links = []
        default_link = None
        selected_links = set()

        for linkname in self.links:
            method = getattr(self, linkname)
            link = method()
            link.name = linkname
            targeturlobj = Url(link.target)
            if targeturlobj.addressingscheme:
                link.url = link.target
            elif link.target.startswith('/'):
                link.url = '%s%s' % (contexturlobj.host, link.target)
            else:
                link.url = '%s%s%s' % (
                    contexturlobj.host, contexturlobj.pathslash, link.target)
            isdefaultlink = IDefaultLink.providedBy(link)
            if requesturlobj is not None:
                linkurlobj = Url(link.url)
                if requesturlobj.is_inside(linkurlobj):
                    selected_links.add(link)
                if requesturlobj == linkurlobj:
                    link.linked = False
            if isdefaultlink:
                assert default_link is None, (
                    'There can be only one DefaultLink')
                default_link = link
            output_links.append(link)
        # If we have many selected_links, make selected_link the one that
        # is inside the rest.  If we have just one selected link, that's easy:
        # that link is selected.  If we have no selected links, then use the
        # default link.
        L = sorted(selected_links, key=lambda link: link.url, reverse=True)
        L = L[:1]
        if L:
            selected_link = L[0]
            selected_link.selected = True
        elif (default_link is not None and
              requesturlobj is not None and
              requesturlobj.is_inside(contexturlobj)):
            default_link.selected = True
        return iter(output_links)


class FacetMenu(MenuBase):
    """Base class for facet menus."""

    implements(IFacetMenu)

    _baseclassname = 'FacetMenu'


class ExtraFacetMenu(MenuBase):
    """Base class for extra facet menus."""

    implements(IExtraFacetMenu)

    _baseclassname = 'ExtraFacetMenu'


class ApplicationMenu(MenuBase):
    """Base class for application menus."""

    implements(IApplicationMenu)

    _baseclassname = 'ApplicationMenu'


class ExtraApplicationMenu(MenuBase):
    """Base class for extra application menus."""

    implements(IExtraApplicationMenu)

    _baseclassname = 'ExtraApplicationMenu'


class Url:
    """A class for url operations."""

    def __init__(self, url, query=None):
        self.url = url
        if query is not None:
            self.url += '?%s' % query
        urlparts = iter(urlparse.urlparse(self.url))
        self.addressingscheme = urlparts.next()
        self.networklocation = urlparts.next()
        self.path = urlparts.next()
        if self.path.endswith('/'):
            self.pathslash = self.path
            self.pathnoslash = self.path[:-1]
        else:
            self.pathslash = self.path + '/'
            self.pathnoslash = self.path
        self.parameters = urlparts.next()
        self.query = urlparts.next()
        self.fragmentids = urlparts.next()

    @property
    def host(self):
        """Returns the addressing scheme and network location."""
        return '%s://%s' % (self.addressingscheme, self.networklocation)

    def __repr__(self):
        return '<Url %s>' % self.url

    def is_inside(self, otherurl):
        return (self.host == otherurl.host and
                self.pathslash.startswith(otherurl.pathslash))

    def __eq__(self, otherurl):
        return (otherurl.host == self.host and
                otherurl.pathslash == self.pathslash and
                otherurl.query == self.query)

    def __ne__(self, otherurl):
        return not self.__eq__(self, otherurl)

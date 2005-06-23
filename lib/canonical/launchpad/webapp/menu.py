# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Menus and facets."""

__metaclass__ = type
__all__ = ['nearest_menu', 'FacetMenu', 'ExtraFacetMenu',
           'ApplicationMenu', 'Link', 'DefaultLink']

import urlparse
from zope.interface import implements
from canonical.launchpad.interfaces import (
    IMenuBase, IFacetMenu, IExtraFacetMenu, IApplicationMenu,
    ILink, IDefaultLink
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

    def __init__(self, target, text, summary=None):
        self.target = target
        self.text = text
        self.summary = summary
        self.name = None
        self.selected = False
        self.linked = True
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
        contexturl = canonical_url(self.context, self.request)
        if self.request is None:
            requesturl = None
        else:
            requesturl = self.request.getURL()

        output_links = []
        default_link = None
        selected_link = None

        for linkname in self.links:
            method = getattr(self, linkname)
            link = method()
            link.name = linkname
            link.url = '%s/%s' % (contexturl, link.target)
            if requesturl is not None:
                if url2_is_inside_url1(link.url, requesturl):
                    link.selected = True
                    assert selected_link is None, (
                        'There can be only one selected link')
                    selected_link = link
                # TODO: compute whether the link is linked.  For now, all
                #       links are linked.
            if IDefaultLink.providedBy(link):
                assert default_link is None, (
                    'There can be only one DefaultLink')
                default_link = link
            output_links.append(link)
        if (selected_link is None and
            default_link is not None and
            requesturl is not None and
            url2_is_inside_url1(contexturl, requesturl)):
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


def url2_is_inside_url1(url1, url2):
    addressingscheme, networklocation, path, parameters, query, fragmentids = (
        urlparse.urlparse(url1))
    path1 = path
    addressingscheme, networklocation, path, parameters, query, fragmentids = (
        urlparse.urlparse(url2))
    path2 = path
    if not path1.endswith('/'):
        path1 += '/'
    if not path2.endswith('/'):
        path2 += '/'
    return path2.startswith(path1)

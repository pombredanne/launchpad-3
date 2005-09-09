# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Menus and facets."""

__metaclass__ = type
__all__ = ['nearest_menu', 'FacetMenu', 'ApplicationMenu', 'Link']

import urlparse
from zope.interface import implements
from zope.component import getDefaultViewName
from canonical.launchpad.interfaces import (
    IMenuBase, IFacetMenu, IApplicationMenu, IFacetLink, ILink
    )
from canonical.launchpad.webapp.publisher import (
    canonical_url, canonical_url_iterator
    )

def nearest_menu(obj, menuinterface):
    """Return the menu adapter of the nearest object up the canonical url chain
    that has such a menu defined for it.

    This might be the menu for the object given as an argument.

    Return None if there is no object that has such a menu in the url chain.

    menuinterface will typically be IFacetMenu.
    """
    for current_obj in canonical_url_iterator(obj):
        facetmenu = menuinterface(current_obj, None)
        if facetmenu is not None:
            return facetmenu
    return None


class Link:
    """General links that aren't default links.

    This is used for all links, not just facet links.  The class implements
    IFacetLink because it can be used for facet links.
    """
    implements(IFacetLink)

    # These attributes are set by the menus infrastructure.
    name = None
    url = None
    linked = True
    selected = False

    def __init__(self, target, text, summary=None, icon=None, enabled=True):
        """Create a new link to 'target' with 'text' as the link text.

        'target' is a relative path, an absolute path, or an absolute url.

        'text' is the link text of this link.

        'summary' is the summary text of this link.

        The 'enabled' argument is boolean for whether this link is enabled.

        The 'icon' is the name of the icon to use, or None if there is no
        icon.
        """
        self.target = target
        self.text = text
        self.summary = summary
        self.icon = icon
        self.enabled = enabled


class MenuBase:
    """Base class for facets and menus."""

    implements(IMenuBase)

    links = None
    _baseclassname = 'MenuBase'

    def __init__(self, context, request=None):
        # The attributes self.context and self.request are defined in
        # IMenuBase.
        self.context = context
        self.request = request
        # XXX: SteveA 2005-09-09, quick hack, awaiting more comprehensive
        # refactor.
        self.published_context = None

    def _get_link(self, name):
        method = getattr(self, name)
        link = method()
        # The link need only provide ILinkData.  We need an ILink so that
        # we can set attributes on it like 'name' and 'url' and 'linked'.
        return ILink(link)

    def __iter__(self):
        """See IMenu."""
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
            # XXX: the problem here is that we're getting the default view
            #      name of the facet menu's context, not of the actual
            #      published object's context!
            #      plan: make the tales stuff responsible for passing
            #            in a string that is the requesturl.
            #     SteveAlexander, 2005-09-09
            if self.published_context is None:
                published_context = self.context
            else:
                published_context = self.published_context
            defaultviewname = getDefaultViewName(
                published_context, self.request)
            if requesturlobj.pathnoslash.endswith(defaultviewname):
                requesturlobj = Url(self.request.getURL(1),
                                    self.request.get('QUERY_STRING'))

        for linkname in self.links:
            link = self._get_link(linkname)
            link.name = linkname

            # Set the .url attribute of the link, using the menu's context.
            targeturlobj = Url(link.target)
            if targeturlobj.addressingscheme:
                link.url = link.target
            elif link.target.startswith('/'):
                link.url = '%s%s' % (contexturlobj.host, link.target)
            else:
                link.url = '%s%s%s' % (
                    contexturlobj.host, contexturlobj.pathslash, link.target)

            # Make the link unlinked if it is a link to the current page.
            if requesturlobj is not None:
                linkurlobj = Url(link.url)
                if requesturlobj == linkurlobj:
                    link.linked = False
            yield link


class FacetMenu(MenuBase):
    """Base class for facet menus."""

    implements(IFacetMenu)

    _baseclassname = 'FacetMenu'

    # See IFacetMenu.
    defaultlink = None

    def _get_link(self, name):
        return IFacetLink(MenuBase._get_link(self, name))

    def iterlinks(self, selectedfacetname=None):
        """See IFacetMenu."""
        if selectedfacetname is None:
            selectedfacetname = self.defaultlink
        for link in MenuBase.__iter__(self):
            if (selectedfacetname is not None and
                selectedfacetname == link.name):
                link.selected = True
            yield link

    def __iter__(self):
        return self.iterlinks()


class ApplicationMenu(MenuBase):
    """Base class for application menus."""

    implements(IApplicationMenu)

    _baseclassname = 'ApplicationMenu'


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

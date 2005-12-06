# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Menus and facets."""

__metaclass__ = type
__all__ = ['nearest_menu', 'FacetMenu', 'ApplicationMenu', 'ContextMenu',
           'Link', 'LinkData', 'FacetLink', 'MenuLink', 'Url', 'structured',
           'enabled_with_permission']

import urlparse
import cgi
from zope.interface import implements
from canonical.lp import decorates
from canonical.launchpad.helpers import check_permission
from canonical.launchpad.interfaces import (
    IMenuBase, IFacetMenu, IApplicationMenu, IContextMenu,
    IFacetLink, ILink, ILinkData, IStructuredString
    )
from canonical.launchpad.webapp.publisher import (
    canonical_url, canonical_url_iterator, UserAttributeCache
    )


class structured:

    implements(IStructuredString)

    def __init__(self, text, *replacements, **kwreplacements):
        self.text = text
        if replacements and kwreplacements:
            raise TypeError(
                "You must provide either positional arguments or keyword "
                "arguments to structured(), not both.")
        if replacements:
            self.escapedtext = text % tuple(
                cgi.escape(replacement) for replacement in replacements)
        elif kwreplacements:
            self.escapedtext = text % dict(
                (key, cgi.escape(value))
                for key, value in kwreplacements.iteritems())
        else:
            self.escapedtext = self.text

    def __repr__(self):
        return "<structured-string '%s'>" % self.text


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


class LinkData:
    """General links that aren't default links.

    Instances of this class just provide link data.  The class is also known
    as 'Link' to make it nice to use when defining menus.
    """
    implements(ILinkData)

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

Link = LinkData


class MenuLink:
    """Adapter from ILinkData to ILink."""
    implements(ILink)
    decorates(ILinkData, context='_linkdata')

    # These attributes are set by the menus infrastructure.
    name = None
    url = None
    linked = True

    # This attribute is used to override self.enabled when it is
    # set, without writing to the object being adapted.
    _enabled_override = None

    def __init__(self, linkdata):
        # Take a copy of the linkdata attributes.
        self._linkdata = linkdata

    def set_enabled(self, value):
        self._enabled_override = value

    def get_enabled(self):
        if self._enabled_override is None:
            return self._linkdata.enabled
        return self._enabled_override

    enabled = property(get_enabled, set_enabled)

    @property
    def escapedtext(self):
        text = self._linkdata.text
        if IStructuredString.providedBy(text):
            return text.escapedtext
        else:
            return cgi.escape(text)


class FacetLink(MenuLink):
    """Adapter from ILinkData to IFacetLink."""
    implements(IFacetLink)

    # This attribute is set by the menus infrastructure.
    selected = False


# Marker object that means 'all links are to be enabled'.
ALL_LINKS = object()


class MenuBase(UserAttributeCache):
    """Base class for facets and menus."""

    implements(IMenuBase)

    links = None
    enable_only = ALL_LINKS
    _baseclassname = 'MenuBase'
    _initialized = False
    _forbiddenlinknames = set(
        ['user', 'initialize', 'links', 'enable_only', 'iterlinks'])

    def __init__(self, context):
        # The attribute self.context is defined in IMenuBase.
        self.context = context

    def initialize(self):
        """Override this in subclasses to do initialization."""
        pass

    def _get_link(self, name):
        method = getattr(self, name)
        linkdata = method()
        # The link need only provide ILinkData.  We need an ILink so that
        # we can set attributes on it like 'name' and 'url' and 'linked'.
        return ILink(linkdata)

    def iterlinks(self, requesturl=None):
        """See IMenu."""
        if not self._initialized:
            self.initialize()
            self._initialized = True
        assert self.links is not None, (
            'Subclasses of %s must provide self.links' % self._baseclassname)
        assert isinstance(self.links, list), "self.links must be a list"
        linksset = set(self.links)
        assert not linksset.intersection(self._forbiddenlinknames), (
            "The following names may not be links: %s" %
            ', '.join(self._forbiddenlinknames))

        contexturlobj = Url(canonical_url(self.context))

        if self.enable_only is ALL_LINKS:
            enable_only = set(self.links)
        else:
            enable_only = set(self.enable_only)

        if enable_only - set(self.links):
            # There are links named in enable_only that do not exist in
            # self.links.
            raise AssertionError(
                "Links in 'enable_only' not found in 'links': %s" %
                (', '.join([name for name in enable_only - set(self.links)])))

        for linkname in self.links:
            link = self._get_link(linkname)
            link.name = linkname

            # Set the .enabled attribute of the link to False if it is not
            # in enable_only.
            if linkname not in enable_only:
                link.enabled = False

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
            if requesturl is not None:
                linkurlobj = Url(link.url)
                if requesturl == linkurlobj:
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

    def iterlinks(self, requesturl=None, selectedfacetname=None):
        """See IFacetMenu."""
        if selectedfacetname is None:
            selectedfacetname = self.defaultlink
        for link in MenuBase.iterlinks(self, requesturl=requesturl):
            if (selectedfacetname is not None and
                selectedfacetname == link.name):
                link.selected = True
            yield link


class ApplicationMenu(MenuBase):
    """Base class for application menus."""

    implements(IApplicationMenu)

    _baseclassname = 'ApplicationMenu'


class ContextMenu(MenuBase):
    """Base class for context menus."""

    implements(IContextMenu)

    _baseclassname = 'ContextMenu'


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


class enabled_with_permission:
    """Function decorator that disables the output link unless the current
    user has the given permission on the context.

    This class is instantiated by programmers who want to apply this decorator.

    Use it like:

        @enabled_with_permission('launchpad.Admin')
        def somemenuitem(self):
            return Link('+target', 'link text')

    """

    def __init__(self, permission):
        """Make a new enabled_with_permission function decorator.

        `permission` is the string permission name, like 'launchpad.Admin'.
        """
        self.permission = permission

    def __call__(self, func):
        """Called by the decorator machinery to return a decorated function.

        Returns a new function that calls the original function, gets the
        link that it returns, and depending on the permissions granted to
        the logged-in user, disables the link, before returning it to the
        called.
        """
        permission = self.permission
        def enable_if_allowed(self):
            link = func(self)
            if not check_permission(permission, self.context):
                link.enabled = False
            return link
        return enable_if_allowed


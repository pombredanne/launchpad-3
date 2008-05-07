# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Menus and facets."""

__metaclass__ = type
__all__ = [
    'enabled_with_permission',
    'escape',
    'nearest_context_with_adapter',
    'nearest_adapter',
    'structured',
    'translate_if_msgid',
    'FacetMenu',
    'ApplicationMenu',
    'ContextMenu',
    'NavigationMenu',
    'Link',
    'LinkData',
    'FacetLink',
    'MenuLink',
    ]

import cgi
from new import instancemethod

from zope.i18n import translate, Message, MessageID
from zope.interface import implements
from zope.component import getMultiAdapter, queryAdapter
from zope.security.proxy import removeSecurityProxy

from canonical.lazr import decorates

from canonical.launchpad.webapp.interfaces import (
    IApplicationMenu, IContextMenu, IFacetLink, IFacetMenu, ILink, ILinkData,
    IMenuBase, INavigationMenu, IStructuredString)
from canonical.launchpad.webapp.publisher import (
    canonical_url, canonical_url_iterator, get_current_browser_request,
    LaunchpadView, UserAttributeCache)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.uri import InvalidURIError, URI
from canonical.launchpad.webapp.vhosts import allvhosts


class structured:

    implements(IStructuredString)

    def __init__(self, text, *replacements, **kwreplacements):
        text = translate_if_i18n(text)
        self.text = text
        if replacements and kwreplacements:
            raise TypeError(
                "You must provide either positional arguments or keyword "
                "arguments to structured(), not both.")
        if replacements:
            self.escapedtext = text % tuple(
                cgi.escape(unicode(replacement))
                for replacement in replacements)
        elif kwreplacements:
            self.escapedtext = text % dict(
                (key, cgi.escape(unicode(value)))
                for key, value in kwreplacements.iteritems())
        else:
            self.escapedtext = unicode(text)

    def __repr__(self):
        return "<structured-string '%s'>" % self.text


def nearest_context_with_adapter(obj, interface):
    """Return the tuple (context, adapter) of the nearest object up the
    canonical url chain that has an adapter of the type given.

    This might be an adapter for the object given as an argument.

    Return (None, None) if there is no object that has such an adapter
    in the url chain.

    """
    for current_obj in canonical_url_iterator(obj):
        adapter = interface(current_obj, None)
        if adapter is not None:
            return (current_obj, adapter)
    return (None, None)


def nearest_adapter(obj, interface):
    """Return the adapter of the nearest object up the canonical url chain
    that has an adapter of the type given.

    This might be an adapter for the object given as an argument.

    :return None: if there is no object that has such an adapter in the url
        chain.

    This will often be used with an interface of IFacetMenu, when looking up
    the facet menu for a particular context.

    """
    context, adapter = nearest_context_with_adapter(obj, interface)
    # Will be None, None if not found.
    return adapter


class LinkData:
    """General links that aren't default links.

    Instances of this class just provide link data.  The class is also known
    as 'Link' to make it nice to use when defining menus.
    """
    implements(ILinkData)

    def __init__(self, target, text, summary=None, icon=None, enabled=True,
                 site=None, menu=None):
        """Create a new link to 'target' with 'text' as the link text.

        'target' is a relative path, an absolute path, or an absolute url.

        'text' is the link text of this link.

        'summary' is the summary text of this link.

        The 'enabled' argument is boolean for whether this link is enabled.

        The 'icon' is the name of the icon to use, or None if there is no
        icon. This is currently unused in the Actions menu, but will likely
        be used when menu links are embedded in the page (bug 5313).

        The 'site' is None for whatever the current site is, and 'main' or
        'blueprint' for a specific site.

        :param menu: The sub menu used by the page that the link represents.
        """
        self.target = target
        self.text = text
        self.summary = summary
        self.icon = icon
        self.enabled = enabled
        self.site = site
        self.menu = menu

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

    @property
    def icon_url(self):
        """The full URL of this link's associated icon, if it has one."""
        if not self.icon:
            return
        else:
            return '/@@/%s' % self.icon

    def render(self):
        """See `ILink`."""
        return getMultiAdapter(
            (self, get_current_browser_request()), name="+inline")()


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
        ['user', 'initialize', 'links', 'enable_only', 'isBetaUser',
         'iterlinks'])

    def __init__(self, context):
        # The attribute self.context is defined in IMenuBase.
        self.context = context
        self.request = None

    def initialize(self):
        """Override this in subclasses to do initialization."""
        pass

    def _get_link(self, name):
        method = getattr(self, name)
        linkdata = method()
        # The link need only provide ILinkData.  We need an ILink so that
        # we can set attributes on it like 'name' and 'url' and 'linked'.
        return ILink(linkdata)

    def _rootUrlForSite(self, site):
        """Return the root URL for the given site."""
        try:
            return URI(allvhosts.configs[site].rooturl)
        except KeyError:
            raise AssertionError('unknown site', site)

    def iterlinks(self, requesturi=None):
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

        if isinstance(self.context, LaunchpadView):
            # It's a navigation menu for a view instead of a db object. Views
            # don't have a canonical URL, they use the db object one used as
            # the context for that view.
            context = self.context.context
        else:
            context = self.context

        contexturlobj = URI(canonical_url(context))

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

        for idx, linkname in enumerate(self.links):
            link = self._get_link(linkname)
            link.name = linkname

            # Set the .enabled attribute of the link to False if it is not
            # in enable_only.
            if linkname not in enable_only:
                link.enabled = False

            # Set the .url attribute of the link, using the menu's context.
            if link.site is None:
                rootsite = contexturlobj.resolve('/')
            else:
                rootsite = self._rootUrlForSite(link.site)
            # Is the target a full URI already?
            try:
                link.url = URI(link.target)
            except InvalidURIError:
                if link.target.startswith('/'):
                    link.url = rootsite.resolve(link.target)
                else:
                    link.url = rootsite.resolve(contexturlobj.path).append(
                        link.target)

            # Make the link unlinked if it is a link to the current page.
            if requesturi is not None:
                if requesturi.ensureSlash() == link.url.ensureSlash():
                    link.linked = False

            link.sort_key = idx
            yield link


class FacetMenu(MenuBase):
    """Base class for facet menus."""

    implements(IFacetMenu)

    _baseclassname = 'FacetMenu'

    # See IFacetMenu.
    defaultlink = None

    def _filterLink(self, name, link):
        """Hook to allow subclasses to alter links based on the name used."""
        return link

    def _get_link(self, name):
        return IFacetLink(
            self._filterLink(name, MenuBase._get_link(self, name)))

    def iterlinks(self, requesturi=None, selectedfacetname=None):
        """See IFacetMenu."""
        if selectedfacetname is None:
            selectedfacetname = self.defaultlink
        for link in MenuBase.iterlinks(self, requesturi=requesturi):
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


class NavigationMenu(MenuBase):
    """Base class for navigation menus."""

    implements(INavigationMenu)

    _baseclassname = 'NavigationMenu'

    def _get_link(self, name):
        return IFacetLink(
            super(NavigationMenu, self)._get_link(name))

    def iterlinks(self, requesturi=None, selectedfacetname=None):
        """See `INavigationMenu`.

        Menus may be associated with content objects and their views. The
        state of a menu's links depends upon the requesturi (or the URL of
        the request) and whether a menu associated with a link is available.
        """
        request = get_current_browser_request()
        if requesturi is None:
            requesturi = request.getURL()
        else:
            requesturi = str(requesturi)

        for link in MenuBase.iterlinks(self):
            link_url = str(link.url)
            link.linked = not requesturi.startswith(link_url)
            # A link is selected when the requestURI matches the link's URL
            # or because the link's menu is available.
            if (requesturi.startswith(link_url)
                or self._is_submenu_available(link, request)):
                link.selected = True
            else:
                link.selected = False
            yield link

    def _is_submenu_available(self, link, request):
        """Return True if a link's menu is available, otherwise False.

        A link's menu is a submenu. The submenu is associates with a view.
        A link is considered selected when the current view can be adapted
        to the link's menu.
        """
        view = request.traversed_objects[-1]
        # Note: The last traversed object may be a view's instance method.
        bare = removeSecurityProxy(view)
        if isinstance(bare, instancemethod):
            view = bare.im_self
        submenu = queryAdapter(view, INavigationMenu)
        if submenu is None:
            return False
        return isinstance(submenu, link.menu.__class__)


class enabled_with_permission:
    """Function decorator that disables the output link unless the current
    user has the given permission on the context.

    This class is instantiated by programmers who want to apply this
    decorator.

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


##
## Helpers for working with normal, structured, and internationalized
## text.
##

# XXX mars 2008-2-12:
# This entire block should be extracted into its own module, along
# with the structured() class.


def escape(message):
    """Performs translation and sanitizes any HTML present in the message.

    A plain string message will be sanitized ("&", "<" and ">" are
    converted to HTML-safe sequences).  Passing a message that
    provides the `IStructuredString` interface will return a unicode
    string that has been properly escaped.  Passing an instance of a
    Zope internationalized message will cause the message to be
    translated, then santizied.

    :param message: This may be a string, `zope.i18n.Message`,
        `zope.i18n.MessageID`, or an instance of `IStructuredString`.
    """
    if IStructuredString.providedBy(message):
        return message.escapedtext
    else:
        # It is possible that the message is wrapped in an
        # internationalized object, so we need to translate it
        # first. See bug #54987.
        return cgi.escape(
            unicode(
                translate_if_i18n(message)))


def translate_if_i18n(obj_or_msgid):
    """Translate an internationalized object, returning the result.

    Returns any other type of object untouched.
    """
    if isinstance(obj_or_msgid, (Message, MessageID)):
        return translate(
            obj_or_msgid,
            context=get_current_browser_request())
    else:
        # Just text (or something unknown).
        return obj_or_msgid

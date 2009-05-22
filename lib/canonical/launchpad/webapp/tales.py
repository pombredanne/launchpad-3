# Copyright 2004-2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=C0103,W0613,R0911
#
"""Implementation of the lp: htmlform: fmt: namespaces in TALES."""

__metaclass__ = type

import bisect
import cgi
from email.Utils import formatdate
import math
import os.path
import re
import rfc822
from xml.sax.saxutils import unescape as xml_unescape
from datetime import datetime, timedelta
from lazr.enum import enumerated_type_registry

from zope.interface import Interface, Attribute, implements
from zope.component import getUtility, queryAdapter, getMultiAdapter
from zope.app import zapi
from zope.publisher.browser import BrowserView
from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.traversing.interfaces import ITraversable, IPathAdapter
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zope_isinstance

import pytz
from z3c.ptcompat import ViewPageTemplateFile

from canonical.config import config
from canonical.launchpad import _
from canonical.launchpad.interfaces import (
    IBug, IBugSet, IDistribution, IFAQSet,
    IProduct, IProject, ISprint, LicenseStatus, NotFoundError)
from lp.soyuz.interfaces.archive import ArchivePurpose
from canonical.launchpad.interfaces.launchpad import (
    IHasIcon, IHasLogo, IHasMugshot)
from lp.registry.interfaces.person import IPerson, IPersonSet
from canonical.launchpad.webapp.interfaces import (
    IApplicationMenu, IContextMenu, IFacetMenu, ILaunchBag, INavigationMenu,
    IPrimaryContext, NoCanonicalUrl)
from canonical.launchpad.webapp.vhosts import allvhosts
import canonical.launchpad.pagetitles
from canonical.launchpad.webapp import canonical_url
from lazr.uri import URI
from canonical.launchpad.webapp.menu import get_current_view, get_facet
from canonical.launchpad.webapp.publisher import (
    get_current_browser_request, LaunchpadView, nearest)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.badge import IHasBadges
from canonical.launchpad.webapp.session import get_cookie_domain
from canonical.lazr.canonicalurl import nearest_adapter
from lp.soyuz.interfaces.build import BuildStatus


def escape(text, quote=True):
    """Escape text for insertion into HTML.

    Wraps `cgi.escape` to make the default to escape double-quotes.
    """
    return cgi.escape(text, quote)


class TraversalError(NotFoundError):
    """Remove this when we upgrade to a more recent Zope x3."""
    # XXX: Steve Alexander 2004-12-14:
    # Remove this when we upgrade to a more recent Zope x3.


class MenuAPI:
    """Namespace to give access to the facet menus.

    The facet menu can be accessed with an expression like:

        tal:define="facetmenu view/menu:facet"

    which gives the facet menu of the nearest object along the canonical url
    chain that has an IFacetMenu adapter.
    """

    def __init__(self, context):
        self._tales_context = context
        if zope_isinstance(context, (LaunchpadView, BrowserView)):
            # The view is a LaunchpadView or a SimpleViewClass from a
            # template. The facet is added to the call by the ZCML.
            self.view = context
            self._context = self.view.context
            self._request = self.view.request
            self._selectedfacetname = getattr(
                self.view, '__launchpad_facetname__', None)
        else:
            self._context = context
            self._request = get_current_browser_request()
            self.view = None
            self._selectedfacetname = None

    def __getattr__(self, facet):
        """Retrieve the links associated with a facet.

        It's used with expressions like context/menu:bugs/subscribe.

        :return: A dictionary mapping the link name to the associated Link
            object.
        :raise AttributeError: when there is no application menu for the
            facet.
        """
        if not self._has_facet(facet):
            raise AttributeError(facet)
        menu = queryAdapter(self._context, IApplicationMenu, facet)
        if menu is None:
            menu = queryAdapter(self._context, INavigationMenu, facet)
        if menu is not None:
            menu.request = self._request
            links_map = dict(
                (link.name, link)
                for link in menu.iterlinks(request_url=self._request_url()))
        else:
            # The object has the facet, but does not have a menu, this
            # is probably the overview menu with is the default facet.
            links_map = {}
        object.__setattr__(self, facet, links_map)
        return links_map

    def _has_facet(self, facet):
        """Does the object have the named facet?"""
        for facet_entry in self.facet():
            if facet == facet_entry.name:
                return True
        return False

    def _request_url(self):
        request = self._request
        if request is None:
            return None
        request_urlobj = URI(request.getURL())
        # If the default view name is being used, we will want the url
        # without the default view name.
        defaultviewname = zapi.getDefaultViewName(self._context, request)
        if request_urlobj.path.rstrip('/').endswith(defaultviewname):
            request_urlobj = URI(request.getURL(1))
        query = request.get('QUERY_STRING')
        if query:
            request_urlobj = request_urlobj.replace(query=query)
        return request_urlobj

    def facet(self):
        """Return the IFacetMenu related to the context."""
        try:
            try:
                context = IPrimaryContext(self._context).context
            except TypeError:
                # Could not adapt raises a type error.  If there was no
                # way to adapt, then just use self._context.
                context = self._context
            menu = nearest_adapter(context, IFacetMenu)
        except NoCanonicalUrl:
            menu = None

        if menu is None:
            return []
        menu.request = self._request
        return list(menu.iterlinks(
            request_url=self._request_url(),
            selectedfacetname=self._selectedfacetname))

    def selectedfacetname(self):
        if self._selectedfacetname is None:
            return 'unknown'
        else:
            return self._selectedfacetname

    @property
    def context(self):
        menu = IContextMenu(self._context, None)
        if menu is None:
            return  {}
        else:
            menu.request = self._request
            links = list(menu.iterlinks(request_url=self._request_url()))
            return dict((link.name, link) for link in links)

    @property
    def navigation(self):
        """Navigation menu links list."""
        # NavigationMenus may be associated with a content object or one of
        # its views. The context we need is the one from the TAL expression.
        context = self._tales_context
        if self._selectedfacetname is not None:
            selectedfacetname = self._selectedfacetname
        else:
            # XXX sinzui 2008-05-09 bug=226917: We should be retrieving the
            # facet name from the layer implemented by the request.
            view = get_current_view(self._request)
            selectedfacetname = get_facet(view)
        try:
            menu = nearest_adapter(
                context, INavigationMenu, name=selectedfacetname)
        except NoCanonicalUrl:
            menu = None
        if menu is None or menu.disabled:
            return {}
        else:
            menu.request = self._request
            links = list(menu.iterlinks(request_url=self._request_url()))
            return dict((link.name, link) for link in links)


class CountAPI:
    """Namespace to provide counting-related functions, such as length.

    This is available for all objects.  Individual operations may fail for
    objects that do not support them.
    """
    def __init__(self, context):
        self._context = context

    def len(self):
        """somelist/count:len  gives you an int that is len(somelist)."""
        return len(self._context)


class EnumValueAPI:
    """Namespace to test the value of an EnumeratedType Item.

    The value is given in the next path step.

        tal:condition="somevalue/enumvalue:BISCUITS"

    Registered for canonical.lazr.enum.Item.
    """
    implements(ITraversable)

    def __init__(self, item):
        self.item = item

    def traverse(self, name, furtherPath):
        if self.item.name == name:
            return True
        else:
            # Check whether this was an allowed value for this
            # enumerated type.
            enum = self.item.enum
            try:
                enum.getTermByToken(name)
            except LookupError:
                raise TraversalError(
                    'The enumerated type %s does not have a value %s.' %
                    (enum.name, name))
            return False


class HTMLFormAPI:
    """HTML form helper API, available as request/htmlform:.

    Use like:

        request/htmlform:fieldname/selected/literalvalue

        if request.form[fieldname] == literalvalue:
            return "selected"
        else:
            return None

    """
    implements(ITraversable)
    __used_for__ = IBrowserApplicationRequest

    def __init__(self, request):
        self.form = request.form

    def traverse(self, name, furtherPath):
        if len(furtherPath) == 1:
            operation = furtherPath.pop()
            return HTMLFormOperation(self.form.get(name), operation)
        else:
            operation = furtherPath.pop()
            value = furtherPath.pop()
            if htmlmatch(self.form.get(name), value):
                return operation
            else:
                return None

def htmlmatch(formvalue, value):
    value = str(value)
    if isinstance(formvalue, list):
        return value in formvalue
    else:
        return formvalue == value

class HTMLFormOperation:

    implements(ITraversable)

    def __init__(self, formvalue, operation):
        self.formvalue = formvalue
        self.operation = operation

    def traverse(self, name, furtherPath):
        if htmlmatch(self.formvalue, name):
            return self.operation
        else:
            return None


class IRequestAPI(Interface):
    """Launchpad lp:... API available for an IApplicationRequest."""

    person = Attribute("The IPerson for the request's principal.")
    cookie_scope = Attribute("The scope parameters for cookies.")


class RequestAPI:
    """Adapter from IApplicationRequest to IRequestAPI."""
    implements(IRequestAPI)

    __used_for__ = IApplicationRequest

    def __init__(self, request):
        self.request = request

    @property
    def person(self):
        return IPerson(self.request.principal, None)

    @property
    def cookie_scope(self):
        params = '; Path=/'
        uri = URI(self.request.getURL())
        if uri.scheme == 'https':
            params += '; Secure'
        domain = get_cookie_domain(uri.host)
        if domain is not None:
            params += '; Domain=%s' % domain
        return params


class DBSchemaAPI:
    """Adapter from integers to things that can extract information from
    DBSchemas.
    """
    implements(ITraversable)

    def __init__(self, number):
        self._number = number

    def traverse(self, name, furtherPath):
        if name in enumerated_type_registry:
            enum = enumerated_type_registry[name]
            return enum.items[self._number].title
        else:
            raise TraversalError(name)


class NoneFormatter:
    """Adapter from None to various string formats.

    In general, these will return an empty string.  They are provided for ease
    of handling NULL values from the database, which become None values for
    attributes in content classes.
    """
    implements(ITraversable)

    allowed_names = set([
        'approximatedate',
        'approximateduration',
        'break-long-words',
        'date',
        'datetime',
        'displaydate',
        'isodate',
        'email-to-html',
        'exactduration',
        'lower',
        'nice_pre',
        'nl_to_br',
        'pagetitle',
        'rfc822utcdatetime',
        'text-to-html',
        'time',
        'url',
        ])

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath):
        if name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            # Remove the maxlength from the path as it is a parameter
            # and not another traversal command.
            furtherPath.pop()
            return ''
        elif name in self.allowed_names:
            return ''
        else:
            raise TraversalError(name)


class ObjectFormatterAPI:
    """Adapter for any object to a formatted string."""

    implements(ITraversable)

    # Although we avoid mutables as class attributes, the two ones below are
    # constants, so it's not a problem. We might want to use something like
    # frozenset (http://code.activestate.com/recipes/414283/) here, though.
    # The names which can be traversed further (e.g context/fmt:url/+edit).
    traversable_names = {'link': 'link', 'url': 'url', 'api_url': 'api_url'}
    # Names which are allowed but can't be traversed further.
    final_traversable_names = {}

    def __init__(self, context):
        self._context = context

    def url(self, view_name=None, rootsite=None):
        """Return the object's canonical URL.

        :param view_name: If not None, return the URL to the page with that
            name on this object.
        :param rootsite: If not None, return the URL to the page on the
            specified rootsite.  Note this is available only for subclasses
            that allow specifying the rootsite.
        """
        try:
            url = canonical_url(
                self._context, path_only_if_possible=True,
                rootsite=rootsite,
                view_name=view_name)
        except Unauthorized:
            url = ""
        return url

    def api_url(self, context):
        """Return the object's (partial) canonical web service URL.

        This method returns everything that goes after the web service
        version number. It's the same as 'url', but without any view
        name.
        """
        return self.url()

    def traverse(self, name, furtherPath):
        if name in self.traversable_names:
            if len(furtherPath) >= 1:
                extra_path = '/'.join(reversed(furtherPath))
                del furtherPath[:]
            else:
                extra_path = None
            method_name = self.traversable_names[name]
            return getattr(self, method_name)(extra_path)
        elif name in self.final_traversable_names:
            method_name = self.final_traversable_names[name]
            return getattr(self, method_name)()
        else:
            raise TraversalError, name

    def link(self, view_name):
        """Return an HTML link to the object's page.

        The link consists of an icon followed by the object's name.

        :param view_name: If not None, the link will point to the page with
            that name on this object.
        """
        raise NotImplementedError(
            "No link implementation for %r, IPathAdapter implementation "
            "for %r." % (self, self._context))


class ObjectImageDisplayAPI:
    """Base class for producing the HTML that presents objects
    as an icon, a logo, a mugshot or a set of badges.
    """

    def __init__(self, context):
        self._context = context

    def default_icon_resource(self, context):
        # XXX: mars 2008-08-22 bug=260468
        # This should be refactored.  We shouldn't have to do type-checking
        # using interfaces.
        if IProduct.providedBy(context):
            return '/@@/product'
        elif IProject.providedBy(context):
            return '/@@/project'
        elif IPerson.providedBy(context):
            if context.isTeam():
                return '/@@/team'
            else:
                if context.is_valid_person:
                    return '/@@/person'
                else:
                    return '/@@/person-inactive'
        elif IDistribution.providedBy(context):
            return '/@@/distribution'
        elif ISprint.providedBy(context):
            return '/@@/meeting'
        elif IBug.providedBy(context):
            return '/@@/bug'
        return None

    def default_logo_resource(self, context):
        # XXX: mars 2008-08-22 bug=260468
        # This should be refactored.  We shouldn't have to do type-checking
        # using interfaces.
        if IProject.providedBy(context):
            return '/@@/project-logo'
        elif IPerson.providedBy(context):
            if context.isTeam():
                return '/@@/team-logo'
            else:
                if context.is_valid_person:
                    return '/@@/person-logo'
                else:
                    return '/@@/person-inactive-logo'
        elif IProduct.providedBy(context):
            return '/@@/product-logo'
        elif IDistribution.providedBy(context):
            return '/@@/distribution-logo'
        elif ISprint.providedBy(context):
            return '/@@/meeting-logo'
        return None

    def default_mugshot_resource(self, context):
        # XXX: mars 2008-08-22 bug=260468
        # This should be refactored.  We shouldn't have to do type-checking
        # using interfaces.
        if IProject.providedBy(context):
            return '/@@/project-mugshot'
        elif IPerson.providedBy(context):
            if context.isTeam():
                return '/@@/team-mugshot'
            else:
                if context.is_valid_person:
                    return '/@@/person-mugshot'
                else:
                    return '/@@/person-inactive-mugshot'
        elif IProduct.providedBy(context):
            return '/@@/product-mugshot'
        elif IDistribution.providedBy(context):
            return '/@@/distribution-mugshot'
        elif ISprint.providedBy(context):
            return '/@@/meeting-mugshot'
        return None

    def _default_icon_url(self, rootsite):
        """Get the default icon URL."""
        if rootsite is None:
            root_url = ''
        else:
            root_url = allvhosts.configs[rootsite].rooturl[:-1]

        default_icon = self.default_icon_resource(self._context)
        if default_icon is None:
            # We want to indicate that this object doesn't have an
            # icon.
            return None
        url = root_url + default_icon
        return url

    def icon_url(self, rootsite):
        """Return the URL for this object's icon."""
        context = self._context
        if context is None:
            # We handle None specially and return an empty string.
            return ''

        if IHasIcon.providedBy(context) and context.icon is not None:
            url = context.icon.getURL()
        else:
            url = self._default_icon_url(rootsite)
        return url

    def icon(self, rootsite=None):
        """Return the appropriate <img> tag for this object's icon.

        :return: A string, or None if the context object doesn't have
            an icon.
        """
        url = self.icon_url(rootsite)
        if url is None or url == '':
            return url
        icon = '<img alt="" width="14" height="14" src="%s" />'
        return icon % url

    def logo(self):
        """Return the appropriate <img> tag for this object's logo.

        :return: A string, or None if the context object doesn't have
            a logo.
        """
        context = self._context
        if not IHasLogo.providedBy(context):
            context = nearest(context, IHasLogo)
        if context is None:
            # we use the Launchpad logo for anything which is in no way
            # related to a Pillar (for example, a buildfarm)
            url = '/@@/launchpad-logo'
        elif context.logo is not None:
            url = context.logo.getURL()
        else:
            url = self.default_logo_resource(context)
            if url is None:
                # We want to indicate that there is no logo for this
                # object.
                return None
        logo = '<img alt="" width="64" height="64" src="%s" />'
        return logo % url

    def mugshot(self):
        """Return the appropriate <img> tag for this object's mugshot.

        :return: A string, or None if the context object doesn't have
            a mugshot.
        """
        context = self._context
        assert IHasMugshot.providedBy(context), 'No Mugshot for this item'
        if context.mugshot is not None:
            url = context.mugshot.getURL()
        else:
            url = self.default_mugshot_resource(context)
            if url is None:
                # We want to indicate that there is no mugshot for this
                # object.
                return None
        mugshot = """<img alt="" class="mugshot"
            width="192" height="192" src="%s" />"""
        return mugshot % url

    def badges(self):
        raise NotImplementedError(
            "Badge display not implemented for this item")


class BugTaskImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IBugTask objects to a formatted string. This inherits
    from the generic ObjectImageDisplayAPI and overrides the icon
    presentation method.

    Used for image:icon.
    """
    implements(ITraversable)

    allowed_names = set([
        'icon',
        'logo',
        'mugshot',
        'badges',
        ])

    icon_template = (
        '<img height="14" width="14" alt="%s" title="%s" src="%s" />')

    linked_icon_template = (
        '<a href="%s"><img height="14" width="14"'
        ' alt="%s" title="%s" src="%s" /></a>')

    def traverse(self, name, furtherPath):
        """Special-case traversal for icons with an optional rootsite."""
        if name in self.allowed_names:
            return getattr(self, name)()
        elif name.startswith('icon:'):
            rootsite = name.split(':', 1)[1]
            return self.icon(rootsite=rootsite)
        else:
            raise TraversalError, name

    def icon(self, rootsite=None):
        """Display the icon dependent on the IBugTask.importance."""
        if rootsite is not None:
            root_url = allvhosts.configs[rootsite].rooturl[:-1]
        else:
            root_url = ''
        if self._context.importance:
            importance = self._context.importance.title.lower()
            alt = "(%s)" % importance
            title = importance.capitalize()
            if importance not in ("undecided", "wishlist"):
                # The other status names do not make a lot of sense on
                # their own, so tack on a noun here.
                title += " importance"
            src = "%s/@@/bug-%s" % (root_url, importance)
        else:
            alt = ""
            title = ""
            src = "%s/@@/bug" % root_url

        return self.icon_template % (alt, title, src)

    def _hasMentoringOffer(self):
        """Return whether the bug has a mentoring offer."""
        return self._context.bug.mentoring_offers.count() > 0

    def _hasBugBranch(self):
        """Return whether the bug has a branch linked to it."""
        return self._context.bug.bug_branches.count() > 0

    def _hasSpecification(self):
        """Return whether the bug is linked to a specification."""
        return self._context.bug.specifications.count() > 0

    def badges(self):

        badges = []
        if self._context.bug.private:
            badges.append(self.icon_template % (
                "private", "Private","/@@/private"))

        if self._hasMentoringOffer():
            badges.append(self.icon_template % (
                "mentoring", "Mentoring offered", "/@@/mentoring"))

        if self._hasBugBranch():
            badges.append(self.icon_template % (
                "branch", "Branch exists", "/@@/branch"))

        if self._hasSpecification():
            badges.append(self.icon_template % (
                "blueprint", "Related to a blueprint", "/@@/blueprint"))

        if self._context.milestone:
            milestone_text = "milestone %s" % self._context.milestone.name
            badges.append(self.linked_icon_template % (
                canonical_url(self._context.milestone),
                milestone_text , "Linked to %s" % milestone_text,
                "/@@/milestone"))

        # Join with spaces to avoid the icons smashing into each other
        # when multiple ones are presented.
        return " ".join(badges)


class BugTaskListingItemImageDisplayAPI(BugTaskImageDisplayAPI):
    """Formatter for image:badges for BugTaskListingItem.

    The BugTaskListingItem has some attributes to decide whether a badge
    should be displayed, which don't require a DB query when they are
    accessed.
    """

    def _hasMentoringOffer(self):
        """See `BugTaskImageDisplayAPI`"""
        return self._context.has_mentoring_offer

    def _hasBugBranch(self):
        """See `BugTaskImageDisplayAPI`"""
        return self._context.has_bug_branch

    def _hasSpecification(self):
        """See `BugTaskImageDisplayAPI`"""
        return self._context.has_specification


class QuestionImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IQuestion to a formatted string. Used for image:icon."""

    def icon(self):
        return '<img alt="" height="14" width="14" src="/@@/question" />'


class SpecificationImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for ISpecification objects to a formatted string. This inherits
    from the generic ObjectImageDisplayAPI and overrides the icon
    presentation method.

    Used for image:icon.
    """

    icon_template = """
        <img height="14" width="14" alt="%s" title="%s" src="%s" />"""

    def icon(self):
        # The icon displayed is dependent on the IBugTask.importance.
        if self._context.priority:
            priority = self._context.priority.title.lower()
            alt = "(%s)" % priority
            title = priority.capitalize()
            if priority != 'not':
                # The other status names do not make a lot of sense on
                # their own, so tack on a noun here.
                title += " priority"
            else:
                title += " a priority"
            src = "/@@/blueprint-%s" % priority
        else:
            alt = ""
            title = ""
            src = "/@@/blueprint"

        return self.icon_template % (alt, title, src)


    def badges(self):

        badges = ''
        if self._context.mentoring_offers.count() > 0:
            badges += self.icon_template % (
                "mentoring", "Mentoring offered", "/@@/mentoring")

        if self._context.branch_links.count() > 0:
            badges += self.icon_template % (
                "branch", "Branch is available", "/@@/branch")

        if self._context.informational:
            badges += self.icon_template % (
                "informational", "Blueprint is purely informational",
                "/@@/info")

        return badges


class KarmaCategoryImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IKarmaCategory objects to an image.

    Used for image:icon.
    """

    icons_for_karma_categories = {
        'bugs': '/@@/bug',
        'code': '/@@/branch',
        'translations': '/@@/translation',
        'specs': '/@@/blueprint',
        'soyuz': '/@@/package-source',
        'answers': '/@@/question'}

    def icon(self):
        icon = self.icons_for_karma_categories[self._context.name]
        return ('<img height="14" width="14" alt="" title="%s" src="%s" />'
                % (self._context.title, icon))


class MilestoneImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IMilestone objects to an image.

    Used for image:icon.
    """

    def icon(self):
        """Return the appropriate <img> tag for the milestone icon."""
        return '<img height="14" width="14" alt="" src="/@@/milestone" />'


class BuildImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IBuild objects to an image.

    Used for image:icon.
    """
    icon_template = """
        <img width="14" height="14" alt="%s" title="%s" src="%s" />
        """

    def icon(self):
        """Return the appropriate <img> tag for the build icon."""
        icon_map = {
            BuildStatus.NEEDSBUILD: "/@@/build-needed",
            BuildStatus.FULLYBUILT: "/@@/build-success",
            BuildStatus.FAILEDTOBUILD: "/@@/build-failed",
            BuildStatus.MANUALDEPWAIT: "/@@/build-depwait",
            BuildStatus.CHROOTWAIT: "/@@/build-chrootwait",
            BuildStatus.SUPERSEDED: "/@@/build-superseded",
            BuildStatus.BUILDING: "/@@/build-building",
            BuildStatus.FAILEDTOUPLOAD: "/@@/build-failedtoupload",
            }

        alt = '[%s]' % self._context.buildstate.name
        title = self._context.buildstate.title
        source = icon_map[self._context.buildstate]

        return self.icon_template % (alt, title, source)


class ArchiveImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IArchive objects to an image.

    Used for image:icon.
    """
    icon_template = """
        <img width="14" height="14" alt="%s" title="%s" src="%s" />
        """

    def icon(self):
        """Return the appropriate <img> tag for an archive."""
        icon_map = {
            ArchivePurpose.PRIMARY: '/@@/distribution',
            ArchivePurpose.PARTNER: '/@@/distribution',
            ArchivePurpose.PPA: '/@@/package-source',
            ArchivePurpose.COPY: '/@@/distribution',
            ArchivePurpose.DEBUG: '/@@/distribution',
            }

        alt = '[%s]' % self._context.purpose.title
        title = self._context.purpose.title
        source = icon_map[self._context.purpose]

        return self.icon_template % (alt, title, source)


class BadgeDisplayAPI:
    """Adapter for IHasBadges to the images for the badges.

    Used for context/badges:small and context/badges:large.
    """

    def __init__(self, context):
        # Adapt the context.
        self.context = IHasBadges(context)

    def small(self):
        """Render the visible badge's icon images."""
        badges = self.context.getVisibleBadges()
        return ''.join([badge.renderIconImage() for badge in badges])

    def large(self):
        """Render the visible badge's heading images."""
        badges = self.context.getVisibleBadges()
        return ''.join([badge.renderHeadingImage() for badge in badges])


class PersonFormatterAPI(ObjectFormatterAPI):
    """Adapter for `IPerson` objects to a formatted string."""

    traversable_names = {'link': 'link', 'url': 'url', 'api_url': 'api_url',
                         'icon_url': 'icon_url',
                         'displayname': 'displayname',
                         'unique_displayname': 'unique_displayname',
                         }

    final_traversable_names = {'local-time': 'local_time'}

    def traverse(self, name, furtherPath):
        """Special-case traversal for links with an optional rootsite."""
        if name.startswith('link:') or name.startswith('url:'):
            rootsite = name.split(':')[1]
            extra_path = None
            if len(furtherPath) > 0:
                extra_path = '/'.join(reversed(furtherPath))
            # Remove remaining entries in furtherPath so that traversal
            # stops here.
            del furtherPath[:]
            if name.startswith('link:'):
                return self.link(extra_path, rootsite=rootsite)
            else:
                return self.url(extra_path, rootsite=rootsite)
        else:
            return super(PersonFormatterAPI, self).traverse(name, furtherPath)

    def local_time(self):
        """Return the local time for this person."""
        time_zone = 'UTC'
        if self._context.time_zone is not None:
            time_zone = self._context.time_zone
        return datetime.now(pytz.timezone(time_zone)).strftime('%T %Z')

    def link(self, view_name, rootsite=None):
        """Return an HTML link to the person's page containing an icon
        followed by the person's name.
        """
        person = self._context
        url = canonical_url(person, rootsite=rootsite, view_name=view_name)
        image_url = ObjectImageDisplayAPI(person).icon_url(rootsite=rootsite)
        return (u'<a href="%s" class="bg-image" '
                 'style="background-image: url(%s)">%s</a>') % (
            url, image_url, cgi.escape(person.browsername))

    def displayname(self, view_name, rootsite=None):
        """Return the displayname as a string."""
        person = self._context
        return person.displayname

    def unique_displayname(self, view_name, rootsite=None):
        """Return the unique_displayname as a string."""
        person = self._context
        return person.unique_displayname

    def icon_url(self, view_name, rootsite=None):
        """Return the URL for the person's icon."""
        return ObjectImageDisplayAPI(self._context).icon_url(
            rootsite=rootsite)

class TeamFormatterAPI(PersonFormatterAPI):
    """Adapter for `ITeam` objects to a formatted string."""

    hidden = u'<hidden>'

    def url(self, view_name=None):
        """See `ObjectFormatterAPI`."""
        if not check_permission('launchpad.View', self._context):
            # This person has no permission to view the team details.
            return None
        return super(TeamFormatterAPI, self).url(view_name)

    def api_url(self, context):
        """See `ObjectFormatterAPI`."""
        if not check_permission('launchpad.View', self._context):
            # This person has no permission to view the team details.
            return None
        return super(TeamFormatterAPI, self).api_url(context)

    def link(self, view_name, rootsite=None):
        """See `ObjectFormatterAPI`."""
        person = self._context
        if not check_permission('launchpad.View', person):
            # This person has no permission to view the team details.
            image_url = ObjectImageDisplayAPI(person)._default_icon_url(
                rootsite=rootsite)
            return ('<span style="padding-left: 18px; background: url(%s)'
                    'center left no-repeat;">%s</span>') % (
                image_url, cgi.escape(self.hidden))
        return super(TeamFormatterAPI, self).link(view_name, rootsite)

    def displayname(self, view_name, rootsite=None):
        """See `PersonFormatterAPI`."""
        person = self._context
        if not check_permission('launchpad.View', person):
            # This person has no permission to view the team details.
            return self.hidden
        return super(TeamFormatterAPI, self).displayname(view_name, rootsite)

    def unique_displayname(self, view_name, rootsite=None):
        """See `PersonFormatterAPI`."""
        person = self._context
        if not check_permission('launchpad.View', person):
            # This person has no permission to view the team details.
            return self.hidden
        return super(TeamFormatterAPI, self).unique_displayname(view_name,
                                                                rootsite)
    def icon_url(self, view_name, rootsite=None):
        """Return the URL for the team's icon.

        If the team is private use the default team icon url.
        """
        person = self._context
        if not check_permission('launchpad.View', person):
            image_url = ObjectImageDisplayAPI(person)._default_icon_url(
                rootsite=rootsite)
            return image_url

        return ObjectImageDisplayAPI(person).icon_url(rootsite=rootsite)


class CustomizableFormatter(ObjectFormatterAPI):
    """A ObjectFormatterAPI that is easy to customize.

    This provides fmt:url and fmt:link support for the object it
    adapts.

    For most object types, only the _link_summary_template class
    variable and _link_summary_values method need to be overridden.
    This assumes that:

      1. canonical_url produces appropriate urls for this type,
      2. the launchpad.View permission alone is required to view this
         object's url, and,
      3. if there is an icon for this object type, image:icon is
         implemented and appropriate.

    For greater control over the summary, overrride
    _make_link_summary.

    If image:icon does not provide a suitable icon, override
    _get_icon.

    If a different permission is required, override _link_permission.
    """

    _link_permission = 'launchpad.View'

    def _link_summary_values(self):
        """Return a dict of values to use for template substitution.

        These values should not be escaped, as this will be performed later.
        For this reason, only string values should be supplied.
        """
        raise NotImplementedError(self._link_summary_values)

    def _make_link_summary(self):
        """Create a summary from _template and _link_summary_values().

        This summary is for use in fmt:link, which is meant to be used in
        contexts like lists of items.
        """
        values = {}
        for key, value in self._link_summary_values().iteritems():
            if value is None:
                values[key] = ''
            else:
                values[key] = cgi.escape(value)
        return self._link_summary_template % values

    def _get_icon(self):
        """Retrieve the icon for the _context, if any.

        :return: The icon HTML or None if no icon is available.
        """
        return queryAdapter(self._context, IPathAdapter, 'image').icon()

    def link(self, view_name):
        """Return html including a link, description and icon.

        Icon and link are optional, depending on type and permissions.
        Uses self._make_link_summary for the summary, self._get_icon
        for the icon, self._should_link to determine whether to link, and
        self.url() to generate the url.
        """
        html = self._get_icon()
        if html is None:
            html = ''
        else:
            html += '&nbsp;'
        html += self._make_link_summary()
        if check_permission(self._link_permission, self._context):
            url = self.url(view_name)
        else:
            url = ''
        if url:
            html = '<a href="%s">%s</a>' % (url, html)
        return html


class PillarFormatterAPI(CustomizableFormatter):
    """Adapter for IProduct, IDistribution and IProject objects to a
    formatted string."""

    _link_summary_template = '%(displayname)s'
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        displayname = self._context.displayname
        return {'displayname': displayname}

    def link(self, view_name):
        html = super(PillarFormatterAPI, self).link(view_name)
        if IProduct.providedBy(self._context):
            license_status = self._context.license_status
            if license_status != LicenseStatus.OPEN_SOURCE:
                html = '<span title="%s">%s (%s)</span>' % (
                    license_status.description, html,
                    license_status.title)
        return html


class SourcePackageFormatterAPI(CustomizableFormatter):
    """Adapter for ISourcePackage objects to a formatted string."""

    _link_summary_template = '%(displayname)s'

    def _link_summary_values(self):
        displayname = self._context.displayname
        return {'displayname': displayname}


class BranchFormatterAPI(ObjectFormatterAPI):
    """Adapter for IBranch objects to a formatted string."""

    traversable_names = {
        'link': 'link', 'url': 'url', 'project-link': 'projectLink',
        'title-link': 'titleLink', 'bzr-link': 'bzrLink'}

    def _args(self, view_name):
        """Generate a dict of attributes for string template expansion."""
        branch = self._context
        if branch.title is not None:
            title = branch.title
        else:
            title = "(no title)"
        return {
            'bzr_identity': branch.bzr_identity,
            'display_name': cgi.escape(branch.displayname),
            'name': branch.name,
            'title': cgi.escape(title),
            'unique_name' : branch.unique_name,
            'url': self.url(view_name),
            }

    def link(self, view_name):
        """A hyperlinked branch icon with the unique name."""
        return (
            '<a href="%(url)s" title="%(display_name)s">'
            '<img src="/@@/branch" alt=""/>'
            '&nbsp;%(unique_name)s</a>' % self._args(view_name))

    def bzrLink(self, view_name):
        """A hyperlinked branch icon with the bazaar identity."""
        return (
            '<a href="%(url)s" title="%(display_name)s">'
            '<img src="/@@/branch" alt=""/>'
            '&nbsp;%(bzr_identity)s</a>' % self._args(view_name))

    def projectLink(self, view_name):
        """A hyperlinked branch icon with the name and title."""
        return (
            '<a href="%(url)s" title="%(display_name)s">'
            '<img src="/@@/branch" alt=""/>'
            '&nbsp;%(name)s</a>: %(title)s' % self._args(view_name))

    def titleLink(self, view_name):
        """A hyperlinked branch name with following title."""
        return (
            '<a href="%(url)s" title="%(display_name)s">'
            '%(name)s</a>: %(title)s' % self._args(view_name))


class PreviewDiffFormatterAPI(ObjectFormatterAPI):
    """Formatter for preview diffs."""

    def url(self, view_name=None):
        """Use the url of the librarian file containing the diff.
        """
        librarian_alias = self._context.diff_text
        if librarian_alias is None:
            return None
        else:
            return librarian_alias.getURL()

    def link(self, view_name):
        """The link to the diff should show the line count.

        Stale diffs will have a stale-diff css class.
        Diffs with conflicts will have a conflict-diff css class.
        Diffs with neither will have clean-diff css class.

        The title of the diff will show the number of lines added or removed
        if available.

        :param view_name: If not None, the link will point to the page with
            that name on this object.
        """
        title_words = []
        if self._context.conflicts is not None:
            style = 'conflicts-diff'
            title_words.append(_('CONFLICTS'))
        else:
            style = 'clean-diff'
        # Stale style overrides conflicts or clean.
        if self._context.stale:
            style = 'stale-diff'
            title_words.append(_('Stale'))

        if self._context.added_lines_count:
            title_words.append(
                _("%s added") % self._context.added_lines_count)

        if self._context.removed_lines_count:
            title_words.append(
                _("%s removed") % self._context.removed_lines_count)

        args = {
            'line_count': _('%s lines') % self._context.diff_lines_count,
            'style': style,
            'title': ', '.join(title_words),
            'url': self.url(view_name),
            }
        # Under normal circumstances, there will be an associated file,
        # however if the diff is empty, then there is no alias to link to.
        if args['url'] is None:
            return (
                '<span title="%(title)s" class="%(style)s">'
                '%(line_count)s</span>' % args)
        else:
            return (
                '<a href="%(url)s" title="%(title)s" class="%(style)s">'
                '<img src="/@@/download"/>&nbsp;%(line_count)s</a>' % args)


class BranchSubscriptionFormatterAPI(CustomizableFormatter):
    """Adapter for IBranchSubscription objects to a formatted string."""

    _link_summary_template = _('Subscription of %(person)s to %(branch)s')

    def _link_summary_values(self):
        """Provide values for template substitution"""
        return {
            'person': self._context.person.displayname,
            'branch': self._context.branch.displayname,
        }


class BranchMergeProposalFormatterAPI(CustomizableFormatter):

    _link_summary_template = _('%(title)s')

    def _link_summary_values(self):
        return {
            'title': self._context.title,
            }


class BugBranchFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for BugBranch objects"""

    def _get_task_formatter(self):
        task = self._context.bug.getBugTask(self._context.branch.product)
        if task is None:
            task = self._context.bug.bugtasks[0]
        return BugTaskFormatterAPI(task)

    def _make_link_summary(self):
        """Return the summary of the related product's bug task"""
        return self._get_task_formatter()._make_link_summary()

    def _get_icon(self):
        """Return the icon of the related product's bugtask"""
        return self._get_task_formatter()._get_icon()


class BugFormatterAPI(CustomizableFormatter):
    """Adapter for IBug objects to a formatted string."""

    _link_summary_template = 'Bug #%(id)s: %(title)s'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'id': str(self._context.id), 'title': self._context.title}


class BugTaskFormatterAPI(CustomizableFormatter):
    """Adapter for IBugTask objects to a formatted string."""

    def _make_link_summary(self):
        return BugFormatterAPI(self._context.bug)._make_link_summary()


class CodeImportFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for CodeImport objects"""

    _link_summary_template = _('Import of %(product)s: %(branch)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        branch_title = self._context.branch.title
        if branch_title is None:
            branch_title = _('(no title)')
        return {'product': self._context.product.displayname,
                'branch': branch_title,
               }

    def url(self, view_name=None):
        """See `ObjectFormatterAPI`."""
        # The url of a code import is the associated branch.
        # This is still here primarily for supporting branch deletion,
        # which does a fmt:link of the other entities that will be deleted.
        url = canonical_url(
            self._context.branch, path_only_if_possible=True,
            view_name=view_name)
        return url


class CodeImportMachineFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for CodeImport objects"""

    _link_summary_template = _('%(hostname)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'hostname': self._context.hostname,}


class MilestoneFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for Milestone objects."""

    _link_summary_template = _('%(title)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'title': self._context.title}


class ProductReleaseFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for Milestone objects."""

    _link_summary_template = _('%(displayname)s %(code_name)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        code_name = self._context.milestone.code_name
        if code_name is None or code_name.strip() == '':
            code_name = ''
        else:
            code_name = '(%s)' % code_name.strip()
        return dict(displayname=self._context.milestone.displayname,
                    code_name=code_name)


class ProductSeriesFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for ProductSeries objects"""

    _link_summary_template = _('%(product)s Series: %(series)s')

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'series': self._context.name,
                'product': self._context.product.displayname}


class QuestionFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for question objects."""

    _link_summary_template = _('%(id)s: %(title)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'id': str(self._context.id), 'title': self._context.title}


class SpecificationFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for Specification objects"""

    _link_summary_template = _('%(title)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'title': self._context.title}


class CodeReviewCommentFormatterAPI(CustomizableFormatter):
    """Adapter providing fmt support for CodeReviewComment objects"""

    _link_summary_template = _('Comment by %(author)s')
    _link_permission = 'zope.Public'

    def _link_summary_values(self):
        """See CustomizableFormatter._link_summary_values."""
        return {'author': self._context.message.owner.displayname}


class SpecificationBranchFormatterAPI(CustomizableFormatter):
    """Adapter for ISpecificationBranch objects to a formatted string."""

    def _make_link_summary(self):
        """Provide the summary of the linked spec"""
        formatter = SpecificationFormatterAPI(self._context.specification)
        return formatter._make_link_summary()

    def _get_icon(self):
        """Provide the icon of the linked spec"""
        formatter = SpecificationFormatterAPI(self._context.specification)
        return formatter._get_icon()


class BugTrackerFormatterAPI(ObjectFormatterAPI):
    """Adapter for `IBugTracker` objects to a formatted string."""

    final_traversable_names = {
        'aliases': 'aliases',
        'external-link': 'external_link',
        'external-title-link': 'external_title_link'}

    def link(self, view_name):
        """Return an HTML link to the bugtracker page.

        If the user is not logged-in, the title of the bug tracker is
        modified to obfuscate all email addresses.
        """
        url = self.url(view_name)
        title = self._context.title
        if getUtility(ILaunchBag).user is None:
            title = FormattersAPI(title).obfuscate_email()
        return u'<a href="%s">%s</a>' % (escape(url), escape(title))

    def external_link(self):
        """Return an HTML link to the external bugtracker.

        If the user is not logged-in, and the URL of the bugtracker
        contains an email address, this returns the obfuscated URL as
        text (i.e. no <a/> link).
        """
        url = self._context.baseurl
        if url.startswith('mailto:') and getUtility(ILaunchBag).user is None:
            return escape(u'mailto:<email address hidden>')
        else:
            href = escape(url)
            return u'<a class="link-external" href="%s">%s</a>' % (href, href)

    def external_title_link(self):
        """Return an HTML link to the external bugtracker.

        If the user is not logged-in, the title of the bug tracker is
        modified to obfuscate all email addresses. Additonally, if the
        URL is a mailto: address then no link is returned, just the
        title text.
        """
        url = self._context.baseurl
        title = self._context.title
        if getUtility(ILaunchBag).user is None:
            title = FormattersAPI(title).obfuscate_email()
            if url.startswith('mailto:'):
                return escape(title)
        return u'<a class="link-external" href="%s">%s</a>' % (
            escape(url), escape(title))

    def aliases(self):
        """Generate alias URLs, obfuscating where necessary.

        If the user is not logged-in, email addresses should be
        hidden.
        """
        anonymous = getUtility(ILaunchBag).user is None
        for alias in self._context.aliases:
            if anonymous and alias.startswith('mailto:'):
                yield escape(u'mailto:<email address hidden>')
            else:
                yield alias


class BugWatchFormatterAPI(ObjectFormatterAPI):
    """Adapter for `IBugWatch` objects to a formatted string."""

    final_traversable_names = {
        'external-link': 'external_link',
        'external-link-short': 'external_link_short'}

    def _make_external_link(self, summary=None):
        """Return an external HTML link to the target of the bug watch.

        If a summary is not specified or empty, an em-dash is used as
        the content of the link.

        If the user is not logged in and the URL of the bug watch is
        an email address, only the summary is returned (i.e. no link).
        """
        if summary is None or len(summary) == 0:
            summary = u'&mdash;'
        else:
            summary = escape(summary)
        url = self._context.url
        if url.startswith('mailto:') and getUtility(ILaunchBag).user is None:
            return summary
        else:
            return u'<a class="link-external" href="%s">%s</a>' % (
                escape(url), summary)

    def external_link(self):
        """Return an HTML link with a detailed link text.

        The link text is formed from the bug tracker name and the
        remote bug number.
        """
        summary = self._context.bugtracker.name
        remotebug = self._context.remotebug
        if remotebug is not None and len(remotebug) > 0:
            summary = u'%s #%s' % (summary, remotebug)
        return self._make_external_link(summary)

    def external_link_short(self):
        """Return an HTML link with a short link text.

        The link text is formed from the bug tracker name and the
        remote bug number.
        """
        return self._make_external_link(self._context.remotebug)


class NumberFormatterAPI:
    """Adapter for converting numbers to formatted strings."""

    implements(ITraversable)

    def __init__(self, number):
        self._number = number

    def traverse(self, name, furtherPath):
        if name == 'float':
            if len(furtherPath) != 1:
                raise TraversalError(
                    "fmt:float requires a single decimal argument")
            # coerce the argument to float to ensure it's safe
            format = furtherPath.pop()
            return self.float(float(format))
        elif name == 'bytes':
            return self.bytes()
        else:
            raise TraversalError(name)

    def bytes(self):
        """Render number as byte contractions according to IEC60027-2."""
        # See http://en.wikipedia.org/wiki
        # /Binary_prefixes#Specific_units_of_IEC_60027-2_A.2
        # Note that there is a zope.app.size.byteDisplay() function, but
        # it really limited and doesn't work well enough for us here.
        assert not float(self._number) < 0, "Expected a non-negative number."
        n = int(self._number)
        if n == 1:
            # Handle the singular case.
            return "1 byte"
        if n == 0:
            # To avoid math.log(0, X) blowing up.
            return "0 bytes"
        suffixes = ["KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
        exponent = int(math.log(n, 1024))
        exponent = min(len(suffixes), exponent)
        if exponent < 1:
            # If this is less than 1 KiB, no need for rounding.
            return "%s bytes" % n
        return "%.1f %s" % (n / 1024.0 ** exponent, suffixes[exponent - 1])

    def float(self, format):
        """Use like tal:content="context/foo/fmt:float/.2".

        Will return a string formatted to the specification provided in
        the manner Python "%f" formatter works. See
        http://docs.python.org/lib/typesseq-strings.html for details and
        doc.displaying-numbers for various examples.
        """
        value = "%" + str(format) + "f"
        return value % float(self._number)


class DateTimeFormatterAPI:
    """Adapter from datetime objects to a formatted string."""

    def __init__(self, datetimeobject):
        self._datetime = datetimeobject

    def time(self):
        if self._datetime.tzinfo:
            value = self._datetime.astimezone(
                getUtility(ILaunchBag).time_zone)
            return value.strftime('%T %Z')
        else:
            return self._datetime.strftime('%T')

    def date(self):
        value = self._datetime
        if value.tzinfo:
            value = value.astimezone(
                getUtility(ILaunchBag).time_zone)
        return value.strftime('%Y-%m-%d')

    def _now(self):
        # This method exists to be overridden in tests.
        if self._datetime.tzinfo:
            # datetime is offset-aware
            return datetime.now(pytz.timezone('UTC'))
        else:
            # datetime is offset-naive
            return datetime.utcnow()

    def displaydate(self):
        delta = abs(self._now() - self._datetime)
        if delta > timedelta(1, 0, 0):
            # far in the past or future, display the date
            return 'on ' + self.date()
        return self.approximatedate()

    def approximatedate(self):
        delta = self._now() - self._datetime
        if abs(delta) > timedelta(1, 0, 0):
            # far in the past or future, display the date
            return self.date()
        future = delta < timedelta(0, 0, 0)
        delta = abs(delta)
        days = delta.days
        hours = delta.seconds / 3600
        minutes = (delta.seconds - (3600*hours)) / 60
        seconds = delta.seconds % 60
        result = ''
        if future:
            result += 'in '
        if days != 0:
            amount = days
            unit = 'day'
        elif hours != 0:
            amount = hours
            unit = 'hour'
        elif minutes != 0:
            amount = minutes
            unit = 'minute'
        else:
            amount = seconds
            unit = 'second'
        if amount != 1:
            unit += 's'
        result += '%s %s' % (amount, unit)
        if not future:
            result += ' ago'
        return result

    def datetime(self):
        return "%s %s" % (self.date(), self.time())

    def rfc822utcdatetime(self):
        return formatdate(
            rfc822.mktime_tz(self._datetime.utctimetuple() + (0,)))

    def isodate(self):
        return self._datetime.isoformat()


class SeriesSourcePackageBranchFormatter(ObjectFormatterAPI):
    """Formatter for a SourcePackage, Pocket -> Branch link.

    Since the link object is never really interesting in and of itself, we
    always link to the source package instead.
    """

    def url(self, view_name=None, rootsite=None):
        return queryAdapter(
            self._context.sourcepackage, IPathAdapter, 'fmt').url(
                view_name, rootsite)

    def link(self, view_name):
        return queryAdapter(
            self._context.sourcepackage, IPathAdapter, 'fmt').link(view_name)


class DurationFormatterAPI:
    """Adapter from timedelta objects to a formatted string."""

    implements(ITraversable)

    def __init__(self, duration):
        self._duration = duration

    def traverse(self, name, furtherPath):
        if name == 'exactduration':
            return self.exactduration()
        elif name == 'approximateduration':
            use_words = True
            if len(furtherPath) == 1:
                if 'use-digits' == furtherPath[0]:
                    furtherPath.pop()
                    use_words = False
            return self.approximateduration(use_words)
        else:
            raise TraversalError(name)

    def exactduration(self):
        """Format timedeltas as "v days, w hours, x minutes, y.z seconds"."""
        parts = []
        minutes, seconds = divmod(self._duration.seconds, 60)
        hours, minutes = divmod(minutes, 60)
        seconds = seconds + (float(self._duration.microseconds) / 10**6)
        if self._duration.days > 0:
            if self._duration.days == 1:
                parts.append('%d day' % self._duration.days)
            else:
                parts.append('%d days' % self._duration.days)
        if parts or hours > 0:
            if hours == 1:
                parts.append('%d hour' % hours)
            else:
                parts.append('%d hours' % hours)
        if parts or minutes > 0:
            if minutes == 1:
                parts.append('%d minute' % minutes)
            else:
                parts.append('%d minutes' % minutes)
        if parts or seconds > 0:
            parts.append('%0.1f seconds' % seconds)

        return ', '.join(parts)

    def approximateduration(self, use_words=True):
        """Return a nicely-formatted approximate duration.

        E.g. 'an hour', 'three minutes', '1 hour 10 minutes' and so
        forth.

        See https://launchpad.canonical.com/PresentingLengthsOfTime.

        :param use_words: Specificly determines whether or not to use
            words for numbers less than or equal to ten.  Expanding
            numbers to words makes sense when the number is used in
            prose or a singualar item on a page, but when used in
            a table, the words do not work as well.
        """
        # NOTE: There are quite a few "magic numbers" in this
        # implementation; they are generally just figures pulled
        # directly out of the PresentingLengthsOfTime spec, and so
        # it's not particularly easy to give each and every number of
        # a useful name. It's also unlikely that these numbers will be
        # changed.

        # Calculate the total number of seconds in the duration,
        # including the decimal part.
        seconds = self._duration.days * (3600 * 24)
        seconds += self._duration.seconds
        seconds += (float(self._duration.microseconds) / 10**6)

        # First we'll try to calculate an approximate number of
        # seconds up to a minute. We'll start by defining a sorted
        # list of (boundary, display value) tuples.  We want to show
        # the display value corresponding to the lowest boundary that
        # 'seconds' is less than, if one exists.
        representation_in_seconds = [
            (1.5, '1 second'),
            (2.5, '2 seconds'),
            (3.5, '3 seconds'),
            (4.5, '4 seconds'),
            (7.5, '5 seconds'),
            (12.5, '10 seconds'),
            (17.5, '15 seconds'),
            (22.5, '20 seconds'),
            (27.5, '25 seconds'),
            (35, '30 seconds'),
            (45, '40 seconds'),
            (55, '50 seconds'),
            (90, 'a minute'),
        ]
        if not use_words:
            representation_in_seconds[-1] = (90, '1 minute')

        # Break representation_in_seconds into two pieces, to simplify
        # finding the correct display value, through the use of the
        # built-in bisect module.
        second_boundaries, display_values = zip(*representation_in_seconds)

        # Is seconds small enough that we can produce a representation
        # in seconds (up to 'a minute'?)
        if seconds < second_boundaries[-1]:
            # Use the built-in bisection algorithm to locate the index
            # of the item which "seconds" sorts after.
            matching_element_index = bisect.bisect(second_boundaries, seconds)

            # Return the corresponding display value.
            return display_values[matching_element_index]

        # More than a minute, approximately; our calculation strategy
        # changes. From this point forward, we may also need a
        # "verbal" representation of the number. (We never need a
        # verbal representation of "1", because we tend to special
        # case the number 1 for various approximations, and we usually
        # use a word like "an", instead of "one", e.g. "an hour")
        if use_words:
            number_name = {
                2: 'two', 3: 'three', 4: 'four', 5: 'five',
                6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
                10: 'ten'}
        else:
            number_name = dict((number, number) for number in range(2, 11))

        # Convert seconds into minutes, and round it.
        minutes, remaining_seconds = divmod(seconds, 60)
        minutes += remaining_seconds / 60.0
        minutes = int(round(minutes))

        if minutes <= 59:
            return "%s minutes" % number_name.get(minutes, str(minutes))

        # Is the duration less than an hour and 5 minutes?
        if seconds < (60 + 5) * 60:
            if use_words:
                return "an hour"
            else:
                return "1 hour"

        # Next phase: try and calculate an approximate duration
        # greater than one hour, but fewer than ten hours, to a 10
        # minute granularity.
        hours, remaining_seconds = divmod(seconds, 3600)
        ten_minute_chunks = int(round(remaining_seconds / 600.0))
        minutes = ten_minute_chunks * 10
        hours += (minutes / 60)
        minutes %= 60
        if hours < 10:
            if minutes:
                # If there is a minutes portion to display, the number
                # of hours is always shown as a digit.
                if hours == 1:
                    return "1 hour %s minutes" % minutes
                else:
                    return "%d hours %s minutes" % (hours, minutes)
            else:
                number_as_text = number_name.get(hours, str(hours))
                return "%s hours" % number_as_text

        # Is the duration less than ten and a half hours?
        if seconds < (10.5 * 3600):
            return '%s hours' % number_name[10]

        # Try to calculate the approximate number of hours, to a
        # maximum of 47.
        hours = int(round(seconds / 3600.0))
        if hours <= 47:
            return "%d hours" % hours

        # Is the duration fewer than two and a half days?
        if seconds < (2.5 * 24 * 3600):
            return '%s days' % number_name[2]

        # Try to approximate to day granularity, up to a maximum of 13
        # days.
        days = int(round(seconds / (24 * 3600)))
        if days <= 13:
            return "%s days" % number_name.get(days, str(days))

        # Is the duration fewer than two and a half weeks?
        if seconds < (2.5 * 7 * 24 * 3600):
            return '%s weeks' % number_name[2]

        # If we've made it this far, we'll calculate the duration to a
        # granularity of weeks, once and for all.
        weeks = int(round(seconds / (7 * 24 * 3600.0)))
        return "%s weeks" % number_name.get(weeks, str(weeks))


class LinkFormatterAPI(ObjectFormatterAPI):
    """Adapter from Link objects to a formatted anchor."""
    final_traversable_names = {
        'icon': 'icon',
        'icon-link': 'icon_link',
        'link-icon': 'link_icon',
        }

    def icon(self):
        """Return the icon representation of the link."""
        request = get_current_browser_request()
        return getMultiAdapter(
            (self._context, request), name="+inline-icon")()

    def link_icon(self):
        """Return the text and icon representation of the link."""
        request = get_current_browser_request()
        return getMultiAdapter(
            (self._context, request), name="+inline-suffix")()

    def icon_link(self):
        """Return the icon and text representation of the link."""
        return self.link(None)

    def link(self, view_name, rootsite=None):
        """Return the default representation of the link."""
        return self._context.render()

    def url(self, view_name=None):
        """Return the URL representation of the link."""
        if self._context.enabled:
            return self._context.url
        else:
            return u''


def clean_path_segments(request):
    """Returns list of path segments, excluding system-related segments."""
    proto_host_port = request.getApplicationURL()
    clean_url = request.getURL()
    clean_path = clean_url[len(proto_host_port):]
    clean_path_split = clean_path.split('/')
    return clean_path_split


class PageTemplateContextsAPI:
    """Adapter from page tempate's CONTEXTS object to fmt:pagetitle.

    This is registered to be used for the dict type.
    """

    implements(ITraversable)

    def __init__(self, contextdict):
        self.contextdict = contextdict

    def traverse(self, name, furtherPath):
        if name == 'pagetitle':
            return self.pagetitle()
        else:
            raise TraversalError(name)

    def pagetitle(self):
        """Return the string title for the page template CONTEXTS dict.

        Take the simple filename without extension from
        self.contextdict['template'].filename, replace any hyphens with
        underscores, and use this to look up a string, unicode or
        function in the module canonical.launchpad.pagetitles.

        If no suitable object is found in canonical.launchpad.pagetitles, emit
        a warning that this page has no title, and return the default page
        title.
        """
        template = self.contextdict['template']
        filename = os.path.basename(template.filename)
        name, ext = os.path.splitext(filename)
        name = name.replace('-', '_')
        titleobj = getattr(canonical.launchpad.pagetitles, name, None)
        if titleobj is None:
            # sabdfl 25/0805 page titles are now mandatory hence the assert
            raise AssertionError(
                 "No page title in canonical.launchpad.pagetitles "
                 "for %s" % name)
        elif isinstance(titleobj, basestring):
            return titleobj
        else:
            context = self.contextdict['context']
            view = self.contextdict['view']
            title = titleobj(context, view)
            if title is None:
                return canonical.launchpad.pagetitles.DEFAULT_LAUNCHPAD_TITLE
            else:
                return title


def split_paragraphs(text):
    """Split text into paragraphs.

    This function yields lists of strings that represent lines of text
    in each paragraph.

    Paragraphs are split by one or more blank lines.
    """
    paragraph = []
    for line in text.splitlines():
        line = line.rstrip()

        # blank lines split paragraphs
        if not line:
            if paragraph:
                yield paragraph
            paragraph = []
            continue

        paragraph.append(line)

    if paragraph:
        yield paragraph


def re_substitute(pattern, replace_match, replace_nomatch, string):
    """Transform a string, replacing matched and non-matched sections.

     :param patter: a regular expression
     :param replace_match: a function used to transform matches
     :param replace_nomatch: a function used to transform non-matched text
     :param string: the string to transform

    This function behaves similarly to re.sub() when a function is
    passed as the second argument, except that the non-matching
    portions of the string can be transformed by a second function.
    """
    if replace_match is None:
        replace_match = lambda match: match.group()
    if replace_nomatch is None:
        replace_nomatch = lambda text: text
    parts = []
    position = 0
    for match in re.finditer(pattern, string):
        if match.start() != position:
            parts.append(replace_nomatch(string[position:match.start()]))
        parts.append(replace_match(match))
        position = match.end()
    remainder = string[position:]
    if remainder:
        parts.append(replace_nomatch(remainder))
    return ''.join(parts)


def next_word_chunk(word, pos, minlen, maxlen):
    """Return the next chunk of the word of length between minlen and maxlen.

    Shorter word chunks are preferred, preferably ending in a non
    alphanumeric character.  The index of the end of the chunk is also
    returned.

    This function treats HTML entities in the string as single
    characters.  The string should not include HTML tags.
    """
    nchars = 0
    endpos = pos
    while endpos < len(word):
        # advance by one character
        if word[endpos] == '&':
            # make sure we grab the entity as a whole
            semicolon = word.find(';', endpos)
            assert semicolon >= 0, 'badly formed entity: %r' % word[endpos:]
            endpos = semicolon + 1
        else:
            endpos += 1
        nchars += 1
        if nchars >= maxlen:
            # stop if we've reached the maximum chunk size
            break
        if nchars >= minlen and not word[endpos-1].isalnum():
            # stop if we've reached the minimum chunk size and the last
            # character wasn't alphanumeric.
            break
    return word[pos:endpos], endpos


def add_word_breaks(word):
    """Insert manual word breaks into a string.

    The word may be entity escaped, but is not expected to contain
    any HTML tags.

    Breaks are inserted at least every 7 to 15 characters,
    preferably after puctuation.
    """
    broken = []
    pos = 0
    while pos < len(word):
        chunk, pos = next_word_chunk(word, pos, 7, 15)
        broken.append(chunk)
    return '<wbr></wbr>'.join(broken)


break_text_pat = re.compile(r'''
  (?P<tag>
    <[^>]*>
  ) |
  (?P<longword>
    (?<![^\s<>])(?:[^\s<>&]|&[^;]*;){20,}
  )
''', re.VERBOSE)

def break_long_words(text):
    """Add word breaks to long words in a run of text.

    The text may contain entity references or HTML tags.
    """
    def replace(match):
        if match.group('tag'):
            return match.group()
        elif match.group('longword'):
            return add_word_breaks(match.group())
        else:
            raise AssertionError('text matched but neither named group found')
    return break_text_pat.sub(replace, text)


class FormattersAPI:
    """Adapter from strings to HTML formatted text."""

    implements(ITraversable)

    def __init__(self, stringtoformat):
        self._stringtoformat = stringtoformat

    def nl_to_br(self):
        """Quote HTML characters, then replace newlines with <br /> tags."""
        return cgi.escape(self._stringtoformat).replace('\n','<br />\n')

    def escape(self):
        return escape(self._stringtoformat)

    def break_long_words(self):
        """Add manual word breaks to long words."""
        return break_long_words(cgi.escape(self._stringtoformat))

    @staticmethod
    def _substitute_matchgroup_for_spaces(match):
        """Return a string made up of '&nbsp;' for each character in the
        first match group.

        Used when replacing leading spaces with nbsps.

        There must be only one match group.
        """
        groups = match.groups()
        assert len(groups) == 1
        return '&nbsp;' * len(groups[0])

    @staticmethod
    def _split_url_and_trailers(url):
        """Given a URL return a tuple of the URL and punctuation trailers.

        :return: an unescaped url, an unescaped trailer.
        """
        # The text will already have been cgi escaped.  We temporarily
        # unescape it so that we can strip common trailing characters
        # that aren't part of the URL.
        url = xml_unescape(url)
        match = FormattersAPI._re_url_trailers.search(url)
        if match:
            trailers = match.group(1)
            url = url[:-len(trailers)]
        else:
            trailers = ''
        return url, trailers

    @staticmethod
    def _linkify_bug_number(text, bugnum, trailers=''):
        # XXX Brad Bollenbach 2006-04-10: Use a hardcoded url so
        # we still have a link for bugs that don't exist.
        url = '/bugs/%s' % bugnum

        bugset = getUtility(IBugSet)
        try:
            bug = bugset.get(bugnum)
        except NotFoundError:
            title = "No such bug"
        else:
            try:
                title = bug.title
            except Unauthorized:
                title = "private bug"
        title = cgi.escape(title, quote=True)
        # The text will have already been cgi escaped.
        return '<a href="%s" title="%s">%s</a>%s' % (
            url, title, text, trailers)

    @staticmethod
    def _linkify_substitution(match):
        if match.group('bug') is not None:
            return FormattersAPI._linkify_bug_number(
                match.group('bug'), match.group('bugnum'))
        elif match.group('url') is not None:
            # The text will already have been cgi escaped.  We temporarily
            # unescape it so that we can strip common trailing characters
            # that aren't part of the URL.
            url = match.group('url')
            url, trailers = FormattersAPI._split_url_and_trailers(url)
            # We use nofollow for these links to reduce the value of
            # adding spam URLs to our comments; it's a way of moderately
            # devaluing the return on effort for spammers that consider
            # using Launchpad.
            return '<a rel="nofollow" href="%s">%s</a>%s' % (
                cgi.escape(url, quote=True),
                add_word_breaks(cgi.escape(url)),
                cgi.escape(trailers))
        elif match.group('faq') is not None:
            text = match.group('faq')
            faqnum = match.group('faqnum')
            faqset = getUtility(IFAQSet)
            faq = faqset.getFAQ(faqnum)
            if not faq:
                return text
            url = canonical_url(faq)
            return '<a href="%s">%s</a>' % (url, text)
        elif match.group('oops') is not None:
            text = match.group('oops')

            if not getUtility(ILaunchBag).developer:
                return text

            root_url = config.launchpad.oops_root_url
            url = root_url + match.group('oopscode')
            return '<a href="%s">%s</a>' % (url, text)
        elif match.group('lpbranchurl') is not None:
            lp_url = match.group('lpbranchurl')
            path = match.group('branch')
            lp_url, trailers = FormattersAPI._split_url_and_trailers(lp_url)
            path, trailers = FormattersAPI._split_url_and_trailers(path)
            if path.isdigit():
                return FormattersAPI._linkify_bug_number(
                    lp_url, path, trailers)
            url = '/+branch/%s' % path
            return '<a href="%s">%s</a>%s' % (
                cgi.escape(url, quote=True),
                cgi.escape(lp_url),
                cgi.escape(trailers))
        else:
            raise AssertionError("Unknown pattern matched.")

    # match whitespace at the beginning of a line
    _re_leadingspace = re.compile(r'^(\s+)')

    # From RFC 3986 ABNF for URIs:
    #
    #   URI           = scheme ":" hier-part [ "?" query ] [ "#" fragment ]
    #   hier-part     = "//" authority path-abempty
    #                 / path-absolute
    #                 / path-rootless
    #                 / path-empty
    #
    #   authority     = [ userinfo "@" ] host [ ":" port ]
    #   userinfo      = *( unreserved / pct-encoded / sub-delims / ":" )
    #   host          = IP-literal / IPv4address / reg-name
    #   reg-name      = *( unreserved / pct-encoded / sub-delims )
    #   port          = *DIGIT
    #
    #   path-abempty  = *( "/" segment )
    #   path-absolute = "/" [ segment-nz *( "/" segment ) ]
    #   path-rootless = segment-nz *( "/" segment )
    #   path-empty    = 0<pchar>
    #
    #   segment       = *pchar
    #   segment-nz    = 1*pchar
    #   pchar         = unreserved / pct-encoded / sub-delims / ":" / "@"
    #
    #   query         = *( pchar / "/" / "?" )
    #   fragment      = *( pchar / "/" / "?" )
    #
    #   unreserved    = ALPHA / DIGIT / "-" / "." / "_" / "~"
    #   pct-encoded   = "%" HEXDIG HEXDIG
    #   sub-delims    = "!" / "$" / "&" / "'" / "(" / ")"
    #                 / "*" / "+" / "," / ";" / "="
    #
    # We only match a set of known scheme names too.  We don't handle
    # IP-literal either.
    #
    # We will simplify "unreserved / pct-encoded / sub-delims" as the
    # following regular expression:
    #   [-a-zA-Z0-9._~%!$&'()*+,;=]
    #
    # We also require that the path-rootless form not begin with a
    # colon to avoid matching strings like "http::foo" (to avoid bug
    # #40255).
    #
    # The path-empty pattern is not matched either, due to false
    # positives.
    #
    # Some allowed URI punctuation characters will be trimmed if they
    # appear at the end of the URI since they may be incidental in the
    # flow of the text.
    #
    # apport has at one time produced query strings containing sqaure
    # braces (that are not percent-encoded). In RFC 2986 they seem to be
    # allowed by section 2.2 "Reserved Characters", yet section 3.4
    # "Query" appears to provide a strict definition of the query string
    # that would forbid square braces. Either way, links with
    # non-percent-encoded square braces are being used on Launchpad so
    # it's probably best to accomodate them.

    # Match urls or bugs or oopses.
    _re_linkify = re.compile(r'''
      (?P<url>
        \b
        (?:about|gopher|http|https|sftp|news|ftp|mailto|file|irc|jabber)
        :
        (?:
          (?:
            # "//" authority path-abempty
            //
            (?: # userinfo
              [%(unreserved)s:]*
              @
            )?
            (?: # host
              \d+\.\d+\.\d+\.\d+ |
              [%(unreserved)s]*
            )
            (?: # port
              : \d*
            )?
            (?: / [%(unreserved)s:@]* )*
          ) | (?:
            # path-absolute
            /
            (?: [%(unreserved)s:@]+
                (?: / [%(unreserved)s:@]* )* )?
          ) | (?:
            # path-rootless
            [%(unreserved)s@]
            [%(unreserved)s:@]*
            (?: / [%(unreserved)s:@]* )*
          )
        )
        (?: # query
          \?
          [%(unreserved)s:@/\?\[\]]*
        )?
        (?: # fragment
          \#
          [%(unreserved)s:@/\?]*
        )?
      ) |
      (?P<bug>
        \bbug(?:[\s=-]|<br\s*/>)*(?:\#|report|number\.?|num\.?|no\.?)?(?:[\s=-]|<br\s*/>)*
        0*(?P<bugnum>\d+)
      ) |
      (?P<faq>
        \bfaq(?:[\s=-]|<br\s*/>)*(?:\#|item|number\.?|num\.?|no\.?)?(?:[\s=-]|<br\s*/>)*
        0*(?P<faqnum>\d+)
      ) |
      (?P<oops>
        \boops\s*-?\s*
        (?P<oopscode> \d* [a-z]+ \d+)
      ) |
      (?P<lpbranchurl>
        \blp:(?:///|/)?
        (?P<branch>[%(unreserved)s][%(unreserved)s/]*)
      )
    ''' % {'unreserved': "-a-zA-Z0-9._~%!$&'()*+,;="},
                             re.IGNORECASE | re.VERBOSE)

    # a pattern to match common trailing punctuation for URLs that we
    # don't want to include in the link.
    _re_url_trailers = re.compile(r'([,.?:);>]+)$')

    def text_to_html(self):
        """Quote text according to DisplayingParagraphsOfText."""
        # This is based on the algorithm in the
        # DisplayingParagraphsOfText spec, but is a little more
        # complicated.

        # 1. Blank lines are used to detect paragraph boundaries.
        # 2. Two lines are considered to be part of the same logical line
        #    only if the first is between 60 and 80 characters and the
        #    second does not begin with white space.
        # 3. Use <br /> to split logical lines within a paragraph.
        output = []
        first_para = True
        for para in split_paragraphs(self._stringtoformat):
            if not first_para:
                output.append('\n')
            first_para = False
            output.append('<p>')
            first_line = True
            for line in para:
                if not first_line:
                    output.append('<br />\n')
                first_line = False
                # escape ampersands, etc in text
                line = cgi.escape(line)
                # convert leading space in logical line to non-breaking space
                line = self._re_leadingspace.sub(
                    self._substitute_matchgroup_for_spaces, line)
                output.append(line)
            output.append('</p>')

        text = ''.join(output)

        # Linkify the text.
        text = re_substitute(self._re_linkify, self._linkify_substitution,
                             break_long_words, text)

        return text

    def nice_pre(self):
        """<pre>, except the browser knows it is allowed to break long lines

        Note that CSS will eventually have a property to specify this
        behaviour, but we want this now. To do this we need to use the mozilla
        specific -moz-pre-wrap value of the white-space property. We try to
        fall back for IE by using the IE specific word-wrap property.

        TODO: Test IE compatibility. StuartBishop 20041118
        TODO: This should probably just live in the stylesheet if this
            CSS implementation is good enough. StuartBishop 20041118
        """
        if not self._stringtoformat:
            return self._stringtoformat
        else:
            linkified_text = re_substitute(self._re_linkify,
                self._linkify_substitution, break_long_words,
                cgi.escape(self._stringtoformat))
            return ('<pre style="'
                    'white-space: -moz-pre-wrap;'
                    'white-space: -o-pre-wrap;'
                    'word-wrap: break-word;'
                    '">%s</pre>'
                    % linkified_text
                    )

    # Match lines that start with one or more quote symbols followed
    # by a space. Quote symbols are commonly '|', or '>'; they are
    # used for quoting passages from another email. Both '>> ' and
    # '> > ' are valid quoting sequences.
    # The dpkg version is used for exceptional cases where it
    # is better to not assume '|' is a start of a quoted passage.
    _re_quoted = re.compile('^(([|] ?)+|(&gt; ?)+)')
    _re_dpkg_quoted = re.compile('^(&gt; ?)+ ')

    # Match blocks that start as signatures or PGP inclusions.
    _re_include = re.compile('^<p>(--<br />|-----BEGIN PGP)')

    def email_to_html(self):
        """text_to_html and hide signatures and full-quoted emails.

        This method wraps inclusions like signatures and PGP blocks in
        <span class="foldable"></span> tags. Quoted passages are wrapped
        <span class="foldable-quoted"></span> tags. The tags identify the
        extra content in the message to the presentation layer. CSS and
        JavaScript may use this markup to control the content's display
        behaviour.
        """
        start_fold_markup = '<span class="foldable">'
        start_fold_quoted_markup = '<span class="foldable-quoted">'
        end_fold_markup = '%s\n</span></p>'
        re_quoted = self._re_quoted
        re_include = self._re_include
        output = []
        in_fold = False
        in_quoted = False
        in_false_paragraph = False

        def is_quoted(line):
            """Test that a line is a quote and not Python.

            Note that passages may be wrongly be interpreted as Python
            because they start with '>>> '. The function does not check
            that next and previous lines of text consistently uses '>>> '
            as Python would.
            """
            python_block = '&gt;&gt;&gt; '
            return (not line.startswith(python_block)
                and re_quoted.match(line) is not None)

        def strip_leading_p_tag(line):
            """Return the characters after the paragraph mark (<p>).

            The caller must be certain the line starts with a paragraph mark.
            """
            assert line.startswith('<p>'), (
                "The line must start with a paragraph mark (<p>).")
            return line[3:]

        def strip_trailing_p_tag(line):
            """Return the characters before the line paragraph mark (</p>).

            The caller must be certain the line ends with a paragraph mark.
            """
            assert line.endswith('</p>'), (
                "The line must end with a paragraph mark (</p>).")
            return line[:-4]

        for line in self.text_to_html().split('\n'):
            if 'Desired=<wbr></wbr>Unknown/' in line and not in_fold:
                # When we see a evidence of dpkg output, we switch the
                # quote matching rules. We do not assume lines that start
                # with a pipe are quoted passages. dpkg output is often
                # reformatted by users and tools. When we see the dpkg
                # output header, we change the rules regardless of if the
                # lines that follow are legitimate.
                re_quoted = self._re_dpkg_quoted
            elif not in_fold and re_include.match(line) is not None:
                # This line is a paragraph with a signature or PGP inclusion.
                # Start a foldable paragraph.
                in_fold = True
                line = '<p>%s%s' % (start_fold_markup,
                                    strip_leading_p_tag(line))
            elif (not in_fold and line.startswith('<p>')
                and is_quoted(strip_leading_p_tag(line))):
                # The paragraph starts with quoted marks.
                # Start a foldable quoted paragraph.
                in_fold = True
                line = '<p>%s%s' % (
                    start_fold_quoted_markup, strip_leading_p_tag(line))
            elif not in_fold and is_quoted(line):
                # This line in the paragraph is quoted.
                # Start foldable quoted lines in a paragraph.
                in_quoted = True
                in_fold = True
                output.append(start_fold_quoted_markup)
            else:
                # This line is continues the current state.
                # This line is not a transition.
                pass

            # We must test line starts and ends in separate blocks to
            # close the rare single line that is foldable.
            if in_fold and line.endswith('</p>') and in_false_paragraph:
                # The line ends with a false paragraph in a PGP signature.
                # Restore the line break to join with the next paragraph.
                line = '%s<br />\n<br />' %  strip_trailing_p_tag(line)
            elif (in_quoted and self._re_quoted.match(line) is None):
                # The line is not quoted like the previous line.
                # End fold before we append this line.
                in_fold = False
                in_quoted = False
                output.append("</span>\n")
            elif in_fold and line.endswith('</p>'):
                # The line is quoted or an inclusion, and ends the paragraph.
                # End the fold before the close paragraph mark.
                in_fold = False
                in_quoted = False
                line = end_fold_markup % strip_trailing_p_tag(line)
            elif in_false_paragraph and line.startswith('<p>'):
                # This line continues a PGP signature, but starts a paragraph.
                # Remove the paragraph to join with the previous paragraph.
                in_false_paragraph = False
                line = strip_leading_p_tag(line)
            else:
                # This line is continues the current state.
                # This line is not a transition.
                pass

            if in_fold and 'PGP SIGNATURE' in line:
                # PGP signature blocks are split into two paragraphs
                # by the text_to_html. The foldable feature works with
                # a single paragraph, so we merge this paragraph with
                # the next one.
                in_false_paragraph = True

            output.append(line)
        return '\n'.join(output)

    # This is a regular expression that matches email address embedded in
    # text. It is not RFC 2821 compliant, nor does it need to be. This
    # expression strives to identify probable email addresses so that they
    # can be obfuscated when viewed by unauthenticated users. See
    # http://www.email-unlimited.com/stuff/email_address_validator.htm

    # localnames do not have [&?%!@<>,;:`|{}()#*^~ ] in practice
    # (regardless of RFC 2821) because they conflict with other systems.
    # See https://lists.ubuntu.com
    #     /mailman/private/launchpad-reviews/2007-June/006081.html

    # This verson of the re is more than 5x faster that the orginal
    # version used in ftest/test_tales.testObfuscateEmail.
    _re_email = re.compile(r"""
        \b[a-zA-Z0-9._/="'+-]{1,64}@  # The localname.
        [a-zA-Z][a-zA-Z0-9-]{1,63}    # The hostname.
        \.[a-zA-Z0-9.-]{1,251}\b      # Dot starts one or more domains.
        """, re.VERBOSE)

    def obfuscate_email(self):
        """Obfuscate an email address if there's no authenticated user.

        The email address is obfuscated as <email address hidden>.

        This formatter is intended to hide possible email addresses from
        unauthenticated users who view this text on the Web. Run this before
        the text is converted to html because text-to-html and email-to-html
        will insert markup into the address. eg.
        foo/fmt:obfuscate-email/fmt:email-to-html

        The pattern used to identify an email address is not 2822. It strives
        to match any possible email address embedded in the text. For example,
        mailto:person@domain.dom and http://person:password@domain.dom both
        match, though the http match is in fact not an email address.
        """
        if getUtility(ILaunchBag).user is not None:
            return self._stringtoformat
        text = self._re_email.sub(
            r'<email address hidden>', self._stringtoformat)
        text = text.replace(
            "<<email address hidden>>", "<email address hidden>")
        return text

    def linkify_email(self):
        """Linkify any email address recognised in Launchpad.

        If an email address is recognised as one registered in Launchpad,
        it is linkified to point to the profile page for that person.

        Note that someone could theoretically register any old email
        address in Launchpad and then have it linkified.  This may or not
        may be a concern but is noted here for posterity anyway.
        """
        text = self._stringtoformat

        matches = re.finditer(self._re_email, text)
        for match in matches:
            address = match.group()
            person = getUtility(IPersonSet).getByEmail(address)
            # Only linkify if person exists and does not want to hide
            # their email addresses.
            if person is not None and not person.hide_email_addresses:
                person_formatter = PersonFormatterAPI(person)
                image_html = ObjectImageDisplayAPI(person).icon()
                text = text.replace(address, '<a href="%s">%s&nbsp;%s</a>' % (
                    canonical_url(person), image_html, address))
        return text

    def lower(self):
        """Return the string in lowercase"""
        return self._stringtoformat.lower()

    def shorten(self, maxlength):
        """Use like tal:content="context/foo/fmt:shorten/60"."""
        if len(self._stringtoformat) > maxlength:
            return '%s...' % self._stringtoformat[:maxlength-3]
        else:
            return self._stringtoformat

    def format_diff(self):
        """Format the string as a diff in a table with line numbers."""
        # Trim off trailing carriage returns.
        text = self._stringtoformat.rstrip('\n')
        if len(text) == 0:
            return text
        result = ['<table class="diff">']

        for row, line in enumerate(text.split('\n')):
            result.append('<tr>')
            result.append('<td class="line-no">%s</td>' % (row+1))
            if line.startswith('==='):
                css_class = 'diff-file text'
            elif (line.startswith('+++') or
                  line.startswith('---')):
                css_class = 'diff-header text'
            elif line.startswith('@@'):
                css_class = 'diff-chunk text'
            elif line.startswith('+'):
                css_class = 'diff-added text'
            elif line.startswith('-'):
                css_class = 'diff-removed text'
            elif line.startswith('#'):
                # This doesn't occur in normal unified diffs, but does
                # appear in merge directives, which use text/x-diff or
                # text/x-patch.
                css_class = 'diff-comment text'
            else:
                css_class = 'text'
            result.append(
                '<td class="%s">%s</td>' % (css_class, escape(line)))
            result.append('</tr>')

        result.append('</table>')
        return ''.join(result)


    def traverse(self, name, furtherPath):
        if name == 'nl_to_br':
            return self.nl_to_br()
        elif name == 'escape':
            return self.escape()
        elif name == 'lower':
            return self.lower()
        elif name == 'break-long-words':
            return self.break_long_words()
        elif name == 'text-to-html':
            return self.text_to_html()
        elif name == 'nice_pre':
            return self.nice_pre()
        elif name == 'email-to-html':
            return self.email_to_html()
        elif name == 'obfuscate-email':
            return self.obfuscate_email()
        elif name == 'linkify-email':
            return self.linkify_email()
        elif name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            maxlength = int(furtherPath.pop())
            return self.shorten(maxlength)
        elif name == 'diff':
            return self.format_diff()
        else:
            raise TraversalError(name)


class PermissionRequiredQuery:
    """Check if the logged in user has a given permission on a given object.

    Example usage::
        tal:condition="person/required:launchpad.Edit"
    """

    implements(ITraversable)

    def __init__(self, context):
        self.context = context

    def traverse(self, name, furtherPath):
        if len(furtherPath) > 0:
            raise TraversalError(
                    "There should be no further path segments after "
                    "required:permission")
        return check_permission(name, self.context)


class PageMacroDispatcher:
    """Selects a macro, while storing information about page layout.

        view/macro:page
        view/macro:page/onecolumn
        view/macro:page/applicationhome
        view/macro:page/pillarindex
        view/macro:page/freeform

        view/macro:pagehas/applicationtabs
        view/macro:pagehas/applicationborder
        view/macro:pagehas/applicationbuttons
        view/macro:pagehas/globalsearch
        view/macro:pagehas/heading
        view/macro:pagehas/pageheading
        view/macro:pagehas/portlets

        view/macro:pagetype

    """

    implements(ITraversable)

    master = ViewPageTemplateFile('../templates/main-template.pt')

    def __init__(self, context):
        # The context of this object is a view object.
        self.context = context

    def traverse(self, name, furtherPath):
        if name == 'page':
            if len(furtherPath) == 1:
                pagetype = furtherPath.pop()
            elif not furtherPath:
                pagetype = 'default'
            else:
                raise TraversalError("Max one path segment after macro:page")

            return self.page(pagetype)
        elif name == 'pagehas':
            if len(furtherPath) != 1:
                raise TraversalError(
                    "Exactly one path segment after macro:haspage")

            layoutelement = furtherPath.pop()
            return self.haspage(layoutelement)
        elif name == 'pagetype':
            return self.pagetype()
        elif name == 'show_actions_menu':
            return self.show_actions_menu()
        else:
            raise TraversalError(name)

    def page(self, pagetype):
        if pagetype not in self._pagetypes:
            raise TraversalError('unknown pagetype: %s' % pagetype)
        self.context.__pagetype__ = pagetype
        return self.master.macros['master']

    def haspage(self, layoutelement):
        pagetype = getattr(self.context, '__pagetype__', None)
        if pagetype is None:
            pagetype = 'unset'
        return self._pagetypes[pagetype][layoutelement]

    def pagetype(self):
        return getattr(self.context, '__pagetype__', 'unset')

    class LayoutElements:

        def __init__(self,
            applicationtabs=False,
            applicationborder=False,
            applicationbuttons=False,
            globalsearch=False,
            heading=False,
            pageheading=True,
            portlets=False,
            pagetypewasset=True,
            actionsmenu=True,
            navigationtabs=False
            ):
            self.elements = vars()

        def __getitem__(self, name):
            return self.elements[name]

    _pagetypes = {
        'unset':
            LayoutElements(
                applicationborder=True,
                applicationtabs=True,
                globalsearch=True,
                portlets=True,
                pagetypewasset=False),
        'default':
            LayoutElements(
                applicationborder=True,
                applicationtabs=True,
                globalsearch=True,
                portlets=True),
        'default2.0':
            LayoutElements(
                actionsmenu=False,
                applicationborder=True,
                applicationtabs=True,
                globalsearch=True,
                portlets=True,
                navigationtabs=True),
        'onecolumn':
            # XXX 20080130 mpt: Should eventually become the new 'default'.
            LayoutElements(
                actionsmenu=False,
                applicationborder=True,
                applicationtabs=True,
                globalsearch=True,
                navigationtabs=True,
                portlets=False),
        'applicationhome':
            LayoutElements(
                applicationborder=True,
                applicationbuttons=True,
                applicationtabs=True,
                globalsearch=True,
                pageheading=False,
                heading=True),
        'pillarindex':
            LayoutElements(
                applicationborder=True,
                applicationbuttons=True,
                globalsearch=True,
                heading=True,
                pageheading=False,
                portlets=True),
        'search':
            LayoutElements(
                actionsmenu=False,
                applicationborder=True,
                applicationtabs=True,
                globalsearch=False,
                heading=False,
                pageheading=False,
                portlets=False),
       'freeform':
            LayoutElements(),
        }

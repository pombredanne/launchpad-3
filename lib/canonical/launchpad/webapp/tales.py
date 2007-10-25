# Copyright 2004 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0613,E0201,R0911
#
"""Implementation of the lp: htmlform: fmt: namespaces in TALES.

"""
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

from zope.interface import Interface, Attribute, implements
from zope.component import getUtility, queryAdapter
from zope.app import zapi
from zope.publisher.interfaces import IApplicationRequest
from zope.publisher.interfaces.browser import IBrowserApplicationRequest
from zope.app.traversing.interfaces import ITraversable
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.security.interfaces import Unauthorized
from zope.security.proxy import isinstance as zope_isinstance

import pytz

from canonical.config import config
from canonical.launchpad.interfaces import (
    BuildStatus,
    IBug,
    IBugAttachment,
    IBugNomination,
    IBugSet,
    IHasIcon,
    IHasLogo,
    IHasMugshot,
    IPerson,
    IProduct,
    IProject,
    ISprint,
    IDistribution,
    IStructuralHeaderPresentation,
    NotFoundError,
    )
from canonical.launchpad.webapp.interfaces import (
    IFacetMenu, IApplicationMenu, IContextMenu, NoCanonicalUrl, ILaunchBag)
from canonical.launchpad.webapp.vhosts import allvhosts
import canonical.launchpad.pagetitles
from canonical.lp import dbschema
from canonical.launchpad.webapp import (
    canonical_url, nearest_context_with_adapter, nearest_adapter)
from canonical.launchpad.webapp.uri import URI
from canonical.launchpad.webapp.publisher import (
    get_current_browser_request, nearest)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.badge import IHasBadges
from canonical.launchpad.webapp.session import get_cookie_domain
from canonical.lazr import enumerated_type_registry


class TraversalError(NotFoundError):
    """Remove this when we upgrade to a more recent Zope x3."""
    # XXX: Steve Alexander 2004-12-14:
    # Remove this when we upgrade to a more recent Zope x3.


class MenuAPI:
    """Namespace to give access to the facet menus.

       CONTEXTS/menu:facet       gives the facet menu of the nearest object
                                 along the canonical url chain that has an
                                 IFacetMenu adapter.

    """

    def __init__(self, context):
        if zope_isinstance(context, dict):
            # We have what is probably a CONTEXTS dict.
            # We get the context out of here, and use that for self.context.
            # We also want to see if the view has a __launchpad_facetname__
            # attribute.
            self._context = context['context']
            view = context['view']
            self._request = context['request']
            self._selectedfacetname = getattr(
                view, '__launchpad_facetname__', None)
        else:
            self._context = context
            self._request = get_current_browser_request()
            self._selectedfacetname = None

    def _nearest_menu(self, menutype):
        try:
            return nearest_adapter(self._context, menutype)
        except NoCanonicalUrl:
            return None

    def _requesturi(self):
        request = self._request
        if request is None:
            return None
        requesturiobj = URI(request.getURL())
        # If the default view name is being used, we will want the url
        # without the default view name.
        defaultviewname = zapi.getDefaultViewName(self._context, request)
        if requesturiobj.path.rstrip('/').endswith(defaultviewname):
            requesturiobj = URI(request.getURL(1))
        query = request.get('QUERY_STRING')
        if query:
            requesturiobj = requesturiobj.replace(query=query)
        return requesturiobj

    def facet(self):
        menu = self._nearest_menu(IFacetMenu)
        if menu is None:
            return []
        else:
            menu.request = self._request
            return list(menu.iterlinks(
                requesturi=self._requesturi(),
                selectedfacetname=self._selectedfacetname))

    def selectedfacetname(self):
        if self._selectedfacetname is None:
            return 'unknown'
        else:
            return self._selectedfacetname

    def application(self):
        selectedfacetname = self._selectedfacetname
        if selectedfacetname is None:
            # No facet menu is selected.  So, return empty list.
            return []
        menu = queryAdapter(
            self._context, IApplicationMenu, selectedfacetname)
        if menu is None:
            return []
        else:
            menu.request = self._request
            return list(menu.iterlinks(requesturi=self._requesturi()))

    def context(self):
        menu = IContextMenu(self._context, None)
        if menu is None:
            return  []
        else:
            menu.request = self._request
            return list(menu.iterlinks(requesturi=self._requesturi()))


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
    """Namespace to test whether an EnumeratedType Item has a particular value.

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
            # Check whether this was an allowed value for this enumerated type.
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
        'breadcrumbs',
        'break-long-words',
        'date',
        'datetime',
        'displaydate',
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
    """Adapter from any object to a formatted string.

    Used for fmt:url.
    """

    def __init__(self, context):
        self._context = context

    def url(self):
        request = get_current_browser_request()
        return canonical_url(
            self._context, request, path_only_if_possible=True)


class ObjectFormatterExtendedAPI(ObjectFormatterAPI):
    """Adapter for any object to a formatted string.

    Adds fmt:link which shows the icon and formatted string in an anchor.
    """

    implements(ITraversable)

    allowed_names = set([
        'url',
        ])

    def traverse(self, name, furtherPath):
        if name == 'link':
            extra_path = '/'.join(reversed(furtherPath))
            del furtherPath[:]
            return self.link(extra_path)
        elif name in self.allowed_names:
            return getattr(self, name)()
        else:
            raise TraversalError, name

    def link(self, extra_path):
        """Return an HTML link to the person's page containing an icon
        followed by the person's name.
        """
        raise NotImplemented


class ObjectImageDisplayAPI:
    """Base class for producing the HTML that presents objects
    as an icon, a logo, a mugshot or a set of badges.
    """

    def __init__(self, context):
        self._context = context

    def default_icon_resource(self, context):
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
        return '/@@/nyet-icon'

    def default_logo_resource(self, context):
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
        return '/@@/nyet-logo'

    def default_mugshot_resource(self, context):
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
        return '/@@/nyet-mugshot'

    def icon(self, rootsite=None):
        """Return the appropriate <img> tag for this object's icon."""
        context = self._context
        if context is None:
            # we handle None specially and return an empty string
            return ''
        if IHasIcon.providedBy(context) and context.icon is not None:
            url = context.icon.getURL()
        else:
            if rootsite is None:
                root_url = ''
            else:
                root_url = allvhosts.configs[rootsite].rooturl[:-1]
            url = root_url + self.default_icon_resource(context)
        icon = '<img alt="" width="14" height="14" src="%s" />'
        return icon % url

    def logo(self):
        """Return the appropriate <img> tag for this object's logo."""
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
        logo = '<img alt="" width="64" height="64" src="%s" />'
        return logo % url

    def mugshot(self):
        """Return the appropriate <img> tag for this object's mugshot."""
        context = self._context
        assert IHasMugshot.providedBy(context), 'No Mugshot for this item'
        if context.mugshot is not None:
            url = context.mugshot.getURL()
        else:
            url = self.default_mugshot_resource(context)
        mugshot = """<div style="width: 200; height: 200; float: right">
            <img alt="" width="192" height="192" src="%s" />
            </div>"""
        return mugshot % url

    def badges(self):
        raise NotImplementedError(
            "Badge display not implemented for this item")


class PillarSearchItemAPI(ObjectImageDisplayAPI):
    """Provides image:icon for a PillarSearchItem."""

    def mugshot(self):
        raise NotImplementedError("A PillarSearchItem doesn't have a mugshot")

    def logo(self):
        raise NotImplementedError("A PillarSearchItem doesn't have a logo")


class BugTaskImageDisplayAPI(ObjectImageDisplayAPI):
    """Adapter for IBugTask objects to a formatted string. This inherits
    from the generic ObjectImageDisplayAPI and overrides the icon
    presentation method.

    Used for image:icon.
    """
    implements(ITraversable)

    icon_template = (
        '<img height="14" width="14" alt="%s" title="%s" src="%s" />')

    def traverse(self, name, furtherPath):
        """Special-case traversal for icons with an optional rootsite."""
        if name == 'icon':
            return self.icon()
        elif name.startswith('icon:'):
            rootsite = name.split(':', 1)[1]
            return self.icon(rootsite=rootsite)
        elif name == 'badges':
            return self.badges()
        else:
            return None

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


    def badges(self):

        badges = ''
        if self._context.bug.private:
            badges += self.icon_template % (
                "private", "Private","/@@/private")

        if self._context.bug.mentoring_offers.count() > 0:
            badges += self.icon_template % (
                "mentoring", "Mentoring offered", "/@@/mentoring")

        if self._context.bug.bug_branches.count() > 0:
            badges += self.icon_template % (
                "branch", "Branch exists", "/@@/branch")

        if self._context.bug.specifications.count() > 0:
            badges += self.icon_template % (
                "blueprint", "Related to a blueprint", "/@@/blueprint")

        return badges


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
        'translations': '/@@/translation',
        'specs': '/@@/blueprint',
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
            BuildStatus.FAILEDTOBUILD: "/@@/build-failure",
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


class PersonFormatterAPI(ObjectFormatterExtendedAPI):
    """Adapter for `IPerson` objects to a formatted string."""

    implements(ITraversable)

    allowed_names = set([
        'url',
        ])

    def traverse(self, name, furtherPath):
        """Special-case traversal for links with an optional rootsite."""
        extra_path = '/'.join(reversed(furtherPath))
        if name == 'link':
            # Remove remaining entries in furtherPath so that traversal
            # stops here.
            del furtherPath[:]
            return self.link(extra_path)
        elif name.startswith('link:'):
            # Remove remaining entries in furtherPath so that traversal
            # stops here.
            del furtherPath[:]
            rootsite = name.split(':')[1]
            return self.link(extra_path, rootsite=rootsite)
        elif name in self.allowed_names:
            return getattr(self, name)()
        else:
            raise TraversalError(name)

    def link(self, extra_path, rootsite=None):
        """Return an HTML link to the person's page containing an icon
        followed by the person's name.
        """
        person = self._context
        url = canonical_url(person, rootsite=rootsite)
        if extra_path:
            url = '%s/%s' % (url, extra_path)
        image_html = ObjectImageDisplayAPI(person).icon(rootsite=rootsite)
        return '<a href="%s">%s&nbsp;%s</a>' % (
            url, image_html, person.browsername)


class BranchFormatterAPI(ObjectFormatterExtendedAPI):
    """Adapter for IBranch objects to a formatted string."""

    def link(self, extra_path):
        """Return an HTML link to the branch page containing an icon
        followed by the branch's unique name.
        """
        branch = self._context
        url = canonical_url(branch)
        if extra_path:
            url = '%s/%s' % (url, extra_path)
        return ('<a href="%s" title="%s"><img src="/@@/branch" alt=""/>'
                '&nbsp;%s</a>' % (url, branch.displayname, branch.unique_name))


class BugFormatterAPI(ObjectFormatterExtendedAPI):
    """Adapter for IBug objects to a formatted string."""

    def link(self, extra_path):
        """Return an HTML link to the bug page containing an icon
        followed by the bug's title.
        """
        bug = self._context
        url = canonical_url(bug)
        if extra_path:
            url = '%s/%s' % (url, extra_path)
        return ('<a href="%s"><img src="/@@/bug" alt=""/>'
                '&nbsp;Bug #%d: %s</a>' % (url, bug.id, bug.title))


class BugTaskFormatterAPI(ObjectFormatterExtendedAPI):
    """Adapter for IBugTask objects to a formatted string."""

    def link(self, extra_path):
        """Return an HTML link to the bug task's page containing an icon
        appropriate to the importance of the bug task.
        """
        bugtask = self._context
        url = canonical_url(bugtask)
        if extra_path:
            url = '%s/%s' % (url, extra_path)
        image_html = BugTaskImageDisplayAPI(bugtask).icon()
        return '<a href="%s">%s&nbsp;Bug #%d: %s</a>' % (
            url, image_html, bugtask.bug.id, bugtask.bug.title)


class NumberFormatterAPI:
    """Adapter for converting numbers to formatted strings."""

    def __init__(self, number):
        assert not float(number) < 0, "Expected a non-negative number."
        self._number = number

    def bytes(self):
        """Render number as byte contractions according to IEC60027-2."""
        # See http://en.wikipedia.org/wiki
        # /Binary_prefixes#Specific_units_of_IEC_60027-2_A.2
        # Note that there is a zope.app.size.byteDisplay() function, but
        # it really limited and doesn't work well enough for us here.
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


class DateTimeFormatterAPI:
    """Adapter from datetime objects to a formatted string."""

    def __init__(self, datetimeobject):
        self._datetime = datetimeobject

    def time(self):
        if self._datetime.tzinfo:
            value = self._datetime.astimezone(getUtility(ILaunchBag).timezone)
            return value.strftime('%T %Z')
        else:
            return self._datetime.strftime('%T')

    def date(self):
        value = self._datetime
        if value.tzinfo:
            value = value.astimezone(getUtility(ILaunchBag).timezone)
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
        if amount > 1:
            s = 's'
        else:
            s = ''
        result += '%s %s%s' % (amount, unit, s)
        if not future:
            result += ' ago'
        return result

    def datetime(self):
        return "%s %s" % (self.date(), self.time())

    def rfc822utcdatetime(self):
        return formatdate(
            rfc822.mktime_tz(self._datetime.utctimetuple() + (0,)))


class DurationFormatterAPI:
    """Adapter from timedelta objects to a formatted string."""

    def __init__(self, duration):
        self._duration = duration

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

    def approximateduration(self):
        """Return a nicely-formatted approximate duration.

        E.g. 'an hour', 'three minutes', '1 hour 10 minutes' and so
        forth.

        See https://launchpad.canonical.com/PresentingLengthsOfTime.
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
        representation_in_seconds = (
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
        )

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
        number_name = {
            2: 'two', 3: 'three', 4: 'four', 5: 'five',
            6: 'six', 7: 'seven', 8: 'eight', 9: 'nine',
            10: 'ten'}

        # Convert seconds into minutes, and round it.
        minutes, remaining_seconds = divmod(seconds, 60)
        minutes += remaining_seconds / 60.0
        minutes = int(round(minutes))

        if minutes <= 59:
            number_as_text = number_name.get(minutes, str(minutes))
            return number_as_text + " minutes"

        # Is the duration less than an hour and 5 minutes?
        if seconds < (60 + 5) * 60:
            return "an hour"

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
            return 'ten hours'

        # Try to calculate the approximate number of hours, to a
        # maximum of 47.
        hours = int(round(seconds / 3600.0))
        if hours <= 47:
            return "%d hours" % hours

        # Is the duration fewer than two and a half days?
        if seconds < (2.5 * 24 * 3600):
            return 'two days'

        # Try to approximate to day granularity, up to a maximum of 13
        # days.
        days = int(round(seconds / (24 * 3600)))
        if days <= 13:
            return "%s days" % number_name.get(days, str(days))

        # Is the duration fewer than two and a half weeks?
        if seconds < (2.5 * 7 * 24 * 3600):
            return 'two weeks'

        # If we've made it this far, we'll calculate the duration to a
        # granularity of weeks, once and for all.
        weeks = int(round(seconds / (7 * 24 * 3600.0)))
        return "%s weeks" % number_name.get(weeks, str(weeks))


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

        If no suitable object is found in canonical.launchpad.pagetitles, emit a
        warning that this page has no title, and return the default page title.
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
    def _linkify_substitution(match):
        if match.group('bug') is not None:
            bugnum = match.group('bugnum')
            # XXX Brad Bollenbach 2006-04-10: Use a hardcoded url so
            # we still have a link for bugs that don't exist.
            url = '/bugs/%s' % bugnum
            # The text will have already been cgi escaped.
            text = match.group('bug')
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
            return '<a href="%s" title="%s">%s</a>' % (url, title, text)
        elif match.group('url') is not None:
            # The text will already have been cgi escaped.  We temporarily
            # unescape it so that we can strip common trailing characters
            # that aren't part of the URL.
            url = xml_unescape(match.group('url'))
            match = FormattersAPI._re_url_trailers.search(url)
            if match:
                trailers = match.group(1)
                url = url[:-len(trailers)]
            else:
                trailers = ''
            return '<a rel="nofollow" href="%s">%s</a>%s' % (
                cgi.escape(url, quote=True),
                add_word_breaks(cgi.escape(url)),
                cgi.escape(trailers))
        elif match.group('oops') is not None:
            text = match.group('oops')

            if not getUtility(ILaunchBag).developer:
                return text

            root_url = config.launchpad.oops_root_url

            if not root_url.endswith('/'):
                root_url += '/'

            url = root_url + match.group('oopscode')
            return '<a rel="nofollow" href="%s">%s</a>' % (url, text)
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
        \bbug(?:\s|<br\s*/>)*(?:\#|report|number\.?|num\.?|no\.?)?(?:\s|<br\s*/>)*
        0*(?P<bugnum>\d+)
      ) |
      (?P<oops>
        \boops\s*-?\s*
        (?P<oopscode> \d* [a-z]+ \d+)
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
            return ('<pre style="'
                    'white-space: -moz-pre-wrap;'
                    'white-space: -o-pre-wrap;'
                    'word-wrap: break-word;'
                    '">%s</pre>'
                    % cgi.escape(self._stringtoformat)
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
                line = '<p>%s%s' % (start_fold_markup, strip_leading_p_tag(line))
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
        """Obfuscate an email address as '<email address hidden>'.

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
        text = self._re_email.sub(
            r'<email address hidden>', self._stringtoformat)
        text = text.replace(
            "<<email address hidden>>", "<email address hidden>")
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

    def traverse(self, name, furtherPath):
        if name == 'nl_to_br':
            return self.nl_to_br()
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
        elif name == 'shorten':
            if len(furtherPath) == 0:
                raise TraversalError(
                    "you need to traverse a number after fmt:shorten")
            maxlength = int(furtherPath.pop())
            return self.shorten(maxlength)
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
        view/macro:pagehas/structuralheaderobject

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

        if name == 'pagehas':
            if len(furtherPath) != 1:
                raise TraversalError(
                    "Exactly one path segment after macro:haspage")

            layoutelement = furtherPath.pop()
            return self.haspage(layoutelement)

        if name == 'pagetype':
            return self.pagetype()

        raise TraversalError()

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
            structuralheaderobject=False,
            pagetypewasset=True
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
                structuralheaderobject=True,
                pagetypewasset=False),
        'default':
            LayoutElements(
                applicationborder=True,
                applicationtabs=True,
                globalsearch=True,
                portlets=True,
                structuralheaderobject=True),
        'applicationhome':
            LayoutElements(
                applicationborder=True,
                applicationbuttons=True,
                pageheading=False,
                globalsearch=False,
                heading=True),
        'pillarindex':
            LayoutElements(
                applicationborder=True,
                applicationbuttons=True,
                globalsearch=False,
                heading=True,
                pageheading=False,
                portlets=True),
        'freeform':
            LayoutElements(),
        }


class GotoStructuralObject:
    """lp:structuralheaderobject, lp:structuralfooterobject

    Returns None when there is no structural object.
    """

    def __init__(self, context_dict):
        self.context = context_dict['context']
        self.view = context_dict['view']
        self.use_context = self._getUseContext()

    def _getUseContext(self):
        """Return the appropriate context to use.

        This works around the hack in bug-related views where the context
        is not the bugtask, but instead the bug.
        """
        if (IBug.providedBy(self.context) or
            IBugAttachment.providedBy(self.context) or
            IBugNomination.providedBy(self.context)):
            return self.view.current_bugtask
        else:
            return self.context

    @property
    def structuralfooterobject(self):
        # The structural object is the nearest object with a facet menu.
        try:
            menucontext, facetmenu = nearest_context_with_adapter(
                self.use_context, IFacetMenu)
        except NoCanonicalUrl:
            return None
        return menucontext

    @property
    def structuralheaderobject(self):
        try:
            headercontext, adapter = nearest_context_with_adapter(
                self.use_context, IStructuralHeaderPresentation)
        except NoCanonicalUrl:
            return None
        return headercontext

    @property
    def immediate_object_is_private(self):
        try:
            headercontext, adapter = nearest_context_with_adapter(
                self.use_context, IStructuralHeaderPresentation)
        except NoCanonicalUrl:
            return False
        return adapter.isPrivate()

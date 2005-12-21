# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Browser code for the launchpad application."""

__metaclass__ = type
__all__ = [
    'LoginStatus',
    'MaintenanceMessage',
    'MenuBox',
    'RosettaContextMenu',
    'MaloneContextMenu',
    'LaunchpadRootNavigation',
    'FOAFApplicationNavigation',
    'MaloneApplicationNavigation'
    ]

import cgi
import urllib
import os.path
from datetime import timedelta, datetime

from zope.app.datetimeutils import parseDatetimetz, tzinfo, DateTimeError
from zope.app.errorservice.interfaces import ILocalErrorReportingService
from zope.component import getUtility

import canonical.launchpad.layers
from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadRoot, IRosettaApplication,
    IMaloneApplication, IProductSet, IShipItApplication, IPersonSet,
    IDistributionSet, ISourcePackageNameSet, IBinaryPackageNameSet,
    IProjectSet, ILoginTokenSet, IKarmaActionSet, IPOTemplateNameSet,
    IBazaarApplication, ICodeOfConductSet, IMaloneApplication,
    IRegistryApplication, IRosettaApplication, ISpecificationSet,
    ISprintSet, ITicketSet, IFOAFApplication, IBuilderSet, IBountySet,
    IBugSet, IBugTrackerSet, ICveSet, IProduct, IProductSeries,
    IMilestone, IDistribution, IDistroRelease, IDistroArchRelease,
    IDistributionSourcePackage, ISourcePackage,
    IDistroArchReleaseBinaryPackage, IDistroReleaseBinaryPackage,
    IPerson, IProject, ISprint)
from canonical.launchpad.components.cal import MergedCalendar
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, ContextMenu, Link, LaunchpadView, Navigation,
    stepto, canonical_url)

# XXX SteveAlexander, 2005-09-22, this is imported here because there is no
#     general timedelta to duration format adapter available.  This should
#     be factored out into a generally available adapter for both this
#     code and for TALES namespace code to use.
#     Same for MenuAPI.
from canonical.launchpad.webapp.tales import DurationFormatterAPI, MenuAPI


class MaloneApplicationNavigation(Navigation):

    usedfor = IMaloneApplication

    newlayer = canonical.launchpad.layers.MaloneLayer

    @stepto('bugs')
    def bugs(self):
        return getUtility(IBugSet)

    @stepto('bugtrackers')
    def bugtrackers(self):
        return getUtility(IBugTrackerSet)

    @stepto('cve')
    def cve(self):
        return getUtility(ICveSet)

    @stepto('distros')
    def distros(self):
        return getUtility(IDistributionSet)

    @stepto('projects')
    def projects(self):
        return getUtility(IProjectSet)

    @stepto('products')
    def products(self):
        return getUtility(IProductSet)

    def traverse(self, name):
        if name.isdigit():
            # Make /bugs/$bug.id and /malone/$bug.id Just Work
            return getUtility(IBugSet).get(name)


class MenuBox(LaunchpadView):
    """View class that helps its template render the actions menu box.

    Nothing at all is rendered if there are no contextmenu items and also
    no applicationmenu items.

    If there is at least one item, the template is rendered.
    """

    usedfor = dict  # Really a TALES CONTEXTS object.

    def initialize(self):
        menuapi = MenuAPI(self.context)
        self.contextmenuitems = [
            link for link in menuapi.context() if link.enabled]
        self.applicationmenuitems = [
            link for link in menuapi.application() if link.enabled]

    def render(self):
        if not self.contextmenuitems and not self.applicationmenuitems:
            return ''
        else:
            return self.template()


class Breadcrumbs(LaunchpadView):
    """Page fragment to display the breadcrumbs text."""

    def render(self):
        """Render the breadcrumbs text.

        The breadcrumbs are taken from the request.breadcrumbs list.
        For each breadcrumb, breadcrumb.text is cgi escaped.  The last
        breadcrumb is made <strong>.
        """
        breadcrumbs = self.request.breadcrumbs
        if not breadcrumbs:
            return ''
        sep = '<span class="breadcrumbSeparator"> &raquo; </span>'
        crumbhtml = '<a href="%s">%s</a>'
        all_but_last = [
            crumbhtml % (breadcrumb.url, cgi.escape(breadcrumb.text))
            for breadcrumb in breadcrumbs[:-1]]
        lastcrumb = breadcrumbs[-1]
        last_htmltext = crumbhtml % (lastcrumb.url, cgi.escape(lastcrumb.text))
        last_htmltext = '<strong>%s</strong>' % last_htmltext
        return sep.join(all_but_last + [last_htmltext])


class SiteMap(LaunchpadView):
    """Page fragment to display the site map."""

    _pillars = [
        # (name, title, interface provided)
        ('product', 'Products',       IProductSet),
        ('distro',  'Distributions',  IDistributionSet),
        ('person',  'People',         IPersonSet),
        ('project', 'Product Groups', IProjectSet),
        ('sprint',  'Meetings',       ISprintSet),
        ]

    def product_subpillar_links(self):
        """Subpillars for the 'Products' pillar."""
        product, dummy = self.request.getNearest(IProduct)
        if product is None:
            product_url = None
        else:
            product_url = canonical_url(product)

        dummy, selected_iface = self.request.getNearest(
            IProductSeries, IMilestone)

        # Release Series
        self.subpillar_links.append(dict(
            target=None,
            text='Release Series',
            enabled=False, # no +series page
            selected=selected_iface == IProductSeries
            ))

        # Branches
        self.subpillar_links.append(dict(
            target='%s/+branches' % product_url,
            text='Branches',
            enabled=product is not None,
            selected=False # should be True if +code is being viewed
            ))

        # Milestones
        self.subpillar_links.append(dict(
            target=None,
            text='Milestones',
            enabled=False,
            selected=selected_iface == IMilestone
            ))

    def distro_subpillar_links(self):
        """Subpillars for the 'Distributions' pillar."""
        distro, dummy = self.request.getNearest(IDistribution)
        if distro is None:
            distro_url = None
        else:
            distro_url = canonical_url(distro)

        dummy, selected_iface = self.request.getNearest(
            IDistroRelease, IDistroArchRelease,
            IDistributionSourcePackage, ISourcePackage,
            IDistroArchReleaseBinaryPackage,
            IDistroReleaseBinaryPackage)

        # Releases
        self.subpillar_links.append(dict(
            target=None,
            text='Releases',
            enabled=False, # no specific page for distro releases
            selected=selected_iface == IDistroRelease
            ))

        # Ports
        self.subpillar_links.append(dict(
            target=None,
            text='Ports',
            enabled=False, # no specific page for ports
            selected=selected_iface == IDistroArchRelease
            ))

        # Source Packages
        self.subpillar_links.append(dict(
            target='%s/+search' % distro_url,
            text='Source Packages',
            enabled=distro is not None, 
            selected=selected_iface in [IDistributionSourcePackage,
                                        ISourcePackage]
            ))

        # Binary Packages
        self.subpillar_links.append(dict(
            target=None,
            text='Binary Packages',
            enabled=False, # no specific page for binpkgs
            selected=selected_iface in [IDistroArchReleaseBinaryPackage,
                                        IDistroReleaseBinaryPackage]
            ))

    def initialize(self):
        # get the current pillar
        pillar_ifaces = [provided_iface
                        for name, title, provided_iface in self._pillars]
        obj, selected_iface = self.request.getNearest(*pillar_ifaces)
        for name, title, provided_iface in self._pillars:
            if provided_iface == selected_iface:
                current_pillar = name
                break
        else:
            current_pillar = None

        self.pillar_links = []
        for name, title, provided_iface in self._pillars:
            self.pillar_links.append(dict(
                target=canonical_url(getUtility(provided_iface)),
                text=title,
                enabled=True,
                selected=name == current_pillar
                ))

        # call a function to create subpillar links
        self.subpillar_links = []
        function = getattr(self, '%s_subpillar_links' % current_pillar, None)
        if function is not None:
            function()


class MaintenanceMessage:
    """Display a maintenance message if the control file is present and
    it contains a valid iso format time.

    The maintenance message shows the approximate time before launchpad will
    be taken offline for maintenance.

    The control file is +maintenancetime.txt in the launchpad root.

    If there is no maintenance message, an empty string is returned.

    If the maintenance time is too far in the future, then an empty string
    is returned.

    If the maintenance time is in the past, then the maintenance message says
    that Launchpad will go offline "very very soon".

    If the text in the maintenance message is poorly formatted, then an
    empty string is returned, and a warning should be logged.
    """

    timelefttext = None

    notmuchtime = timedelta(seconds=30)
    toomuchtime = timedelta(seconds=1800)  # 30 minutes

    def __call__(self):
        if os.path.exists('+maintenancetime.txt'):
            message = file('+maintenancetime.txt').read()
            try:
                maintenancetime = parseDatetimetz(message)
            except DateTimeError:
                # XXX log a warning here.
                #     SteveAlexander, 2005-09-22
                return ''
            nowtz = datetime.utcnow().replace(tzinfo=tzinfo(0))
            timeleft = maintenancetime - nowtz
            if timeleft > self.toomuchtime:
                return ''
            elif timeleft < self.notmuchtime:
                self.timelefttext = 'very very soon'
            else:
                self.timelefttext = 'in %s' % (
                    DurationFormatterAPI(timeleft).approximateduration())
            return self.index()
        return ''


class LaunchpadRootFacets(StandardLaunchpadFacets):

    usedfor = ILaunchpadRoot

    enable_only = ['overview', 'bugs', 'support', 'bounties', 'specifications',
                   'translations', 'calendar']

    def overview(self):
        target = ''
        text = 'Overview'
        return Link(target, text)

    def translations(self):
        target = 'rosetta'
        text = 'Translations'
        return Link(target, text)

    def bugs(self):
        target = 'malone'
        text = 'Bugs'
        return Link(target, text)

    def support(self):
        target = 'support'
        text = 'Support'
        summary = 'Launchpad technical support tracker.'
        return Link(target, text, summary)

    def specifications(self):
        target = 'specs'
        text = 'Specifications'
        summary = 'Launchpad feature specification tracker.'
        return Link(target, text, summary)

    def bounties(self):
        target = 'bounties'
        text = 'Bounties'
        summary = 'The Launchpad Universal Bounty Tracker'
        return Link(target, text, summary)

    def calendar(self):
        target = 'calendar'
        text = 'Calendar'
        return Link(target, text)


class MaloneContextMenu(ContextMenu):
    usedfor = IMaloneApplication
    links = ['cvetracker']

    def cvetracker(self):
        text = 'CVE Tracker'
        return Link('cve/', text, icon='cve')


class RosettaContextMenu(ContextMenu):
    usedfor = IRosettaApplication
    links = ['about', 'preferences', 'imports']

    def upload(self):
        target = '+upload'
        text = 'Upload'
        return Link(target, text)

    def download(self):
        target = '+export'
        text = 'Download'
        return Link(target, text)

    def about(self):
        text = 'About Rosetta'
        return Link('+about', text)

    def preferences(self):
        text = 'Preferences'
        return Link('prefs', text)

    def imports(self):
        text = 'Import queue'
        return Link('imports', text)


class LoginStatus:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    @property
    def login_shown(self):
        return (self.user is None and
                '+login' not in self.request['PATH_INFO'])

    @property
    def logged_in(self):
        return self.user is not None

    @property
    def login_url(self):
        query_string = self.request.get('QUERY_STRING', '')

        # If we have a query string, remove some things we don't want, and
        # keep it around.
        if query_string:
            query_dict = cgi.parse_qs(query_string, keep_blank_values=True)
            query_dict.pop('loggingout', None)
            query_string = urllib.urlencode(
                sorted(query_dict.items()), doseq=True)
            # If we still have a query_string after things we don't want
            # have been removed, add it onto the url.
            if query_string:
                query_string = '?' + query_string

        # The approach we're taking is to combine the application url with
        # the path_info, taking out path steps that are to do with virtual
        # hosting.  This is not exactly correct, as the application url
        # can have other path steps in it.  We're not using the feature of
        # having other path steps in the application url, so this will work
        # for us, assuming we don't need that in the future.

        # The application_url is typically like 'http://thing:port'. No
        # trailing slash.
        application_url = self.request.getApplicationURL()

        # We're going to use PATH_INFO to remove any spurious '+index' at the
        # end of the URL.  But, PATH_INFO will contain virtual hosting
        # configuration, if there is any.
        path_info = self.request['PATH_INFO']

        # Remove any virtual hosting segments.
        path_steps = []
        in_virtual_hosting_section = False
        for step in path_info.split('/'):
            if step.startswith('++vh++'):
                in_virtual_hosting_section = True
                continue
            if step == '++':
                in_virtual_hosting_section = False
                continue
            if not in_virtual_hosting_section:
                path_steps.append(step)
        path = '/'.join(path_steps)

        # Make the URL stop at the end of path_info so that we don't get
        # spurious '+index' at the end.
        full_url = '%s%s' % (application_url, path)
        if full_url.endswith('/'):
            full_url = full_url[:-1]
        logout_url_end = '/+logout'
        if full_url.endswith(logout_url_end):
            full_url = full_url[:-len(logout_url_end)]
        return '%s/+login%s' % (full_url, query_string)


class LaunchpadRootNavigation(Navigation):

    usedfor = ILaunchpadRoot

    def breadcrumb(self):
        return 'Launchpad'

    stepto_utilities = {
        'products': IProductSet,
        'shipit': IShipItApplication,
        'people': IPersonSet,
        'distros': IDistributionSet,
        'sourcepackagenames': ISourcePackageNameSet,
        'binarypackagenames': IBinaryPackageNameSet,
        'projects': IProjectSet,
        'token': ILoginTokenSet,
        'karmaaction': IKarmaActionSet,
        'potemplatenames': IPOTemplateNameSet,
        'bazaar': IBazaarApplication,
        'codeofconduct': ICodeOfConductSet,
        'malone': IMaloneApplication,
        'bugs': IMaloneApplication,
        'registry': IRegistryApplication,
        'rosetta': IRosettaApplication,
        'specs': ISpecificationSet,
        'sprints': ISprintSet,
        'support': ITicketSet,
        'foaf': IFOAFApplication,
        '+builds': IBuilderSet,
        'bounties': IBountySet,
        'errors': ILocalErrorReportingService
        }

    def traverse(self, name):
        if name in self.stepto_utilities:
            return getUtility(self.stepto_utilities[name])
        else:
            return None

    @stepto('calendar')
    def calendar(self):
        # XXX permission=launchpad.AnyPerson
        return MergedCalendar()


class FOAFApplicationNavigation(Navigation):

    usedfor = IFOAFApplication

    @stepto('projects')
    def projects(self):
        # DEPRECATED
        return getUtility(IProjectSet)

    @stepto('people')
    def people(self):
        # DEPRECATED
        return getUtility(IPersonSet)

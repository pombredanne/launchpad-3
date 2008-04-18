# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Browser views for distributions."""

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    'DistributionDynMenu',
    'DistributionSOP',
    'DistributionFacets',
    'DistributionSpecificationsMenu',
    'DistributionView',
    'DistributionPPASearchView',
    'DistributionAllPackagesView',
    'DistributionBrandingView',
    'DistributionEditView',
    'DistributionSetView',
    'DistributionAddView',
    'DistributionArchiveMirrorsView',
    'DistributionCountryArchiveMirrorsView',
    'DistributionSeriesMirrorsView',
    'DistributionSeriesMirrorsRSSView',
    'DistributionArchiveMirrorsRSSView',
    'DistributionDisabledMirrorsView',
    'DistributionPendingReviewMirrorsView',
    'DistributionUnofficialMirrorsView',
    'DistributionLanguagePackAdminView',
    'DistributionSetFacets',
    'DistributionSetNavigation',
    'DistributionSetContextMenu',
    'DistributionSetSOP',
    ]

import datetime
import operator

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import (
    DistroSeriesStatus, IArchiveSet, IDistributionMirrorSet,
    IDistributionSet, IDistribution, ILaunchBag, ILaunchpadCelebrities,
    IPublishedPackageSet, MirrorContent, MirrorSpeed, NotFoundError)
from canonical.launchpad.browser.announcement import HasAnnouncementsView
from canonical.launchpad.browser.branding import BrandingChangeView
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.faqtarget import FAQTargetNavigationMixin
from canonical.launchpad.browser.feeds import FeedsMixin
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.components.request_country import (
    ipaddress_from_request, request_country)
from canonical.launchpad.browser.questiontarget import (
    QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, ContextMenu,
    enabled_with_permission, GetitemNavigation, LaunchpadEditFormView,
    LaunchpadFormView, LaunchpadView, Link, Navigation, redirection,
    StandardLaunchpadFacets, stepthrough, stepto)
from canonical.launchpad.browser.seriesrelease import (
    SeriesOrReleasesMixinDynMenu)
from canonical.launchpad.browser.sprint import SprintsMixinDynMenu
from canonical.launchpad.webapp.dynmenu import DynMenu, neverempty
from canonical.launchpad.webapp.batching import BatchNavigator


class DistributionNavigation(
    GetitemNavigation, BugTargetTraversalMixin, QuestionTargetTraversalMixin,
    FAQTargetNavigationMixin):

    usedfor = IDistribution

    @redirection('+source', status=301)
    def redirect_source(self):
        return canonical_url(self.context)

    def breadcrumb(self):
        return self.context.displayname

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

    @stepthrough('+mirror')
    def traverse_mirrors(self, name):
        return self.context.getMirrorByName(name)

    @stepthrough('+source')
    def traverse_sources(self, name):
        return self.context.getSourcePackage(name)

    @stepthrough('+milestone')
    def traverse_milestone(self, name):
        return self.context.getMilestone(name)

    @stepthrough('+announcement')
    def traverse_announcement(self, name):
        return self.context.getAnnouncement(name)

    @stepthrough('+spec')
    def traverse_spec(self, name):
        return self.context.getSpecification(name)


class DistributionSetNavigation(Navigation):

    usedfor = IDistributionSet

    def breadcrumb(self):
        return 'Distributions'

    def traverse(self, name):
        # Raise a 404 on an invalid distribution name
        distribution = self.context.getByName(name)
        if distribution is None:
            raise NotFoundError(name)
        return self.redirectSubTree(canonical_url(distribution))


class DistributionSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.title

    def listChildren(self, num):
        return self.context.serieses[:num]

    def listAltChildren(self, num):
        return None


class DistributionFacets(QuestionTargetFacetMixin, StandardLaunchpadFacets):

    usedfor = IDistribution

    enable_only = ['overview', 'bugs', 'answers', 'specifications',
                   'translations']

    def specifications(self):
        text = 'Blueprints'
        summary = 'Feature specifications for %s' % self.context.displayname
        return Link('', text, summary)


class DistributionSetSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return 'Distributions in Launchpad'

    def listChildren(self, num):
        return []

    def listAltChildren(self, num):
        return None


class DistributionSetFacets(StandardLaunchpadFacets):

    usedfor = IDistributionSet

    enable_only = ['overview', ]


class DistributionSetContextMenu(ContextMenu):

    usedfor = IDistributionSet
    links = ['products', 'distributions', 'people', 'meetings']

    def distributions(self):
        return Link('/distros/', 'View distributions')

    def products(self):
        return Link('/projects/', 'View projects')

    def people(self):
        return Link('/people/', 'View people')

    def meetings(self):
        return Link('/sprints/', 'View meetings')


class DistributionOverviewMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'overview'
    links = ['edit', 'branding', 'driver', 'search', 'allpkgs', 'members',
             'mirror_admin', 'reassign', 'addseries', 'top_contributors',
             'mentorship', 'builds', 'cdimage_mirrors', 'archive_mirrors',
             'pending_review_mirrors', 'disabled_mirrors',
             'unofficial_mirrors', 'newmirror', 'announce', 'announcements',
             'upload_admin', 'ppas', 'subscribe']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change distribution details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def branding(self):
        text = 'Change branding'
        return Link('+branding', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals for all series'
        return Link('+driver', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change registrant'
        return Link('+reassign', text, icon='edit')

    def newmirror(self):
        text = 'Register a new mirror'
        enabled = self.context.full_functionality
        return Link('+newmirror', text, enabled=enabled, icon='add')

    def top_contributors(self):
        text = 'List top contributors'
        return Link('+topcontributors', text, icon='info')

    def mentorship(self):
        text = 'Mentoring available'
        return Link('+mentoring', text, icon='info')

    def cdimage_mirrors(self):
        text = 'Show CD mirrors'
        enabled = self.context.full_functionality
        return Link('+cdmirrors', text, enabled=enabled, icon='info')

    def archive_mirrors(self):
        text = 'Show archive mirrors'
        enabled = self.context.full_functionality
        return Link('+archivemirrors', text, enabled=enabled, icon='info')

    def _userCanSeeNonPublicMirrorListings(self):
        """Does the user have rights to see non-public mirrors listings?"""
        user = getUtility(ILaunchBag).user
        return (self.context.full_functionality
                and user is not None
                and user.inTeam(self.context.mirror_admin))

    def disabled_mirrors(self):
        text = 'Show disabled mirrors'
        enabled = self._userCanSeeNonPublicMirrorListings()
        return Link('+disabledmirrors', text, enabled=enabled, icon='info')

    def pending_review_mirrors(self):
        text = 'Show pending-review mirrors'
        enabled = self._userCanSeeNonPublicMirrorListings()
        return Link(
            '+pendingreviewmirrors', text, enabled=enabled, icon='info')

    def unofficial_mirrors(self):
        text = 'Show unofficial mirrors'
        enabled = self._userCanSeeNonPublicMirrorListings()
        return Link('+unofficialmirrors', text, enabled=enabled, icon='info')

    def allpkgs(self):
        text = 'List all packages'
        return Link('+allpackages', text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def members(self):
        text = 'Change members team'
        return Link('+selectmemberteam', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def upload_admin(self):
        text = 'Change upload manager'
        summary = 'Someone with permission to manage uploads'
        return Link('+uploadadmin', text, summary, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def mirror_admin(self):
        text = 'Change mirror admins'
        enabled = self.context.full_functionality
        return Link('+selectmirroradmins', text, enabled=enabled, icon='edit')

    def search(self):
        text = 'Search packages'
        return Link('+search', text, icon='search')

    @enabled_with_permission('launchpad.Admin')
    def addseries(self):
        text = 'Add series'
        return Link('+addseries', text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def announce(self):
        text = 'Make announcement'
        summary = 'Publish an item of news for this project'
        return Link('+announce', text, summary, icon='add')

    def announcements(self):
        text = 'Show announcements'
        enabled = bool(self.context.announcements().count())
        return Link('+announcements', text, enabled=enabled)

    def builds(self):
        text = 'Builds'
        return Link('+builds', text, icon='info')

    def ppas(self):
        text = 'Personal Package Archives'
        return Link('+ppas', text, icon='info')

    def subscribe(self):
        text = 'Subscribe to bug mail'
        return Link('+subscribe', text, icon='edit')


class DistributionBugsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'bugs'
    links = ['bugcontact', 'securitycontact', 'cve_list']

    def cve_list(self):
        text = 'CVE reports'
        return Link('+cve', text, icon='cve')

    @enabled_with_permission('launchpad.Edit')
    def bugcontact(self):
        text = 'Change bug supervisor'
        return Link('+bugcontact', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def securitycontact(self):
        text = 'Change security contact'
        return Link('+securitycontact', text, icon='edit')


class DistributionBountiesMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'bounties'
    links = ['new', 'link']

    def new(self):
        text = 'Register new bounty'
        return Link('+addbounty', text, icon='add')

    def link(self):
        text = 'Link existing bounty'
        return Link('+linkbounty', text, icon='edit')


class DistributionSpecificationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'specifications'
    links = ['listall', 'doc', 'roadmap', 'assignments', 'new']

    def listall(self):
        text = 'List all blueprints'
        return Link('+specs?show=all', text, icon='info')

    def roadmap(self):
        text = 'Roadmap'
        return Link('+roadmap', text, icon='info')

    def assignments(self):
        text = 'Assignments'
        return Link('+assignments', text, icon='info')

    def doc(self):
        text = 'Documentation'
        summary = 'List all complete informational specifications'
        return Link('+documentation', text, summary,
            icon='info')

    def new(self):
        text = 'Register a blueprint'
        summary = 'Register a new blueprint for %s' % self.context.title
        return Link('+addspec', text, summary, icon='add')


class DistributionTranslationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'translations'
    links = ['edit', 'imports', 'language_pack_admin']

    def imports(self):
        text = 'See import queue'
        return Link('+imports', text)

    def edit(self):
        text = 'Change translators'
        return Link('+changetranslators', text, icon='edit')

    @enabled_with_permission('launchpad.TranslationsAdmin')
    def language_pack_admin(self):
        text = 'Change language pack admins'
        return Link('+select-language-pack-admin', text, icon='edit')


class DistributionView(HasAnnouncementsView, BuildRecordsView, FeedsMixin):
    """Default Distribution view class."""

    def initialize(self):
        """Initialize template control fields.

        Also check if the search action was invoked and setup a batched
        list with the results if necessary.
        """
        # initialize control fields
        self.matches = 0

        # check if the user invoke search, if not dismiss
        self.text = self.request.form.get('text', None)
        if not self.text:
            self.search_requested = False
            return
        self.search_requested = True

        results = self.search_results()
        self.matches = len(results)
        if self.matches > 5:
            self.detailed = False
        else:
            self.detailed = True

        self.batchnav = BatchNavigator(results, self.request)

    @cachedproperty
    def translation_focus(self):
        """Return the IDistroSeries where the translators should work.

        If ther isn't a defined focus, we return latest series.
        """
        if self.context.translation_focus is None:
            return self.context.currentseries
        else:
            return self.context.translation_focus

    def search_results(self):
        """Return IDistributionSourcePackages according given a text.

        Try to find the source packages in this distribution that match
        the given text.
        """
        return self.context.searchSourcePackages(self.text)

    def secondary_translatable_serieses(self):
        """Return a list of IDistroSeries that aren't the translation_focus.

        It only includes the ones that are still supported.
        """
        serieses = [
            series
            for series in self.context.serieses
            if (series.status != DistroSeriesStatus.OBSOLETE
                and (self.translation_focus is None or
                     self.translation_focus.id != series.id))
            ]

        return sorted(serieses, key=operator.attrgetter('version'),
                      reverse=True)


class DistributionPPASearchView(LaunchpadView):
    """Search PPAs belonging to the Distribution in question."""

    def initialize(self):
        self.name_filter = self.request.get('name_filter')
        self.show_inactive = self.request.get('show_inactive')

    @property
    def search_results(self):
        """Process search form request."""
        if self.name_filter is None:
            return None

        # Preserve self.show_inactive state because it's used in the
        # template and build a boolean field to be passed for
        # searchPPAs.
        show_inactive = (self.show_inactive == 'on')

        ppas = self.context.searchPPAs(
            text=self.name_filter, show_inactive=show_inactive,
            user=self.user)

        self.batchnav = BatchNavigator(ppas, self.request)
        return self.batchnav.currentBatch()

    @property
    def number_of_registered_ppas(self):
        """The number of archives with PPA purpose.

        It doesn't include private PPAs.
        """
        return self.context.searchPPAs(show_inactive=True).count()

    @property
    def number_of_active_ppas(self):
        """The number of PPAs with at least one source publication.

        It doesn't include private PPAs.
        """
        return self.context.searchPPAs(show_inactive=False).count()

    @property
    def number_of_ppa_sources(self):
        """The number of sources published across all PPAs."""
        return getUtility(IArchiveSet).number_of_ppa_sources

    @property
    def number_of_ppa_binaries(self):
        """The number of binaries published across all PPAs."""
        return getUtility(IArchiveSet).number_of_ppa_binaries


class DistributionAllPackagesView(LaunchpadView):
    def initialize(self):
        results = self.context.getSourcePackageCaches()
        self.batchnav = BatchNavigator(results, self.request)


class DistributionRedirectingEditView(SQLObjectEditView):
    """A deprecated view to be used by the +driver and +uploadadmin pages."""

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class DistributionBrandingView(BrandingChangeView):

    schema = IDistribution
    field_names = ['icon', 'logo', 'mugshot']


class DistributionSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def count(self):
        return self.context.count()


class DistributionAddView(LaunchpadFormView):

    schema = IDistribution
    label = "Create a new distribution"
    field_names = ["name", "displayname", "title", "summary", "description",
                   "domainname", "members",
                   "official_malone", "official_blueprints",
                   "official_rosetta", "official_answers"]

    @action("Save", name='save')
    def save_action(self, action, data):
        distribution = getUtility(IDistributionSet).new(
            name=data['name'],
            displayname=data['displayname'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            domainname=data['domainname'],
            members=data['members'],
            owner=self.user,
            )
        notify(ObjectCreatedEvent(distribution))
        self.next_url = canonical_url(distribution)


class DistributionEditView(LaunchpadEditFormView):

    schema = IDistribution
    label = "Change distribution details"
    field_names = ['displayname', 'title', 'summary', 'description',
                   'bug_reporting_guidelines', 'official_malone',
                   'enable_bug_expiration', 'official_blueprints',
                   'official_rosetta', 'official_answers']

    def isAdmin(self):
        return self.user.inTeam(getUtility(ILaunchpadCelebrities).admin)

    def setUpFields(self):
        LaunchpadFormView.setUpFields(self)
        if not self.isAdmin():
            self.form_fields = self.form_fields.omit(
                'official_malone', 'official_rosetta', 'official_answers',
                'enable_bug_expiration')

    def validate(self, data):
        """Constrain bug expiration to Launchpad Bugs tracker."""
        # enable_bug_expiration is disabled by JavaScript when official_malone
        # is set False. The contraint is enforced here in case the JavaScript
        # fails to load or activate.
        official_malone = data.get('official_malone', False)
        if not official_malone:
            data['enable_bug_expiration'] = False

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class DistributionLanguagePackAdminView(LaunchpadEditFormView):
    """Browser view to change the language pack administrator."""

    schema = IDistribution
    label = "Change the language pack administrator"
    field_names = ['language_pack_admin']

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)


class DistributionCountryArchiveMirrorsView(LaunchpadView):
    """A text/plain page that lists the mirrors in the country of the request.

    If there are no mirrors located in the country of the request, we fallback
    to the main Ubuntu repositories.
    """

    def render(self):
        request = self.request
        if not self.context.full_functionality:
            request.response.setStatus(404)
            return u''
        ip_address = ipaddress_from_request(request)
        country = request_country(request)
        mirrors = getUtility(IDistributionMirrorSet).getBestMirrorsForCountry(
            country, MirrorContent.ARCHIVE)
        body = "\n".join(mirror.base_url for mirror in mirrors)
        request.response.setHeader('content-type', 'text/plain;charset=utf-8')
        if country is None:
            country_name = 'Unknown'
        else:
            country_name = country.name
        request.response.setHeader('X-Generated-For-Country', country_name)
        request.response.setHeader('X-Generated-For-IP', ip_address)
        # XXX: These are here only for debugging
        # https://launchpad.net/bugs/173729. -- Guilherme Salgado, 2008-01-09
        request.response.setHeader(
            'X-REQUEST-HTTP_X_FORWARDED_FOR',
            request.get('HTTP_X_FORWARDED_FOR'))
        request.response.setHeader(
            'X-REQUEST-REMOTE_ADDR', request.get('REMOTE_ADDR'))
        return body.encode('utf-8')


class DistributionMirrorsView(LaunchpadView):

    show_freshness = True

    @cachedproperty
    def mirror_count(self):
        return self.mirrors.count()

    def _sum_throughput(self, mirrors):
        """Given a list of mirrors, calculate the total bandwidth
        available.
        """
        throughput = 0
        # this would be a wonderful place to have abused DBItem.sort_key ;-)
        for mirror in mirrors:
            if mirror.speed == MirrorSpeed.S128K:
                throughput += 128
            elif mirror.speed == MirrorSpeed.S256K:
                throughput += 256
            elif mirror.speed == MirrorSpeed.S512K:
                throughput += 512
            elif mirror.speed == MirrorSpeed.S1M:
                throughput += 1000
            elif mirror.speed == MirrorSpeed.S2M:
                throughput += 2000
            elif mirror.speed == MirrorSpeed.S10M:
                throughput += 10000
            elif mirror.speed == MirrorSpeed.S45M:
                throughput += 45000
            elif mirror.speed == MirrorSpeed.S100M:
                throughput += 100000
            elif mirror.speed == MirrorSpeed.S1G:
                throughput += 1000000
            elif mirror.speed == MirrorSpeed.S2G:
                throughput += 2000000
            elif mirror.speed == MirrorSpeed.S4G:
                throughput += 4000000
            elif mirror.speed == MirrorSpeed.S10G:
                throughput += 10000000
            elif mirror.speed == MirrorSpeed.S20G:
                throughput += 20000000
            else:
                # need to be made aware of new values in
                # interfaces/distributionmirror.py MirrorSpeed
                return 'Indeterminate'
        if throughput < 1000:
            return str(throughput) + ' Kbps'
        elif throughput < 1000000:
            return str(throughput/1000) + ' Mbps'
        else:
            return str(throughput/1000000) + ' Gbps'

    @cachedproperty
    def total_throughput(self):
        return self._sum_throughput(self.mirrors)

    def getMirrorsGroupedByCountry(self):
        """Given a list of mirrors, create and return list of dictionaries
        containing the country names and the list of mirrors on that country.

        This list is ordered by country name.
        """
        mirrors_by_country = {}
        for mirror in self.mirrors:
            mirrors = mirrors_by_country.setdefault(mirror.country.name, [])
            mirrors.append(mirror)
        return [dict(country=country,
                     mirrors=mirrors,
                     number=len(mirrors),
                     throughput=self._sum_throughput(mirrors))
                for country, mirrors in sorted(mirrors_by_country.items())]


class DistributionArchiveMirrorsView(DistributionMirrorsView):

    heading = 'Official Archive Mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.archive_mirrors


class DistributionSeriesMirrorsView(DistributionMirrorsView):

    heading = 'Official CD Mirrors'
    show_freshness = False

    @cachedproperty
    def mirrors(self):
        return self.context.cdimage_mirrors


class DistributionMirrorsRSSBaseView(LaunchpadView):
    """A base class for RSS feeds of distribution mirrors."""

    def initialize(self):
        self.now = datetime.datetime.utcnow()

    def render(self):
        self.request.response.setHeader(
            'content-type', 'text/xml;charset=utf-8')
        body = LaunchpadView.render(self)
        return body.encode('utf-8')


class DistributionArchiveMirrorsRSSView(DistributionMirrorsRSSBaseView):
    """The RSS feed for archive mirrors."""

    heading = 'Archive Mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.archive_mirrors


class DistributionSeriesMirrorsRSSView(DistributionMirrorsRSSBaseView):
    """The RSS feed for series mirrors."""

    heading = 'CD Mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.cdimage_mirrors


class DistributionMirrorsAdminView(DistributionMirrorsView):

    def initialize(self):
        """Raise an Unauthorized exception if the user is not a member of this
        distribution's mirror_admin team.
        """
        # XXX: Guilherme Salgado 2006-06-16:
        # We don't want these pages to be public but we can't protect
        # them with launchpad.Edit because that would mean only people with
        # that permission on a Distribution would be able to see them. That's
        # why we have to do the permission check here.
        if not (self.user and self.user.inTeam(self.context.mirror_admin)):
            raise Unauthorized('Forbidden')


class DistributionUnofficialMirrorsView(DistributionMirrorsAdminView):

    heading = 'Unofficial Mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.unofficial_mirrors


class DistributionPendingReviewMirrorsView(DistributionMirrorsAdminView):

    heading = 'Pending-review mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.pending_review_mirrors


class DistributionDisabledMirrorsView(DistributionMirrorsAdminView):

    heading = 'Disabled Mirrors'

    @cachedproperty
    def mirrors(self):
        return self.context.disabled_mirrors


class DistributionDynMenu(
    DynMenu, SprintsMixinDynMenu, SeriesOrReleasesMixinDynMenu):

    menus = {
        '': 'mainMenu',
        'meetings': 'meetingsMenu',
        'series': 'seriesMenu',
        'milestones': 'milestoneMenu',
        }

    @neverempty
    def milestoneMenu(self):
        """Show milestones more recently than one month ago,
        or with no due date.
        """
        fairly_recent = (
            datetime.datetime.utcnow() - datetime.timedelta(days=30))
        for milestone in self.context.milestones:
            if (milestone.dateexpected is None or
                milestone.dateexpected > fairly_recent):
                yield self.makeLink(milestone.title, context=milestone)
        yield self.makeLink('Show all milestones...', page='+milestones')

    @neverempty
    def mainMenu(self):
        yield self.makeLink('Series', page='+series', submenu='serieses')
        yield self.makeLink('Meetings', page='+sprints', submenu='meetings')
        yield self.makeLink(
            'Milestones', page='+milestones', submenu='milestones')

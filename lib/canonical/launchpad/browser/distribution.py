# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    'DistributionSOP',
    'DistributionFacets',
    'DistributionSpecificationsMenu',
    'DistributionView',
    'DistributionAllPackagesView',
    'DistributionEditView',
    'DistributionSetView',
    'DistributionAddView',
    'DistributionBugContactEditView',
    'DistributionArchiveMirrorsView',
    'DistributionCountryArchiveMirrorsView',
    'DistributionReleaseMirrorsView',
    'DistributionReleaseMirrorsRSSView',
    'DistributionArchiveMirrorsRSSView',
    'DistributionDisabledMirrorsView',
    'DistributionUnofficialMirrorsView',
    'DistributionLaunchpadUsageEditView',
    'DistributionSetFacets',
    'DistributionSetNavigation',
    'DistributionSetContextMenu',
    'DistributionSetSOP',
    ]

from datetime import datetime
import operator

from zope.component import getUtility
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IPublishedPackageSet, ILaunchBag,
    IArchiveSet, ILaunchpadRoot, NotFoundError, IDistributionMirrorSet)
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation
from canonical.launchpad.components.request_country import request_country
from canonical.launchpad.browser.questiontarget import (
    QuestionTargetFacetMixin, QuestionTargetTraversalMixin)
from canonical.launchpad.webapp import (
    action, ApplicationMenu, canonical_url, ContextMenu,
    enabled_with_permission,
    GetitemNavigation, LaunchpadEditFormView, LaunchpadView, Link,
    redirection, Navigation, StandardLaunchpadFacets,
    stepthrough, stepto, LaunchpadFormView, custom_widget)
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.lp.dbschema import DistributionReleaseStatus, MirrorContent
from canonical.widgets.image import ImageAddWidget, ImageChangeWidget


class DistributionNavigation(
    GetitemNavigation, BugTargetTraversalMixin, QuestionTargetTraversalMixin):

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
        return self.context.releases[:num]

    def listAltChildren(self, num):
        return None


class DistributionFacets(QuestionTargetFacetMixin, StandardLaunchpadFacets):

    usedfor = IDistribution

    enable_only = ['overview', 'bugs', 'answers', 'specifications',
                   'translations']

    def specifications(self):
        target = '+specs'
        text = 'Blueprints'
        summary = 'Feature specifications for %s' % self.context.displayname
        return Link(target, text, summary)


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
        return Link('/products/', 'View projects')

    def people(self):
        return Link('/people/', 'View people')

    def meetings(self):
        return Link('/sprints/', 'View meetings')


class DistributionOverviewMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'overview'
    links = ['edit', 'driver', 'search', 'allpkgs', 'members', 'mirror_admin',
             'reassign', 'addrelease', 'top_contributors', 'builds',
             'release_mirrors', 'archive_mirrors', 'disabled_mirrors',
             'unofficial_mirrors', 'newmirror', 'launchpad_usage',
             'upload_admin']

    @enabled_with_permission('launchpad.Edit')
    def edit(self):
        text = 'Change details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def driver(self):
        text = 'Appoint driver'
        summary = 'Someone with permission to set goals for all releases'
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

    def release_mirrors(self):
        text = 'Show CD mirrors'
        enabled = self.context.full_functionality
        return Link('+cdmirrors', text, enabled=enabled, icon='info')

    def archive_mirrors(self):
        text = 'Show archive mirrors'
        enabled = self.context.full_functionality
        return Link('+archivemirrors', text, enabled=enabled, icon='info')

    def disabled_mirrors(self):
        text = 'Show disabled mirrors'
        enabled = False
        user = getUtility(ILaunchBag).user
        if (self.context.full_functionality and user is not None and
            user.inTeam(self.context.mirror_admin)):
            enabled = True
        return Link('+disabledmirrors', text, enabled=enabled, icon='info')

    def unofficial_mirrors(self):
        text = 'Show unofficial mirrors'
        enabled = False
        user = getUtility(ILaunchBag).user
        if (self.context.full_functionality and user is not None and
            user.inTeam(self.context.mirror_admin)):
            enabled = True
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
    def addrelease(self):
        text = 'Add release'
        return Link('+addrelease', text, icon='add')

    def builds(self):
        text = 'Builds'
        return Link('+builds', text, icon='info')

    @enabled_with_permission('launchpad.Edit')
    def launchpad_usage(self):
        text = 'Define Launchpad usage'
        return Link('+launchpad', text, icon='edit')


class DistributionBugsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'bugs'
    links = ['new', 'bugcontact', 'securitycontact', 'cve_list']

    def cve_list(self):
        text = 'CVE reports'
        return Link('+cve', text, icon='cve')

    def new(self):
        text = 'Report a bug'
        return Link('+filebug', text, icon='add')

    @enabled_with_permission('launchpad.Edit')
    def bugcontact(self):
        text = 'Change bug contact'
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
        text = 'Register new blueprint'
        return Link('+addspec', text, icon='add')


class DistributionTranslationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'translations'
    links = ['edit']

    def edit(self):
        text = 'Change translators'
        return Link('+changetranslators', text, icon='edit')


class DistributionView(BuildRecordsView):
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
        """Return the IDistroRelease where the translators should work.

        If ther isn't a defined focus, we return latest release.
        """
        if self.context.translation_focus is None:
            return self.context.currentrelease
        else:
            return self.context.translation_focus

    def search_results(self):
        """Return IDistributionSourcePackages according given a text.

        Try to find the source packages in this distribution that match
        the given text.
        """
        return self.context.searchSourcePackages(self.text)

    def secondary_translatable_releases(self):
        """Return a list of IDistroRelease that aren't the translation_focus.

        It only includes the ones that are still supported.
        """
        releases = [
            release
            for release in self.context.releases
            if (release.releasestatus != DistributionReleaseStatus.OBSOLETE
                and (self.translation_focus is None or
                     self.translation_focus.id != release.id))
            ]

        return sorted(releases, key=operator.attrgetter('version'),
                      reverse=True)


class DistributionAllPackagesView(LaunchpadView):
    def initialize(self):
        results = self.context.source_package_caches
        self.batchnav = BatchNavigator(results, self.request)


class DistributionRedirectingEditView(SQLObjectEditView):
    """A deprecated view to be used by the +driver and +uploadadmin pages."""

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class DistributionEditView(LaunchpadEditFormView):

    schema = IDistribution
    label = "Change distribution details"
    field_names = ['displayname', 'title', 'summary', 'description',
                   'gotchi', 'emblem']
    custom_widget('gotchi', ImageChangeWidget)
    custom_widget('emblem', ImageChangeWidget)

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(self.context)


class DistributionLaunchpadUsageEditView(LaunchpadEditFormView):
    """View class for defining Launchpad usage."""

    schema = IDistribution
    field_names = ["official_rosetta", "official_malone"]
    label = "Describe Launchpad usage"

    @action("Change", name='change')
    def change_action(self, action, data):
        self.updateContextFromData(data)

    @property
    def next_url(self):
        return canonical_url(self.context)


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
                   "gotchi", "emblem", "domainname", "members"]
    custom_widget('gotchi', ImageAddWidget)
    custom_widget('emblem', ImageAddWidget)

    @action("Save", name='save')
    def save_action(self, action, data):
        archive = getUtility(IArchiveSet).new()
        distribution = getUtility(IDistributionSet).new(
            name=data['name'],
            displayname=data['displayname'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            domainname=data['domainname'],
            members=data['members'],
            owner=self.user,
            main_archive=archive,
            gotchi=data['gotchi'],
            gotchi_heading=None,
            emblem=data['emblem'])
        notify(ObjectCreatedEvent(distribution))
        self.next_url = canonical_url(distribution)


class DistributionBugContactEditView(SQLObjectEditView):
    """Browser view for editing the distribution bug contact."""
    def changed(self):
        """Redirect to the distribution page."""
        distribution = self.context
        contact_display_value = None

        if distribution.bugcontact:
            if distribution.bugcontact.preferredemail:
                contact_display_value = (
                    distribution.bugcontact.preferredemail.email)
            else:
                contact_display_value = distribution.bugcontact.displayname

        # The bug contact was set to a new person or team.
        if contact_display_value:
            self.request.response.addNotification(
                "Successfully changed the distribution bug contact to %s" %
                contact_display_value)
        else:
            # The bug contact was set to noone.
            self.request.response.addNotification(
                "Successfully cleared the distribution bug contact. This "
                "means that there is no longer a distro-wide contact for "
                "bugmail. You can, of course, set a distribution bug "
                "contact again whenever you want to.")

        self.request.response.redirect(canonical_url(distribution))


class DistributionCountryArchiveMirrorsView(LaunchpadView):
    """A text/plain page which lists the mirrors in the country of the request.

    If there are no mirrors located in the country of the request, we fallback
    to the main Ubuntu repositories.
    """

    def render(self):
        if not self.context.full_functionality:
            self.request.response.setStatus(404)
            return u''
        country = request_country(self.request)
        mirrors = getUtility(IDistributionMirrorSet).getBestMirrorsForCountry(
            country, MirrorContent.ARCHIVE)
        body = "\n".join(mirror.base_url for mirror in mirrors)
        self.request.response.setHeader(
            'content-type', 'text/plain;charset=utf-8')
        return body.encode('utf-8')


class DistributionMirrorsView(LaunchpadView):

    def _groupMirrorsByCountry(self, mirrors):
        """Given a list of mirrors, create and return list of dictionaries
        containing the country names and the list of mirrors on that country.

        This list is ordered by country name.
        """
        mirrors_by_country = {}
        for mirror in mirrors:
            mirrors = mirrors_by_country.setdefault(mirror.country.name, [])
            mirrors.append(mirror)
        return [dict(country=country, mirrors=mirrors)
                for country, mirrors in sorted(mirrors_by_country.items())]


class DistributionArchiveMirrorsView(DistributionMirrorsView):

    heading = 'Official Archive Mirrors'

    def getMirrorsGroupedByCountry(self):
        return self._groupMirrorsByCountry(self.context.archive_mirrors)


class DistributionReleaseMirrorsView(DistributionMirrorsView):

    heading = 'Official CD Mirrors'

    def getMirrorsGroupedByCountry(self):
        return self._groupMirrorsByCountry(self.context.release_mirrors)


class DistributionMirrorsRSSBaseView(LaunchpadView):
    """A base class for RSS feeds of distribution mirrors."""

    def initialize(self):
        self.now = datetime.utcnow()

    def render(self):
        self.request.response.setHeader(
            'content-type', 'text/xml;charset=utf-8')
        body = LaunchpadView.render(self)
        return body.encode('utf-8')


class DistributionArchiveMirrorsRSSView(DistributionMirrorsRSSBaseView):
    """The RSS feed for archive mirrors."""

    heading = 'Archive Mirrors'

    @property
    def mirrors(self):
        return self.context.archive_mirrors


class DistributionReleaseMirrorsRSSView(DistributionMirrorsRSSBaseView):
    """The RSS feed for release mirrors."""

    heading = 'CD Mirrors'

    @property
    def mirrors(self):
        return self.context.release_mirrors


class DistributionMirrorsAdminView(DistributionMirrorsView):

    def initialize(self):
        """Raise an Unauthorized exception if the user is not a member of this
        distribution's mirror_admin team.
        """
        # XXX: We don't want these pages to be public but we can't protect
        # them with launchpad.Edit because that would mean only people with
        # that permission on a Distribution would be able to see them. That's
        # why we have to do the permission check here.
        # -- Guilherme Salgado, 2006-06-16
        if not (self.user and self.user.inTeam(self.context.mirror_admin)):
            raise Unauthorized('Forbidden')


class DistributionUnofficialMirrorsView(DistributionMirrorsAdminView):

    heading = 'Unofficial Mirrors'

    def getMirrorsGroupedByCountry(self):
        return self._groupMirrorsByCountry(self.context.unofficial_mirrors)


class DistributionDisabledMirrorsView(DistributionMirrorsAdminView):

    heading = 'Disabled Mirrors'

    def getMirrorsGroupedByCountry(self):
        return self._groupMirrorsByCountry(self.context.disabled_mirrors)

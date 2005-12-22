# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    'DistributionSetNavigation',
    'DistributionFacets',
    'DistributionView',
    'DistributionSetView',
    'DistributionSetAddView',
    'DistributionMirrorAddView',
    'DistributionBugContactEditView'
    ]

from zope.component import getUtility
from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.lp.dbschema import MirrorPulseType
from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IPerson, IPublishedPackageSet,
    NotFoundError)
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ApplicationMenu, enabled_with_permission,
    GetitemNavigation, stepthrough, stepto, canonical_url, redirection)
from canonical.launchpad.validators import LaunchpadValidationError
from canonical.launchpad import _


class DistributionNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistribution

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

    @stepthrough('+ticket')
    def traverse_ticket(self, name):
        # tickets should be ints
        try:
            ticket_num = int(name)
        except ValueError:
            raise NotFoundError
        return self.context.getTicket(ticket_num)

    redirection('+ticket', '+tickets')


class DistributionSetNavigation(GetitemNavigation):

    usedfor = IDistributionSet

    def breadcrumb(self):
        return 'Distributions'


class DistributionFacets(StandardLaunchpadFacets):

    usedfor = IDistribution

    enable_only = ['overview', 'bugs', 'support', 'bounties', 'specifications',
                   'translations', 'calendar']

    def specifications(self):
        target = '+specs'
        text = 'Specifications'
        summary = 'Feature specifications for %s' % self.context.displayname
        return Link(target, text, summary)

    def support(self):
        target = '+tickets'
        text = 'Support'
        summary = (
            'Technical support requests for %s' % self.context.displayname)
        return Link(target, text, summary)


class DistributionOverviewMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'overview'
    links = ['search', 'allpkgs', 'milestone_add', 'members', 'edit',
             'editbugcontact', 'reassign', 'addrelease', 'officialmirrors',
             'allmirrors', 'newmirror']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    def editbugcontact(self):
        text = 'Edit Bug Contact'
        return Link('+editbugcontact', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change Admin'
        return Link('+reassign', text, icon='edit')

    def newmirror(self):
        text = 'Register a New Mirror'
        return Link('+newmirror', text, icon='add')

    def officialmirrors(self):
        text = 'List Official Mirrors'
        return Link('+officialmirrors', text, icon='info')

    def allmirrors(self):
        text = 'List All Mirrors'
        return Link('+allmirrors', text, icon='info')

    def allpkgs(self):
        text = 'List All Packages'
        return Link('+allpackages', text, icon='info')

    def members(self):
        text = 'Change Members'
        return Link('+selectmemberteam', text, icon='edit')

    def milestone_add(self):
        text = 'Add Milestone'
        return Link('+addmilestone', text, icon='add')

    def search(self):
        text = 'Search Packages'
        return Link('+search', text, icon='search')

    @enabled_with_permission('launchpad.Admin')
    def addrelease(self):
        text = 'Add Release'
        return Link('+addrelease', text, icon='add')


class DistributionBugsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'bugs'
    links = ['new', 'cve_list']

    def cve_list(self):
        text = 'CVE List'
        return Link('+cve', text, icon='cve')

    def new(self):
        text = 'Report a Bug'
        return Link('+filebug', text, icon='add')


class DistributionBountiesMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'bounties'
    links = ['new', 'link']

    def new(self):
        text = 'Register New Bounty'
        return Link('+addbounty', text, icon='add')

    def link(self):
        text = 'Link Existing Bounty'
        return Link('+linkbounty', text, icon='edit')


class DistributionSpecificationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'specifications'
    links = ['roadmap', 'table', 'workload', 'new']

    def roadmap(self):
        text = 'Show Roadmap'
        return Link('+specplan', text, icon='info')

    def table(self):
        text = 'Show Assignments'
        return Link('+specstable', text, icon='info')

    def workload(self):
        text = 'Show Workload'
        return Link('+workload', text, icon='info')

    def new(self):
        text = 'New Specification'
        return Link('+addspec', text, icon='add')


class DistributionSupportMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'support'
    links = ['new']
    # XXX: MatthewPaulThomas, 2005-09-20
    # Add 'help' once +gethelp is implemented for a distribution

    def help(self):
        text = 'Help and Support Options'
        return Link('+gethelp', text, icon='info')

    def new(self):
        text = 'Request Support'
        return Link('+addticket', text, icon='add')


class DistributionTranslationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'translations'
    links = ['edit']

    def edit(self):
        text = 'Change Translators'
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
        self.detailed = True
        self.search_requested = False

        # check if the user invoke search, if not dismiss 
        self.text = self.request.form.get('text', None)
        if not self.text:
            return

        # setup a batched list with the results
        self.search_requested = True
        results = self.search_results()
        start = int(self.request.get('batch_start', 0))
        # store the results list length
        self.matches = len(results)
        # check if detailed list view is allowed for this result set.
        self.check_detailed_view()
        # since we are using the results length in the layout, we can save
        # one query by passing this number to Batch initialization
        self.batch = Batch(results, start, _listlength=self.matches)
        self.batchnav = BatchNavigator(self.batch, self.request)

    def check_detailed_view(self):
        """Enable detailed list view only for sets smaller than 5 matches."""
        if self.matches > 5:
            self.detailed = False

    def search_results(self):
        """Return IDistributionSourcePackages according given a text.

        Try to find the source packages in this distribution that match
        the given text.
        """
        return self.context.searchSourcePackages(self.text)

class DistributionSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def count(self):
        return self.context.count()


class DistributionMirrorAddView(GeneralFormView):

    # XXX: This is a workaround while
    # https://launchpad.net/products/launchpad/+bug/5792 isn't fixed.
    __launchpad_facetname__ = 'overview'

    def doSchemaValidation(self, data):
        errors = []
        if (data['pulse_type'] == MirrorPulseType.PULL and
            not data['pulse_source']):
            errors.append(LaunchpadValidationError(_(
                "You have choosen 'Pull' as the pulse type but have not "
                "supplied a pulse source.")))

        if not (data['http_base_url'] or data['ftp_base_url'] or
                data['rsync_base_url']):
            errors.append(LaunchpadValidationError(_(
                "All mirrors require at least one URL (HTTP, FTP or "
                "Rsync) to be specified.")))

        if errors:
            raise WidgetsError(errors)

    def process(self, owner, name, displayname, description, speed, country,
                content, http_base_url, ftp_base_url, rsync_base_url,
                pulse_type, pulse_source, enabled, official_candidate):
        mirror = self.context.newMirror(
            owner=owner, name=name, speed=speed, country=country,
            content=content, pulse_type=pulse_type, displayname=displayname,
            description=description, http_base_url=http_base_url,
            ftp_base_url=ftp_base_url, rsync_base_url=rsync_base_url,
            official_candidate=official_candidate, enabled=enabled,
            pulse_source=pulse_source)

        self._nextURL = canonical_url(mirror)
        notify(ObjectCreatedEvent(mirror))
        return mirror
        

class DistributionSetAddView(AddView):

    __used_for__ = IDistributionSet

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the distribution
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise Unauthorized(
                "Need an authenticated user in order to create a"
                " distribution.")
        distribution = getUtility(IDistributionSet).new(
            name=data['name'],
            displayname=data['displayname'],
            title=data['title'],
            summary=data['summary'],
            description=data['description'],
            domainname=data['domainname'],
            members=data['members'],
            owner=owner)
        notify(ObjectCreatedEvent(distribution))
        self._nextURL = data['name']
        return distribution

    def nextURL(self):
        return self._nextURL


class DistributionBugContactEditView(SQLObjectEditView):
    """Browser view for editing the distribution bug contact."""
    def changed(self):
        """Redirect to the distribution page."""
        distribution = self.context
        contact_email = None

        if distribution.bugcontact:
            contact_email = distribution.bugcontact.preferredemail.email

        if contact_email:
            # The bug contact was set to a new person or team.
            self.request.response.addNotification(
                "Successfully changed the distribution bug contact to %s" %
                contact_email)
        else:
            # The bug contact was set to noone.
            self.request.response.addNotification(
                "Successfully cleared the distribution bug contact. This "
                "means that there is no longer a distro-wide contact for "
                "bugmail. You can, of course, set a distribution bug "
                "contact again whenever you want to.")

        self.request.response.redirect(canonical_url(distribution))

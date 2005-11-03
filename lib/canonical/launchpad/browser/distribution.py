# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    'DistributionSetNavigation',
    'DistributionFacets',
    'DistributionView',
    'DistributionSetView',
    'DistributionSetAddView',
    ]

from zope.component import getUtility
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IPerson, IPublishedPackageSet,
    NotFoundError)
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.browser.build import BuildRecordsView
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, ApplicationMenu, enabled_with_permission,
    GetitemNavigation, stepthrough, stepto)


class DistributionNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistribution

    def breadcrumb(self):
        return self.context.displayname

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

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
             'reassign', 'addrelease']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change Admin'
        return Link('+reassign', text, icon='edit')

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

    def __init__(self, context, request):
        self.context = context
        self.request = request
        form = self.request.form
        self.text = form.get('text', None)
        self.matches = 0
        self.detailed = True
        self._results = None

        self.searchrequested = False
        if self.text is not None and self.text != '':
            self.searchrequested = True

    def searchresults(self):
        """Try to find the source packages in this distribution that match
        the given text, then present those as a list. Cache previous results
        so the search is only done once.
        """
        if self._results is None:
            self._results = self.context.searchSourcePackages(self.text)
        self.matches = len(self._results)
        if self.matches > 5:
            self.detailed = False
        return self._results


class DistributionSetView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def count(self):
        return self.context.count()


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


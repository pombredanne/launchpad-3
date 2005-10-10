# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'DistributionNavigation',
    'DistributionSetNavigation',
    'DistributionFacets',
    'DistributionView',
    'DistributionBugsView',
    'DistributionFileBugView',
    'DistributionSetView',
    'DistributionSetAddView',
    'DistributionSetSearchView',
    ]

from zope.interface import implements
from zope.component import getUtility
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IPerson, IBugTaskSearchListingView,
    IBugSet, IPublishedPackageSet, ISourcePackageNameSet, NotFoundError,
    IDistroSourcePackageSet)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser import BugTaskSearchListingView
from canonical.launchpad.browser.bugtask import BugTargetTraversalMixin
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, canonical_url, ContextMenu, ApplicationMenu,
    enabled_with_permission, GetitemNavigation, stepthrough, stepto)


class DistributionNavigation(GetitemNavigation, BugTargetTraversalMixin):

    usedfor = IDistribution

    @stepto('+packages')
    def packages(self):
        return getUtility(IPublishedPackageSet)

    @stepthrough('+sources')
    def traverse_sources(self, name):
        # XXX: Brad Bollenbach, 2005-09-12: There is not yet an
        # interface for $distro/+sources; for now, this code's only
        # promise is that it will return the correct
        # IDistroSourcePackage for a URL path like:
        #
        # /distros/ubuntu/+sources/mozilla-firefox
        #
        # Obviously, there needs to be a simple page designed for a
        # bare +sources. Here's the bug report to track that task:
        #
        # https://launchpad.net/malone/bugs/2230
        sourcepackagenameset = getUtility(ISourcePackageNameSet)
        srcpackagename = sourcepackagenameset.queryByName(name)
        if not srcpackagename:
            raise NotFoundError
        return getUtility(IDistroSourcePackageSet).getPackage(
            distribution=self.context, sourcepackagename=srcpackagename)

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


class DistributionFacets(StandardLaunchpadFacets):

    usedfor = IDistribution

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
    links = ['edit', 'reassign', 'members', 'milestone_add']

    def edit(self):
        text = 'Edit Details'
        return Link('+edit', text, icon='edit')

    @enabled_with_permission('launchpad.Edit')
    def reassign(self):
        text = 'Change Admin'
        return Link('+reassign', text, icon='edit')

    def members(self):
        text = 'Change Members'
        return Link('+selectmemberteam', text, icon='edit')

    def milestone_add(self):
        text = 'Add Milestone'
        return Link('+addmilestone', text, icon='add')

    def searchpackages(self):
        text = 'Search Packages'
        return Link('+packages', text, icon='search')

    @enabled_with_permission('launchpad.Admin')
    def addrelease(self):
        text = 'Add New Distribution Release'
        return Link('+add', text, icon='add')


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
        text = 'Register a New Bounty'
        return Link('+addbounty', text, icon='add')

    def link(self):
        text = 'Link Existing Bounty'
        return Link('+linkbounty', text, icon='edit')


class DistributionSpecificationsMenu(ApplicationMenu):

    usedfor = IDistribution
    facet = 'specifications'
    links = ['new', 'roadmap']

    def roadmap(self):
        text = 'Roadmap'
        return Link('+specplan', text, icon='info')

    def new(self):
        text = 'Register a New Specification'
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


class DistributionView:
    """Default Distribution view class."""


class DistributionBugsView(BugTaskSearchListingView):

    implements(IBugTaskSearchListingView)

    def __init__(self, context, request):
        BugTaskSearchListingView.__init__(self, context, request)
        self.milestone_widget = None

    def task_columns(self):
        """See canonical.launchpad.interfaces.IBugTaskSearchListingView."""
        return [
            "select", "id", "title", "package", "status", "submittedby",
            "assignedto"]


class DistributionFileBugView(SQLObjectAddView):

    __used_for__ = IDistribution

    def __init__(self, context, request):
        self.request = request
        self.context = context
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the bug
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise Unauthorized(
                "Need an authenticated user in order to file a"
                " bug on a distribution.")
        bug = getUtility(IBugSet).createBug(
            distribution=self.context,
            sourcepackagename=data['sourcepackagename'],
            title=data['title'],
            comment=data['comment'],
            private=data['private'],
            owner=data['owner'])
        notify(SQLObjectCreatedEvent(bug))
        self.addedBug = bug
        return bug

    def nextURL(self):
        task = self.addedBug.bugtasks[0]
        return canonical_url(task)


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

class DistributionSetSearchView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form  = request.form

    def results(self):
        return []

    def search_action(self):
        return True

    def count(self):
        return 3


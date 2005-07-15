# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
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
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.app.form.browser.add import AddView
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.security.interfaces import Unauthorized

from canonical.launchpad.interfaces import (
    IDistribution, IDistributionSet, IPerson, IBugTaskSearchListingView,
    IBugSet)
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser import BugTaskSearchListingView
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent
from canonical.launchpad.webapp import StandardLaunchpadFacets


class DistributionFacets(StandardLaunchpadFacets):
    usedfor = IDistribution


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
        return absoluteURL(self.addedBug, self.request)


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


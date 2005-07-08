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
    'DistrosSearchView',
    'DistrosAddView',
    'DistrosEditView',
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
        # add the owner information for the product
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


    def add_action(self):
        title = self.request.get("title", "")
        description = self.request.get("description", "")
        domain = self.request.get("domain", "")
        person = IPerson(self.request.principal, None)


        if not person:
            return False

        if not title:
            return False

        dt = getUtility(IDistroTools)
        res = dt.createDistro(person.id, name, displayname,
            title, summary, description, domain)
        self.results = res
        return res

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

class DistrosSearchView:
    """
    DistroSearchView:
    This Views able the user to search on all distributions hosted on
    Soyuz by Name Distribution Title (Dispalyed name),
    """
    # TODO: (class+doc) cprov 20041003
    # This is the EpyDoc Class Document Format,
    # Does it fits our expectations ? (except the poor content)
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def search_action(self):
        raise NotImplementedError

class DistrosAddView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def add_action(self):
        name = self.request.get("name", "")
        displayname = self.request.get("displayname", "")
        title = self.request.get("title", "")
        summary = self.request.get("summary", "")
        description = self.request.get("description", "")
        domain = self.request.get("domain", "")
        person = IPerson(self.request.principal, None)


        if not person:
            return False

        if not title:
            return False

        dt = getUtility(IDistroTools)
        res = dt.createDistro(person.id, name, displayname,
            title, summary, description, domain)
        self.results = res
        return res

class DistrosEditView:

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        domainname = self.request.get("domainname", "")
        description = self.request.get("description", "")

        if not (name or title or description):
            return False

        ##XXX: (uniques) cprov 20041003
        ## again :)
        self.context.distribution.name = name
        self.context.distribution.title = title
        self.context.distribution.domainname = domainname
        self.context.distribution.description = description
        return True


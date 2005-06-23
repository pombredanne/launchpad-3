# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.interface import implements
from zope.component import getUtility
from zope.app.traversing.browser.absoluteurl import absoluteURL
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.browser.add import AddView
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form import CustomWidgetFactory
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
import zope.security.interfaces
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

from canonical.launchpad.database import Distribution, BugFactory
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import BugTaskStatus
from canonical.launchpad.interfaces import IDistribution, \
        IDistributionSet, IPerson, IBugTaskSet, ILaunchBag, \
        IBugTaskSearchListingView
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.helpers import is_maintainer
from canonical.launchpad.browser.addview import SQLObjectAddView
from canonical.launchpad.browser import BugTaskSearchListingView
from canonical.launchpad.event.sqlobjectevent import SQLObjectCreatedEvent

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
            raise zope.security.interfaces.Unauthorized(
                "Need an authenticated bug owner")
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        kw['distribution'] = self.context.id
        bug = BugFactory(
            distribution = kw['distribution'],
            sourcepackagename = kw['sourcepackagename'],
            title = kw['title'], comment = kw['comment'],
            private = kw['private'], owner = kw['owner'])

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

    ow = CustomWidgetFactory(ObjectWidget, Distribution)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        # add the owner information for the product
        owner = IPerson(self.request.principal, None)
        if not owner:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated owner"
        kw = {}
        for item in data.items():
            kw[str(item[0])] = item[1]
        kw['owner'] = owner
        distribution = Distribution(**kw)
        notify(ObjectCreatedEvent(distribution))
        self._nextURL = kw['name']
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
        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        if not (name or title or description):
            return False

        name = name.replace('%', '%%')
        title = title.replace('%', '%%')
        description = description.replace('%', '%%')

        name_like = LIKE(Distribution.q.name, "%%" + name + "%%")
        title_like = LIKE(Distribution.q.title, "%%" + title + "%%")
        description_like = LIKE(Distribution.q.description,
                                "%%" + description + "%%")
        query = AND(name_like, title_like, description_like)

##XXX: (case+insensitive) cprov 20041003
## Performe case insensitive queries using ILIKE doesn't work
## properly, since we don't have ILIKE method on SQLObject
## ===============================================================
#            name_like = ("name ILIKE %s" % "%%" + name + "%%")
#            title_like = ("title ILIKE %s" % "%%" + title + "%%")
#            description_like = ("description ILIKE %s" % "%%"\
#                                + description + "%%")
#=================================================================

        self.results = Distribution.select(query)
        self.entries = self.results.count()
        return True

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


# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from sqlobject import LIKE, AND

from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp.dbschema import BugTaskStatus
from canonical.launchpad.interfaces import IBugTaskSet, ILaunchBag
from canonical.launchpad.searchbuilder import any
from canonical.launchpad.helpers import is_maintainer

BATCH_SIZE = 20

class DistroReleaseView(object):

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-details.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-actions.pt')

    linksPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-links.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        bugtasks_to_show = getUtility(IBugTaskSet).search(
            status = any(BugTaskStatus.NEW, BugTaskStatus.ACCEPTED),
            distrorelease = self.context, orderby = "-id")
        self.batch = Batch(
            list(bugtasks_to_show), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)
        self.is_maintainer = is_maintainer(self.context)

    def task_columns(self):
        return [
            "id", "package", "title", "status", "submittedby", "assignedto"]

    def assign_to_milestones(self):
        return []

class ReleasesAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def add_action(self):
        person = IPerson(self.request.principal, None)
        if not person:
            return False

        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")
        parent = self.request.get("parentrelease", "")

        if not (title and version and parent):
            return False

        distro_id = self.context.distribution.id

        dt = getUtility(IDistroTools)
        res = dt.createDistroRelease(person.id, title, distro_id,
                                     shortdesc, description, version,
                                     parent)
        self.results = res
        return res

    def getReleases(self):
        d_util = getUtility(IDistroTools)
        return d_util.getDistroReleases()

class ReleaseEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def edit_action(self):

        name = self.request.get("name", "")
        title = self.request.get("title", "")
        shortdesc = self.request.get("shortdesc", "")
        description = self.request.get("description", "")
        version = self.request.get("version", "")

        if not (name or title or description or version):
            return False

        ##XXX: (uniques) cprov 20041003
        self.context.release.name = name
        self.context.release.title = title
        self.context.release.shortdesc = shortdesc
        self.context.release.description = description
        self.context.release.version = version
        return True

class ReleaseSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sources = []
        self.binaries = []

    def search_action(self):
        name = self.request.get("name", "")
        context = self.context

        if not name:
            return False

        self.sources = list(context.findSourcesByName(name))
        self.binaries = list(context.findBinariesByName(name))
        return True


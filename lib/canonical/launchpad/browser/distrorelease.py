
# sqlobject/sqlos
from sqlobject import LIKE, AND

# lp imports
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.lp import dbschema                       

# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.component import getUtility


class DistroReleaseView(object):

    detailsPortlet = ViewPageTemplateFile(
        '../templates/portlet-distrorelease-details.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def bugSourcePackagesBatchNavigator(self):
        packages = list(self.context.bugSourcePackages())
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))

        batch = Batch(list=packages, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

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


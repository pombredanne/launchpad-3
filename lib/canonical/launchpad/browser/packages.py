# lp imports
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# interface import
from canonical.launchpad.database import IPerson

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# Stock View 
from canonical.launchpad.browser import ProductView

# LP imports
from canonical.lp.dbschema import BugSeverity

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages 
BATCH_SIZE = 40

class SourcePackageView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def affectedBinaryPackages(self):
        '''Return a list of [BinaryPackage, {severity -> count}]'''
        m = {}
        sevdef = {}
        for i in BugSeverity.items:
            sevdef[i.name] = 0
        for bugass in self.context.bugs:
            binarypackage = bugass.binarypackage
            if binarypackage:
                severity = BugSeverity.items[i].name
                stats = m.setdefault(binarypackage, sevdef.copy())
                m[binarypackage][severity] += 1
        rv = m.items()
        rv.sort(lambda a,b: cmp(a.id, b.id))
        return rv


#
# SourcePackage in a DistroRelease related classes
#

##XXX: (batch+duplicated) cprov 20041006
## The two following classes are almost like a duplicated piece
## of code. We should look for a better way for use Batching Pages
class DistroReleaseSourcesView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagesBatchNavigator(self):
        source_packages = list(self.context)
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = source_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

##XXX: (batch+duplicated) cprov 20041003
## AGAIN !!!
class DistrosReleaseSourcesSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def searchSourcesBatchNavigator(self):        

        name = self.request.get("name", "")

        if name:
            source_packages = list(self.context.findPackagesByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = source_packages, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None

class DistroReleaseSourceView(object):
    translationPortlet = ViewPageTemplateFile(
        '../templates/portlet-translations-sourcepackage.pt')
    watchPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroreleasesource-watch.pt')


    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)


    def productTranslations(self):
        if self.context.sourcepackage.product:
            return ProductView(self.context.sourcepackage.product,
                               self.request)
        return None

    def sourcepackageWatch(self):
        if self.person is not None:            
            return True

        return False

#
# BinaryPackage in a DistroRelease related classes
#

class DistroReleaseBinariesView(object):
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def binaryPackagesBatchNavigator(self):
        binary_packages = list(self.context)
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = binary_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

class DistrosReleaseBinariesSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        
    def searchBinariesBatchNavigator(self):        

        name = self.request.get("name", "")

        if name:
            binary_packages = list(self.context.findPackagesByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = binary_packages, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None



################################################################

# these are here because there is a bug in sqlobject that stub is fixing,
# once fixed they should be nuked, and pages/traverse* set to use getters.
# XXX
def urlTraverseProjects(projects, request, name):
    return projects[str(name)]


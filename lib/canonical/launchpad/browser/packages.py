from urllib import quote as urlquote

# lp imports
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# interface import
from canonical.launchpad.database import IPerson

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

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

class DistroSourcesView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

        release = urlquote(request.get("release", ""))
        name = urlquote(request.get("name", ""))
        if release and name:
            redirect = request.response.redirect
            redirect("%s/%s?name=%s" % (request.get('PATH_INFO'), 
                                        release, name))

##XXX: (batch+duplicated) cprov 20041006
## The two following classes are almost like a duplicated piece
## of code. We should look for a better way for use Batching Pages
class DistroReleaseSourcesView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagesBatchNavigator(self):
        name = self.request.get("name", "")
        showall = self.request.get("showall", "")

        if not (name or showall):
            return None

        if showall:
            source_packages = list(self.context)
        else:
            source_packages = list(self.context.findPackagesByName(name))

        if not source_packages:
            return None

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packages, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)

#
# Source Package
#

class DistroReleaseSourceView(object):
    translationPortlet = ViewPageTemplateFile(
        '../templates/portlet-translations-sourcepackage.pt')
    watchPortlet = ViewPageTemplateFile(
        '../templates/portlet-distroreleasesource-watch.pt')
    bugPortlet = ViewPageTemplateFile(
        '../templates/portlet-sourcepackage-bugcounter.pt')


    def __init__(self, context, request):
        self.context = context
        self.request = request

    def productTranslations(self):
        # XXX: Daniel Debonzi
        # It must still here until rosetta
        # merge it (or change) to launchpad/browser
        from canonical.rosetta.browser import ProductView

        if self.context.sourcepackage.product:
            return ProductView(self.context.sourcepackage.product,
                               self.request)
        return None

    def sourcepackageWatch(self):
        self.person = IPerson(self.request.principal, None)
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


__metaclass__ = type

from apt_pkg import ParseDepends

from urllib import quote as urlquote

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from canonical.lp.dbschema import BugSeverity
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.database import IPerson

# XXX: Daniel Debonzi
# Importing stuff from Soyuz directory
# Until have a place for it or better
# Solution
from canonical.soyuz.generalapp import builddepsSet
    

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages 
BATCH_SIZE = 40

class SourcePackageView:
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

class DistroSourcesView:
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
class DistroReleaseSourcesView:
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

class DistroReleaseSourceView:
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

class DistroReleaseBinariesView:
    
    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.fti = self.request.get("fti", "")

    def binaryPackagesBatchNavigator(self):
        name = self.request.get("name", "")
        
        if not name:
            binary_packages = []
            # XXX: Daniel Debonzi 20050104
            # Returns all binarypackage available.
            # Do not work with more than 45000 binarypackage
            # (Actual dogfood db)
            #binary_packages = list(self.context)
        else:
            binary_packages = list(self.context.findPackagesByArchtagName(name,
                                                                          self.fti))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = binary_packages, start = start,
                      size = batch_size)

        return BatchNavigator(batch = batch, request = self.request)

class DistrosReleaseBinariesSearchView:
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

class SourcePackageBugsView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.batch = Batch(
            self.bugassignment_search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def bugassignment_search(self):
        return self.context.bugs

    def assignment_columns(self):
        return [
            "id", "title", "status", "priority", "severity",
            "submittedon", "submittedby", "assignedto", "actions"]

class BinaryPackageView(object):
    """View class for BinaryPackage"""

    lastversionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-binarypackage-lastversions.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _buildList(self, packages):
        blist = []
        if packages:
            packs = ParseDepends(packages)
            for pack in packs:
                blist.append(builddepsSet(*pack[0]))
                                          
        return blist

    def depends(self):
        return self._buildList(self.context.depends)

    def recommends(self):
        return self._buildList(self.context.recommends)

    def conflicts(self):
        return self._buildList(self.context.conflicts)

    def replaces(self):
        return self._buildList(self.context.replaces)

    def suggests(self):
        return self._buildList(self.context.suggests)

    def provides(self):
        return self._buildList(self.context.provides)

    
################################################################

# these are here because there is a bug in sqlobject that stub is fixing,
# once fixed they should be nuked, and pages/traverse* set to use getters.
# XXX
def urlTraverseProjects(projects, request, name):
    return projects[str(name)]


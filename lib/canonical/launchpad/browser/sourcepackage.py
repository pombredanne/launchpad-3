# sqlobject/sqlos
from sqlobject import LIKE, AND

# Python standard library imports
from apt_pkg import ParseSrcDepends

# lp imports
from canonical.lp import dbschema                       

# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# interface import
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import IPerson,\
                                           IPersonSet, \
                                           IDistroTools, \
                                           ILaunchBag

# depending on apps
from canonical.soyuz.generalapp import builddepsSet


BATCH_SIZE = 40

class SourcePackageReleasePublishingView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


    def builddepends(self):
        if not self.context.builddepends:
            return []
        
        builddepends = []

        depends = ParseSrcDepends(self.context.builddepends)
        for dep in depends:
            builddepends.append(builddepsSet(*dep[0]))
        return builddepends


    def builddependsindep(self):
        if not self.context.builddependsindep:
            return []
        builddependsindep = []
        
        depends = ParseSrcDepends(self.context.builddependsindep)
        
        for dep in depends:
            builddependsindep.append(builddepsSet(*dep[0]))
        return builddependsindep
                
class SourcePackageInDistroSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)
    
    def sourcePackagesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            source_packages = list(self.context)
        else:
            source_packages = list(self.context.findPackagesByName(name))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=source_packages, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)


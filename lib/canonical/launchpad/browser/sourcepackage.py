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
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.interfaces import IPersonSet
from canonical.launchpad.interfaces import IDistroTools

# depending on apps
from canonical.soyuz.generalapp import builddepsSet

class SourcePackageReleaseView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request


    def builddepends(self):
        if not self.context.sourcepackagerelease.builddepends:
            return None
        
        builddepends = ([], [], [])

        depends = ParseSrcDepends(self.context.sourcepackagerelease.builddepends)

        for i in range(len(depends)):
            dep = depends[i]
            builddepends[i % 3].append(builddepsSet(*dep[0]))
        return builddepends


    def builddependsindep(self):
        if not self.context.sourcepackagerelease.builddependsindep:
            return None
        builddependsindep = ([], [], [])
        
        depends = ParseSrcDepends(self.context.sourcepackagerelease.builddependsindep)
        
        for i in range(len(depends)):
            dep = depends[i]
            builddependsindep[i % 3].append(builddepsSet(*dep[0]))
        return builddependsindep
                



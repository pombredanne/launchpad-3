# sqlobject/sqlos
from sqlobject import LIKE, AND

# Python standard library imports
import cgi
import re
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
    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-sourcepackagerelease-actions.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.bag = getUtility(ILaunchBag)

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
                
    def linkified_changelog(self):
        # XXX: salgado: No bugtracker URL should be hardcoded.
        changelog = cgi.escape(self.context.changelog)
        sourcepkgname = self.context.sourcepackage.sourcepackagename.name
        deb_bugs = 'http://bugs.debian.org/cgi-bin/bugreport.cgi?bug='
        warty_bugs = 'https://bugzilla.ubuntu.com/show_bug.cgi?id='
        changelog = re.sub(r'%s \(([^)]+)\)' % sourcepkgname,
                           r'%s (<a href="../\1">\1</a>)' % sourcepkgname,
                           changelog)
        changelog = re.sub(r'(([Ww]arty|[Uu]buntu) *#)([0-9]+)', 
                           r'<a href="%s\3">\1\3</a>' % warty_bugs,
                           changelog)
        changelog = re.sub(r'[^(W|w)arty]#([0-9]+)', 
                           r'<a href="%s\1">#\1</a>' % deb_bugs,
                           changelog)
        return changelog


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


# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'SourcePackageView',
    'DistroSourcesView',
    'DistrosReleaseBinariesSearchView',
    'SourcePackageBugsView',
    'BinaryPackageView',
    ]

from apt_pkg import ParseDepends

from urllib import quote as urlquote

from zope.component import getUtility

from canonical.lp.dbschema import BugTaskSeverity
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import ILaunchBag

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
        for i in BugTaskSeverity.items:
            sevdef[i.name] = 0
        for bugtask in self.context.bugtasks:
            binarypackage = bugtask.binarypackage
            if binarypackage:
                severity = BugTaskSeverity.items[i].name
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

#
# Source Package
#


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
            list(self.bugtask_search()), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def bugtask_search(self):
        return self.context.bugtasks

    def task_columns(self):
        return [
            "id", "title", "status", "priority", "severity",
            "submittedon", "submittedby", "assignedto", "actions"]

class BinaryPackageView(object):
    """View class for BinaryPackage"""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.launchbag = getUtility(ILaunchBag)

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


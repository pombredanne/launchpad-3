
#
# The Bazaar application. Interface, view and context have all been put
# into this one file because they are trivial, they should be moved to
# distinct files.
#

from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.interface import implements
from zope.component import getUtility

from canonical.launchpad.interfaces import \
    ILaunchpadApplication, IProductSeriesSet

from canonical.lp.dbschema import ImportStatus

class IBazaarApplication(ILaunchpadApplication):
    """A Bazaar Application"""


class BazaarApplication:
    implements(IBazaarApplication)

    def __init__(self):
        self.title = 'The Open Source Bazaar'

class BazaarApplicationView(object):

    importsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-upstream-imports.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.seriesset = getUtility(IProductSeriesSet)

    def import_count(self):
        return self.seriesset.importcount()

    def testing_count(self):
        return self.seriesset.importcount(ImportStatus.TESTING.value)

    def autotested_count(self):
        return self.seriesset.importcount(ImportStatus.AUTOTESTED.value)

    def testfailed_count(self):
        return self.seriesset.importcount(ImportStatus.TESTFAILED.value)

    def processing_count(self):
        return self.seriesset.importcount(ImportStatus.PROCESSING.value)

    def syncing_count(self):
        return self.seriesset.importcount(ImportStatus.SYNCING.value)

    def stopped_count(self):
        return self.seriesset.importcount(ImportStatus.STOPPED.value)


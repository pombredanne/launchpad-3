# zope imports
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.browser.add import AddView
from zope.app.form.interfaces import WidgetsError
from zope.app.form.browser import SequenceWidget, ObjectWidget
from zope.app.form import CustomWidgetFactory

# launchpad import
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# launchpad database and interfaces import
from canonical.launchpad.database import BinaryPackageName
from canonical.launchpad.interfaces import IBinaryPackageName

BATCH_SIZE = 40

class BinaryPackageNameSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def binaryPackagenamesBatchNavigator(self):
        name = self.request.get("name", "")

        if not name:
            binary_packagenames = list(self.context)
        else:
            binary_packagenames = list(self.context.findByName(name))

        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE

        batch = Batch(list=binary_packagenames, start=start, size=batch_size)
        return BatchNavigator(batch=batch, request=self.request)

class BinaryPackageNameAddView(AddView):

    __used_for__ = IBinaryPackageName

    ow = CustomWidgetFactory(ObjectWidget, BinaryPackageName)
    sw = CustomWidgetFactory(SequenceWidget, subwidget=ow)
    options_widget = sw
    

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self._nextURL = '.'
        AddView.__init__(self, context, request)

    def createAndAdd(self, data):
        self.name = data['name']
        BinaryPackageName.ensure(self.name)
        self._nextURL = '.?name=%s'%self.name
        
    def nextURL(self):
        return self._nextURL


from zope.component import getUtility
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator
from canonical.launchpad.interfaces import IProductSet
from canonical.lp.dbschema import SourceSourceStatus

class SourceSourceView(object):
    """Present a SourceSource table for a browser."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        if not self.request.form.get("Update", None) == "Update Upstream Source":
            return
        if not self.request.method == "POST":
            return
        #
        # Extract the form data
        #

        fields = ["title",
                  "description",
                  "cvsroot",
                  "cvsmodule",
                  "cvstarfileurl",
                  "cvsbranch",
                  "svnrepository",
                  "releaseroot",
                  "releaseverstyle",
                  "releasefileglob",
                  "newarchive",
                  "archversion",
                  "newbranchcategory",
                  "newbranchbranch",
                  "newbranchversion"]
        for f in fields:
            v = self.form.get(f, None)
            if v is not None:
                setattr(self.context, f, v)
        if self.form.get('syncCertified', None):
            if not self.context.syncCertified():
                self.context.certifyForSync()
        if self.form.get('autoSyncEnabled', None):
            if not self.context.autoSyncEnabled():
                self.context.enableAutoSync()
        product = self.form.get('product', None)
        if product and self.context.canChangeProduct():
            self.context.changeProduct(product)
            newurl='/doap/products/' + self.context.product.name
            self.request.response.redirect(newurl)


    def selectedProduct(self):
        return self.context.product.name # "/" + self.context.product.project.name

    def products(self):
        """all the products that context can switch between"""
        products = getUtility(IProductSet)
        for product in products:
            if product.name != "unassigned":
                yield product.name


class SourceSourceSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.ready = request.form.get('ready', None)
        self.sync = request.form.get('sync', None)
        self.process = request.form.get('process', None)
        self.tested = request.form.get('tested', None)
        self.assigned = request.form.get('assigned', None)
        self.text = request.form.get('text', None)
        try:
            self.state = int(request.form.get('state', None))
        except (ValueError, TypeError):
            self.state = None
        # setup the initial values if there was no form submitted
        if request.form.get('search', None) is None:
            self.ready = 'on'
            self.tested = 'on'
            self.assigned = 'on'
        self.batch = Batch(self.search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def search(self):
        return list(self.context.search(ready = self.ready,
                                        text=self.text,
                                        state=self.state))
        #return list(self.context.filter(sync=self.sync,
        #                           process=self.process,
        #                           tested=self.tested,
        #                           text=self.text,
        #                           assigned=self.assigned))

    def sourcestateselector(self):
        html = '<select name="state">\n'
        html += '  <option value="ANY"'
        if self.state == None:
            html += ' selected'
        html += '>Any</option>\n'
        for enum in SourceSourceStatus.items:
            html += '<option value="'+str(enum.value)+'"'
            if self.state == enum.value:
                html += ' selected'
            html += '>' + str(enum.title) + '</option>\n'
        html += '</select>\n'
        return html
        html += '  <option value="DONTSYNC"'
        if self.state == 'DONTSYNC':
            html += ' selected'
        html += '>Do Not Sync</option>\n'
        html += '  <option value="TESTING"'
        if self.state == 'TESTING':
            html += ' selected'
        html += '>Testing</option>\n'
        html += '  <option value="AUTOTESTED"'
        if self.state == 'AUTOTESTED':
            html += ' selected'
        html += '>Auto-Tested</option>\n'
        html += '  <option value="PROCESSING"'
        if self.state == 'PROCESSING':
            html += ' selected'
        html += '>Processing</option>\n'
        html += '  <option value="SYNCING"'
        if self.state == 'SYNCING':
            html += ' selected'
        html += '>Syncing</option>\n'
        html += '  <option value="STOPPED"'
        if self.state == 'STOPPED':
            html += ' selected'
        html += '>Stopped</option>\n'




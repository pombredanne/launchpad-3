
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

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

        fields = ["title"
                  "description"
                  "cvsroot"
                  "cvsmodule"
                  "cvstarfileurl"
                  "cvsbranch"
                  "svnrepository"
                  "releaseroot"
                  "releaseverstyle"
                  "releasefileglob"
                  "newarchive"
                  "archversion"
                  "newbranchcategory"
                  "newbranchbranch"
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
            newurl='../../../../' + self.context.product.project.name + "/" + self.context.product.name
            self.request.response.redirect(newurl)


    def selectedProduct(self):
        return self.context.product.name + "/" + self.context.product.project.name

    def products(self):
        """all the products that context can switch between"""
        """ugly"""
        from canonical.soyuz.importd import ProjectMapper, ProductMapper
        projMapper=ProjectMapper()
        prodMapper=ProductMapper()
        for project in projMapper.findByName("%%"):
            if project.name != "do-not-use-info-imports":
                for product in prodMapper.findByName("%%", project):
                    name=project.name + "/" + product.name
                    if name != "do-not-use-info-imports/unassigned":
                        yield name


class SourceSourceSetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.ready = request.form.get('ready', None)
        self.sync = request.form.get('sync', None)
        self.process = request.form.get('process', None)
        self.tested = request.form.get('tested', None)
        self.text = request.form.get('text', None)
        # setup the initial values if there was no form submitted
        if request.form.get('search', None) is None:
            self.ready = 'on'
            self.tested = 'on'
        self.batch = Batch(self.search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def search(self):
        return list(self.context.filter(sync=self.sync,
                                   process=self.process,
                                   tested=self.tested,
                                   text=self.text))




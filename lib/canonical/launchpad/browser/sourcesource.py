
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

class SourceSourceView(object):
    """Present a SourceSource table for a browser."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.form = request.form

    def edit(self):
        if not self.request.form.get("Update", None)=="Update Upstream Source":
            return
        if not self.request.method == "POST":
            return
        formdata = {}
        #
        # Extract the form data
        #
        title = self.form.get('title', None)
        description = self.form.get('description', None)
        cvsroot = self.form.get('cvsroot', None)
        cvsmodule = self.form.get('cvsmodule', None)
        cvstarfileurl = self.form.get('cvstarfileurl', None)
        cvsbranch = self.form.get('cvsbranch', None)
        svnrepository = self.form.get('svnrepository', None)
        releaseroot = self.form.get('releaseroot', None)
        releaseverstyle = self.form.get('releaseverstyle', None)
        releasefileglob = self.form.get('releasefileglob', None)
        newarchive = self.form.get('newarchive', None)
        archversion = self.form.get('newbranchcategory', None)
        newbranchcategory = self.form.get('newbranchcategory', None)
        newbranchbranch = self.form.get('newbranchbranch', None)
        newbranchversion = self.form.get('newbranchversion', None)
        product = self.form.get('product', None)
        if title: self.context.title = title
        if description: self.context.description = description
        if cvsroot: self.context.cvsroot = cvsroot
        if cvsmodule: self.context.cvsmodule = cvsmodule
        if cvstarfileurl: self.context.cvstarfileurl = cvstarfileurl
        if cvsbranch: self.context.cvsbranch = cvsbranch
        if svnrepository: self.context.svnrepository = svnrepository
        if releaseroot: self.context.releaseroot = releaseroot
        if releaseverstyle: self.context.releaseverstyle = releaseverstyle
        if releasefileglob: self.context.releasefileglob = releasefileglob
        if newarchive: self.context.newarchive = newarchive
        if newbranchcategory: self.context.newbranchcategory = newbranchcategory
        if newbranchbranch: self.context.newbranchbranch = newbranchbranch
        if newbranchversion: self.context.newbranchversion = newbranchversion
        if self.form.get('syncCertified', None):
            if not self.context.syncCertified():
                self.context.certifyForSync()
        if self.form.get('autoSyncEnabled', None):
            if not self.context.autoSyncEnabled():
                self.context.enableAutoSync()
        newurl = None
        if product and self.context.canChangeProduct():
            self.context.changeProduct(product)
            newurl='../../../../' + self.context.product.project.name + "/" + self.context.product.name
        if newurl:
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
        self.sync = request.form.get('sync', None)
        self.process = request.form.get('process', None)
        self.tested = request.form.get('tested', None)
        self.projecttext = request.form.get('projecttext', None)
        self.batch = Batch(self.search(), int(request.get('batch_start', 0)))
        self.batchnav = BatchNavigator(self.batch, request)

    def search(self):
        return list(self.context.filter(sync=self.sync, process=self.process,
                                   tested=self.tested,
                                   projecttext=self.projecttext))




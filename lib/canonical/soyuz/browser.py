from canonical.soyuz.sql import SoyuzDistribution, Release, SoyuzPerson
from canonical.soyuz.database import SoyuzSourcePackage
from sqlobject import LIKE, OR, AND



class DistrosSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_results = False

        name = self.request.get("name", "")
        title = self.request.get("title", "")
        description = self.request.get("description", "")

        #FIXME: add operator '%' for query all distros
        if name or title or description:
            
            name_like = LIKE(SoyuzDistribution.q.name, "%%"+name+"%%")
            title_like = LIKE(SoyuzDistribution.q.title, "%%"+title+"%%")
            description_like = LIKE(SoyuzDistribution.q.description,
                                    "%%"+description+"%%")
            self.results = SoyuzDistribution.select(AND(name_like, title_like,\
                                                        description_like))
            self.entries = self.results.count()
            self.enable_results = True                
            
class PeopleSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_results = False       

        name = self.request.get("name", "")

        #FIXME: add operator '%' to query all persons
        #FIXME: use 'UPPER(field) LIKE UPPER('%%name%%') 
        if name:
            name_like = LIKE(SoyuzPerson.q.displayname,
                             '%%' + name + '%%')
            self.results = SoyuzPerson.select(AND(name_like))

            self.entries = self.results.count()
            self.enable_results = True

class DistrosAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_added = False
        
        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")

        if name or title or description:
            #FIXME: verify unique name before insert new distro
            #FIXME: the owner is hardcoded to Mark !!!!
            #How will we handler Security/Authentication Issues ?!?!
            self.results = SoyuzDistribution(name=name, title=title, \
                                             description=description,\
                                             domainname='domain', owner=1)
            #FIXME: verify results
            self.enable_added = True
    

class DistrosEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_edited = False

        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")

        if name or title or description:
            #FIXME: verify the unique name before update distro
            self.context.distribution.name = name
            self.context.distribution.title = title
            self.context.distribution.description = description
            self.enable_edited = True


class ReleasesAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_added = False

        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")
        version = self.request.get("version", "").encode("ascii")

        if name or title or description or version:
            #FIXME: verify unique name before insert a new release
            #FIXME: get current UTC
            #FIXME: What about figure out finally what to do with
            #      components, sections ans so on ...
            #FIXME: parentrelease hardcoded to "warty" 
            self.results = Release(distribution=self.context.distribution.id,\
                                   name=name, title=title, \
                                   description=description,version=version,\
                                   components=1, releasestate=1,sections=1,\
                                   datereleased='2004-08-15 10:00', owner=1,
                                   parentrelease=1)
            #FIXME: verify the results 
            self.enable_added = True
            
class ReleasesEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_edited = False
        
        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")
        version = self.request.get("version", "").encode("ascii")

        if name or title or description or version:
            #FIXME: verify unique name before update release information
            self.context.release.name = name
            self.context.release.title = title
            self.context.release.description = description
            self.context.release.version = version
            #FIXME: verify the results 
            self.enable_edited = True
            
class DistrosReleaseSourcesSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        name = request.get("name", "")
        if name:
            self.results = list(context.findPackagesByName(name))
        else:
            self.results = []

class DistrosReleaseBinariesSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        name = request.get("name", "")
        if name:
            self.results = list(context.findPackagesByName(name))
        else:
            self.results = []


################################################################

# these are here because there is a bug in sqlobject that stub is fixing,
# once fixed they should be nuked, and pages/traverse* set to use getters.
# XXX FIXME
def urlTraverseProjects(projects, request, name):
    return projects[str(name)]

def urlTraverseProducts(project, request, name):
    return project.getProduct(str(name))
    
def urlTraverseSyncs(product, request, name):
    return product.getSync(str(name))

# DONE!

class ViewProjects(object):
    def projects(self):
        return iter(self.context.projects())
    def handle_submit(self):
        if not self.request.form.get("Register", None)=="Register":
            return
        if not self.request.method == "POST":
            return
        name=self.request.form['name']
        url=self.request.form['url']
        description=self.request.form['description']
        title=self.request.form['title']
        
        self.request.response.redirect(name)
        self.context.new(name,title,description,url)
        self.submittedok= True


class ViewProject(object):
    def products(self):
        return self.context.products()
    def handle_submit(self):
        if not self.request.form.get("Register", None)=="Register":
            return
        if not self.request.method == "POST":
            return
        name=self.request.form['name']
        url=self.request.form['url']
        description=self.request.form['description']
        title=self.request.form['title']
        
        self.request.response.redirect(name)
        self.context.newProduct(name,title,description,url)
        self.submittedok= True

class View(object):
    def setArg(self, name, kwargs):
        kwargs[name]=self.getField(name)
    def getField(self, name):
        return self.request.form[name]
        
class ViewProduct(View):
    def syncs(self):
        return iter(self.context.syncs())
    def handle_submit(self):
        if not self.request.form.get("Register", None)=="Register":
            return
        if not self.request.method == "POST":
            return
        kwargs={}
        for param in ["name", "title","description","cvsroot","module","cvstarfile","branchfrom","svnrepository","category","branchto","archversion","archsourcegpgkeyid","archsourcename","archsourceurl"]:
            self.setArg(param, kwargs)
        self.context.newSync(**kwargs)
        self.submittedok=True
        self.request.response.redirect('f') #kwargs['name'])

class ViewSync(View):
    """har har"""
    def handle_submit(self):
        if not self.request.form.get("Update", None)=="Update":
            return
        if not self.request.method == "POST":
            return
        kwargs={}
        for param in ["name", "title", "description", "cvsroot", "cvsmodule","cvstarfile",
            "branchfrom","svnrepository","archarchive","category","branchto","archversion","archsourcegpgkeyid","archsourcename","archsourceurl"]:
            self.setArg(param, kwargs)
        newurl=None
        if kwargs.get('name', self.context.name) != self.context.name:
            newurl='../' + kwargs['name']
        self.context.update(**kwargs)
        if self.context.canChangeProduct() and self.request.form.has_key('product'):
            self.context.changeProduct(self.request.form.get('product'))
            newurl='../../../' + self.context.product.project.name + "/" + self.context.product.name #+ '/' + self.context.name
        self.submittedok=True
        if newurl:
            self.request.response.redirect(newurl)
    def selectedProduct(self):
        return self.context.product.name + "/" + self.context.product.project.name
    def products(self):
        """all the products that context can switch between"""
        """ugly"""
        from canonical.soyuz.sql import ProjectMapper, ProductMapper
        projMapper=ProjectMapper()
        prodMapper=ProductMapper()
        for project in projMapper.findByName("%%"):
            if project.name != "do-not-use-info-imports":
                for product in prodMapper.findByName("%%", project):
                    name=project.name + "/" + product.name
                    if name != "do-not-use-info-imports/unassigned":
                        yield name


#arch-tag: 985007b4-9c10-4601-b3ce-bdb03576569f

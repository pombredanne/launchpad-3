from canonical.soyuz.sql import Distribution
from sqlobject import LIKE, OR, AND


class DistrosApplication(object):
    def __getitem__(self, name):
        return Distribution.selectBy(name=name.encode("ascii"))[0]

    def __iter__(self):
    	return iter(Distribution.select())

class DistrosSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")

        if name or title or description:
            name_like = LIKE(Distribution.q.name, "%%"+name+"%%")
            title_like = LIKE(Distribution.q.title, "%%"+title+"%%")
            description_like = LIKE(Distribution.q.description,
                                    "%%"+description+"%%")
            self.results = Distribution.select(AND(name_like, title_like, description_like))



class DistrosAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

        name = self.request.get("name", "").encode("ascii")
        title = self.request.get("title", "").encode("ascii")            
        description = self.request.get("description", "").encode("ascii")

        if name or title or description:
            #YAPS: the owner is hardcodes to Mark !!!!
            #How will we handler Security/Authentication Issues ?!?!
            Distribution(name=name, title=title, description=description,\
                         owner=1)
                
    
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
        for param in ["name", "title", "description", "cvsroot"]:
            self.setArg(param, kwargs)
        newurl=kwargs.get('name', self.context.name) != self.context.name
        print newurl
        self.context.update(**kwargs)
        self.submittedok=True
        if newurl:
            self.request.response.redirect('../' + kwargs['name'])


#arch-tag: 985007b4-9c10-4601-b3ce-bdb03576569f

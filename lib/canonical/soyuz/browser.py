from canonical.soyuz.sql import SoyuzDistribution, Release, SoyuzPerson

from canonical.soyuz.database import SoyuzSourcePackage, SoyuzBinaryPackage

from canonical.soyuz.database import TeamParticipation, SoyuzEmailAddress
from canonical.soyuz.database import GPGKey, ArchUserID, WikiName, JabberID
from canonical.soyuz.database import IrcID, Membership
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from sqlobject import LIKE, OR, AND

from canonical.database.sqlbase import quote

from canonical.lp import dbschema

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
            self.results = SoyuzDistribution.select(AND(name_like, title_like,
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

        if name:
            name = name.replace('%', '%%')
            query = quote('%%'+ name.upper() + '%%')

            #FIXME: 'ORDER by displayname' doesn't work properly
            self.results = SoyuzPerson.select('UPPER(displayname) LIKE %s OR \
            UPPER(teamdescription) LIKE %s'%(query,query))

            self.entries = self.results.count()
            self.enable_results = True


class PeopleAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_added = False

        displayname = self.request.get("displayname", "")
        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        email = self.request.get("email", "")
        password = self.request.get("password", "")
        retype = self.request.get("retype", "")

        #FIXME verify password == retype
        if displayname:
            #FIXME: How to get the true DB result of the INSERT ?
            self.results = SoyuzPerson(displayname=displayname,
                                       givenname=givenname,
                                       familyname=familyname,
                                       password=password,
                                       teamownerID=None,
                                       teamdescription=None,
                                       karma=None,
                                       karmatimestamp=None)

            SoyuzEmailAddress(person=self.results.id,
                         email=email,
                         status=int(dbschema.EmailAddressStatus.NEW))

            self.enable_added = True

class TeamAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_added = False

        displayname = self.request.get("displayname", "")
        teamdescription = self.request.get("teamdescription", "")

        #FIXME: How to get the true DB result of the INSERT ?
        if displayname:

            #FIXME the team is owned by the current ID now,
            # but it should comes from authserver
            self.results = SoyuzPerson(displayname=displayname,
                                       givenname=None,
                                       familyname=None,
                                       password=None,
                                       teamdescription=teamdescription,
                                       teamowner=self.context.id,
                                       karma=None,
                                       karmatimestamp=None)

            TeamParticipation(personID=self.results.id,
                              teamID=self.context.id)

            ##FIXME: what about Membership ? the owner should be always
            ##       the admin ? I supose not and

            self.enable_added = True

class TeamJoinView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_join = False

        dummy_id = self.request.get("id", "")
        proto_role = self.request.get("role", "")
        proto_status = self.request.get("status", "")

        role = dbschema.MembershipRole.MEMBER
        for item in dbschema.MembershipRole.items:
            if item.title == proto_role:
                role = item.value

        status = dbschema.MembershipStatus.PROPOSED
        for item in dbschema.MembershipStatus.items:
            if item.title == proto_status:
                status = item.value


        if dummy_id:
            self.person = SoyuzPerson.get(dummy_id)
            #FIXME: verify if the person is already a member
            self.results = Membership(personID=dummy_id,
                                      team=self.context.id,
                                      role=role,
                                      status=status)

            #FIXME: How to do it recursively as it is suposed to be
            self.results = TeamParticipation(personID=dummy_id,
                                             teamID=self.context.id)

            self.enable_join = True


class PersonEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.enable_edited = False

        displayname = self.request.get("displayname", "")
        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        teamdescription = self.request.get("teamdescription", "")

        email = self.request.get("email", "")
        wiki = self.request.get("wiki", "")
        wikiname = self.request.get("wikiname", "")
        network = self.request.get("network", "")
        nickname = self.request.get("nickname", "")
        jabberid = self.request.get("jabberid", "")
        archuserid = self.request.get("archuserid", "")
        gpgid = self.request.get("gpgid", "")

        #FIXME: verify the unique name before update distro
        if displayname :
            self.context.person.displayname = displayname
            self.context.person.givenname = givenname
            self.context.person.familyname = familyname
            self.context.person.teamdescription = teamdescription
            self.enable_edited = True

            #EmailAddress
            if self.context.email:
                self.context.email.email = email
                self.enable_edited = True
            else:
                try:
                    self.context.email = Soyuz.EmailAddress(personID=self.context.person.id,
                                                            email=email,
                                                            status=int(dbschema.EmailAddressStatus.NEW))
                except:
                    pass
            #WikiName
            if self.context.wiki:
                self.context.wiki.wiki = wiki
                self.context.wiki.wikiname = wikiname
                self.enable_edited = True
            else:
                try:
                    self.context.wiki = WikiName(personID=self.context.person.id,
                                                 wiki=wiki,
                                                 wikiname=wikiname)
                except:
                    pass
            #IrcID
            if self.context.irc:
                self.context.irc.network = network
                self.context.irc.nickname = nickname
                self.enable_edited = True
            else:
                try:
                    self.context.irc = IrcID(personID=self.context.person.id,
                                             network=network,
                                             nickname=nickname)
                except IndexError:
                    pass
            #JabberID
            if self.context.jabber:
                self.context.jabber.jabberid = jabberid
                self.enable_edited = True
            else:
                try:
                    self.context.jabber = JabberID(personID=self.context.person.id,
                                                   jabberid=jabberid)
                except IndexError:
                    pass
            #ArchUserID
            if self.context.archuser:
                self.context.archuser.archuserid = archuserid
                self.enable_edited = True
            else:
                try:
                    self.context.archuser = ArchUserID(personID=self.context.person.id,
                                                   archuserid=archuserid)
                except IndexError:
                    pass



            #GPGKey
            if self.context.gpg:
                self.context.gpg.keyid = gpgid
                self.enable_edited = True
            else:
                try:
                    #FIXME: lazy unique fingerprint and pubkey
                    fingerprint = 'sample%d'%self.context.id
                    pubkey = fingerprint

                    self.context.gpg = GPGKey(personID=self.context.person.id,
                                              keyid=gpgid,
                                              fingerprint=fingerprint,
                                              pubkey=pubkey,
                                              revoked=False)
                except IndexError:
                    pass

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

class DistroReleaseSourcesView(object):

    BATCH_SIZE = 20

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def sourcePackagesBatchNavigator(self):
        source_packages = list(self.context)
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', self.BATCH_SIZE))
        batch_size = self.BATCH_SIZE
        batch = Batch(
            list = source_packages, start = start, size = batch_size)
        return BatchNavigator(batch = batch, request = self.request)

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

class ReleaseEditView(object):

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

class ReleaseSearchView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.sources = []
        self.binaries = []

        name = request.get("name", "")

        if name:
            self.sources = list(context.findSourcesByName(name))
            self.binaries = list(context.findBinariesByName(name))
        else:
            self.sources = []
            self.binaries = []

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

class View(object):
    def setArg(self, name, kwargs):
        kwargs[name]=self.getField(name)
    def getField(self, name):
        return self.request.form[name]

class ViewProjects(View):
    def projects(self):
        return iter(self.context)
    def handle_submit(self):
        if not self.request.form.get("Register", None)=="Register":
            return
        if not self.request.method == "POST":
            return
        name=self.getField('name')
        url=self.getField('url')
        description=self.getField('description')
        title=self.getField('title')
        shortDescription=self.getField('shortDescription')
        displayName=self.getField('displayName')

        project=self.context.new(name,title,description,url)
        project.shortDescription(shortDescription)
        project.displayName(displayName)
        project=None
        self.submittedok= True
        self.request.response.redirect(name)


class ViewProject(View):
    def products(self):
        return self.context.products()
    def handle_submit(self):
        if not self.request.form.get("Register", None)=="Register":
            return
        if not self.request.method == "POST":
            return
        name=self.getField('name')
        url=self.getField('url')
        description=self.getField('description')
        title=self.getField('title')

        self.request.response.redirect(name)
        self.context.newProduct(name,title,description,url)
        self.submittedok= True

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
        self.request.response.redirect(kwargs['name'])

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
        if self.request.form.get('enabled', None):
            if not self.context.enabled():
                self.context.enable()
        if self.request.form.get('autosyncenabled', None):
            if not self.context.autosyncing():
                self.context.autosync()
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

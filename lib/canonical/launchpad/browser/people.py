# Copyright 2004 Canonical Ltd
# sqlobject/sqlos
from sqlobject import LIKE, AND, SQLObjectNotFound
from canonical.database.sqlbase import quote

# lp imports
from canonical.lp import dbschema
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# database imports
from canonical.launchpad.database import WikiName
from canonical.launchpad.database import JabberID
from canonical.launchpad.database import TeamParticipation, Membership
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID
from canonical.launchpad.database import createPerson
from canonical.launchpad.database import createTeam
from canonical.launchpad.database import Project
from canonical.launchpad.database import Person
from canonical.launchpad.database import SSHKey

# interface import
from canonical.launchpad.interfaces import IPerson
from canonical.launchpad.interfaces import IPasswordEncryptor

# zope imports
import zope
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent, ObjectModifiedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages
BATCH_SIZE = 40


class BaseListView(object):

    header = ""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _getBatchNavigator(self, list):
        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=list, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def getTeamsList(self):
        results = Person.select(Person.q.teamownerID!=None,
                                orderBy='displayname')
        return self._getBatchNavigator(list(results))

    def getPeopleList(self):
        results = Person.select(Person.q.teamownerID==None,
                                orderBy='displayname')
        return self._getBatchNavigator(list(results))


class PeopleListView(BaseListView):

    header = "People List"

    def getList(self):
        return self.getPeopleList()


class TeamListView(BaseListView):

    header = "Team List"

    def getList(self):
        return self.getTeamsList()


class FOAFSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def searchPeopleBatchNavigator(self):
        name = self.request.get("name", "")
        searchfor = self.request.get("searchfor", "")

        if not name:
            return None

        if searchfor == "all":
            results = self._findPeopleByName(name)
        elif searchfor == "peopleonly":
            results = self._findPeopleByName(name, peopleonly=True)
        elif searchfor == "teamsonly":
            results = self._findPeopleByName(name, teamsonly=True)

        people = list(results)
        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=people, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def _findPeopleByName(self, name, peopleonly=False, teamsonly=False):
        # This method is somewhat weird, cause peopleonly and teamsonly
        # are mutually exclusive.
        query = "fti @@ ftq(%s)" % quote(name)
        if peopleonly:
            query += " AND teamowner is NULL"
        elif teamsonly:
            query += " AND teamowner is not NULL"
        return Person.select(query, orderBy='displayname')


class BaseAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL


class TeamAddView(BaseAddView):

    def createAndAdd(self, data):
        person = IPerson(self.request.principal, None)
        if not person:
            raise zope.security.interfaces.Unauthorized, "Need an authenticated owner"

        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        team = createTeam(kw['displayname'], person.id,
                          kw['teamdescription'], kw['email'])
        notify(ObjectCreatedEvent(team))
        self._nextURL = team.name
        return team


class PeopleAddView(BaseAddView):

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value
        if kw['password'] != kw['password2']:
            self._nextURL = '+new'
            return None
        person = createPerson(kw['displayname'], kw['givenname'],
                              kw['familyname'], kw['password'], kw['email'])
        if person:
            notify(ObjectCreatedEvent(person))
            self._nextURL = person.name
        return person


class PersonView(object):
    """ A Base class for views of a specific person/team. """

    leftMenu = ViewPageTemplateFile('../templates/foaf-menu.pt')
    packagesPortlet = ViewPageTemplateFile(
        '../templates/portlet-person-packages.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.person = IPerson(self.request.principal, None)

    def is_member(self):
        if self.person and self.context.teamowner:
            membership = Membership.selectBy(personID=self.person.id,
                                             teamID=self.context.id)
            if membership.count() > 0:
                return True

        return False

    def unjoin_action(self):
        if self.person:
            teampart = TeamParticipation.selectBy(personID=self.person.id,
                                                  teamID=self.context.id)[0]

            membership = Membership.selectBy(personID=self.person.id,
                                             teamID=self.context.id)[0]
            teampart.destroySelf()
            membership.destroySelf()
            return True

        return False


class PersonEditView(PersonView):

    def __init__(self, context, request):
        PersonView.__init__(self, context, request)
        self.results = []
        self.errormessage = None

    def edit_action(self):
        if self.request.get("REQUEST_METHOD") != "POST":
            # Nothing to do
            return False

        person = self.context

        password = self.request.get("password", "")
        newpassword = self.request.get("newpassword", "")
        newpassword2 = self.request.get("newpassword2", "")
        displayname = self.request.get("displayname", "")

        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, person.password):
            self.errormessage = "Wrong password. Please try again."
            return False

        ##XXX: (uniques) cprov 20041003
        if not displayname:
            self.errormessage = "Wrong password. Please try again."
            return False

        if newpassword:
            if newpassword != newpassword2:
                self.errormessage = "New password didn't match."
                return False
            else:
                newpassword = encryptor.encrypt(newpassword)
                person.password = newpassword

        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        teamdescription = self.request.get("teamdescription", "")

        wiki = self.request.get("wiki", "")
        wikiname = self.request.get("wikiname", "")
        network = self.request.get("network", "")
        nickname = self.request.get("nickname", "")
        jabberid = self.request.get("jabberid", "")
        archuserid = self.request.get("archuserid", "")
        #gpgid = self.request.get("gpgid", "")

        person.displayname = displayname
        person.givenname = givenname
        person.familyname = familyname
        person.teamdescription = teamdescription

        #WikiName
        if self.context.wiki:
            self.context.wiki.wiki = wiki
            self.context.wiki.wikiname = wikiname
        else:
            if wiki or wikiname:
                self.context.wiki = WikiName(personID=person.id, wiki=wiki,
                                             wikiname=wikiname)
            else:
                self.context.wiki = None

        #IrcID
        if self.context.irc:
            self.context.irc.network = network
            self.context.irc.nickname = nickname
        else:
            if network or nickname:
                self.context.irc = IrcID(personID=person.id, network=network,
                                         nickname=nickname)
            else:
                self.context.irc = None

        #JabberID
        if self.context.jabber:
            self.context.jabber.jabberid = jabberid
        else:
            if jabberid:
                self.context.jabber = JabberID(personID=person.id,
                                               jabberid=jabberid)
            else:
                self.context.jabber = None

        #ArchUserID
        if self.context.archuser:
            self.context.archuser.archuserid = archuserid
        else:
            if archuserid:
                self.context.archuser = ArchUserID(personID=person.id, archuserid=archuserid)
            else:
                self.context.archuser = None
##TODO: (gpg+portlet) cprov 20041003
## GPG key handling requires a specific Portlet to handle key imports and
##  validation
#             #GPGKey
#             if self.context.gpg:
#                 self.context.gpg.keyid = gpgid
#                 self.context.gpg.fingerprint = fingerprint
#                 self.enable_edited = True
#             else:
#                 if gpgid:
#                     pubkey = 'sample%d'%self.context.id
#                     person = self.context.person.id
#                     self.context.gpg = GPGKey(personID=person,
#                                               keyid=gpgid,
#                                               fingerprint=fingerprint,
#                                               pubkey=pubkey,
#                                               revoked=False)
#                 else:
#                     self.context.gpg = None

        return True


class EmailAddressEditView(PersonView):

    def email_action(self):
        if self.request.get("REQUEST_METHOD") != "POST":
            # Nothing to do
            return False

        email = self.request.get("email", "")
        new_email = self.request.get("new_email", "")
        operation = self.request.get("operation", "")
        # XXX: We must create a framework to validate a new email address.
        # Until we create it, let's set the new email status as VALIDATED.
        valid = int(dbschema.EmailAddressStatus.VALIDATED)
        person = self.context.id

        if operation == 'add' and new_email:
            res = EmailAddress(email=new_email,
                               personID=person,
                               status=valid)
            return res

        elif operation == 'replace' and new_email:
            results = EmailAddress.selectBy(email=email)
            assert results.count() == 1
            emailaddress = results[0]
            emailaddress.email = new_email
            return emailaddress

        elif operation == 'delete':
            results = EmailAddress.selectBy(email=email)
            assert results.count() == 1
            emailaddress = results[0]
            emailaddress.destroySelf()
            return True


class GPGKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        request = self.request
        if request is not None:
            request.response.setHeader('Content-Type', 'text/plain')

        return self.context.gpg.pubkey


class SSHKeyView(PersonView):
    def form_action(self):
        if self.request.get("REQUEST_METHOD") != "POST":
            # Nothing to do
            return ''

        if not self.permission:
            return ''

        action = self.request.get('action', '')
        if action == 'add':
            return self.add_action()
        elif action == 'remove':
            return self.remove_action()

    def add_action(self):
        sshkey = self.request.get('sshkey', '')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            return 'Invalid public key'
        
        if kind == 'ssh-rsa':
            keytype = int(dbschema.SSHKeyType.RSA)
        elif kind == 'ssh-dss':
            keytype = int(dbschema.SSHKeyType.DSA)
        else:
            return 'Invalid public key'
        
        SSHKey(personID=self.person.id, keytype=keytype, keytext=keytext,
               comment=comment)
        return 'SSH public key added.'

    def remove_action(self):
        try:
            id = self.request.get('key', '')
        except ValueError:
            return "Can't remove key that doesn't exist"

        try:
            sshkey = SSHKey.get(id)
        except SQLObjectNotFound:
            return "Can't remove key that doesn't exist"

        if sshkey.person != self.person:
            return "Cannot remove someone else's key"

        comment = sshkey.comment
        sshkey.destroySelf()
        return 'Key "%s" removed' % comment


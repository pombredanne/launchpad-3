# Copyright 2004 Canonical Ltd
# sqlobject/sqlos
from sqlobject import LIKE, AND
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
from canonical.launchpad.database import getPermission
from canonical.launchpad.database import Project
from canonical.launchpad.database import Person

# interface import
from canonical.launchpad.interfaces import IPerson

# zope imports
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('foaf')

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages 
BATCH_SIZE = 40


class FOAFApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    def update(self):
        # XXX: do something about this
        '''Handle request and setup this view the way the templates expect it
        '''
        from sqlobject import OR, LIKE, CONTAINSSTRING, AND
        if self.request.form.has_key('query'):
            # TODO: Make this case insensitive
            s = self.request.form['query']
            self.results = Project.select(OR(
                    CONTAINSSTRING(Project.q.name, s),
                    CONTAINSSTRING(Project.q.displayname, s),
                    CONTAINSSTRING(Project.q.title, s),
                    CONTAINSSTRING(Project.q.shortdesc, s),
                    CONTAINSSTRING(Project.q.description, s)
                ))
            self.noresults = not self.results
        else:
            self.noresults = False
            self.results = []

class PeopleListView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def viewPeopleBatchNavigator(self):
        people = list(Person.select(orderBy='displayname'))
        start = int(self.request.get('batch_start', 0))
        end = int(self.request.get('batch_end', BATCH_SIZE))
        batch_size = BATCH_SIZE
        batch = Batch(list = people, start = start,
                      size = batch_size)
        return BatchNavigator(batch = batch,
                              request = self.request)    

class PeopleSearchView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []


    def searchPeopleBatchNavigator(self):
        name = self.request.get("name", "")

        if name:
            people = list(self._findPeopleByName(name))
            start = int(self.request.get('batch_start', 0))
            end = int(self.request.get('batch_end', BATCH_SIZE))
            batch_size = BATCH_SIZE
            batch = Batch(list = people, start = start,
                          size = batch_size)
            return BatchNavigator(batch = batch,
                                  request = self.request)
        else:
            return None

    def _findPeopleByName(self, name):
        name = name.replace('%', '%%')
        name = quote('%%'+ name.upper() + '%%')
        query = '''displayname ILIKE %s OR 
                   teamdescription ILIKE %s''' % (name, name)
        return Person.select(query, orderBy='displayname')


class PeopleAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.error_msg = None


    def add_action(self):
        displayname = self.request.get("displayname", "")
        givenname = self.request.get("givenname", "")
        familyname = self.request.get("familyname", "")
        email = self.request.get("email", "")
        password = self.request.get("password", "")
        retype = self.request.get("retype", "")

        if displayname:
            if password != retype:
                self.error_msg = 'Password does not match'
                return False

            self.results = createPerson(displayname, givenname, familyname,
                                        password, email)

            if not self.results:
                # it happens when generate_nick returns
                # a nick that already exists
                self.error_msg = 'Unhandled error creating person'
                return False

            return True

        return False
        
class TeamAddView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []
        self.error_msg = None

        self.person = IPerson(self.request.principal, None)
        self.permission = getPermission(self.person, self.context)        

    def add_action(self):
        enable_added = False

        if not self.permission:
            return False
    
        displayname = self.request.get("displayname", "")
        teamdescription = self.request.get("teamdescription", "")
        email = self.request.get("email", "")
        password = self.request.get("password", "")
        retype = self.request.get("retype", "")

        ##XXX: (uniques) cprov 20041003        
        if displayname and self.person:
            if password != retype:
                self.error_msg = 'Password does not match'
                return enable_added

            teamowner = self.person.id
            
            self.results = createTeam(displayname,
                                      teamowner,
                                      teamdescription,
                                      password,
                                      email)
            
            if not self.results:
                # it happens when generate_nick returns
                # a nick that already exists
                self.error_msg = 'Unhandled error creating person'
                return enable_added

            enable_added = True

        return enable_added
            

class TeamJoinView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)

            
    def join_action(self):
        ## XXX: (proposed+member) cprov 20041003
        ##  Join always as PROPOSED MEMBER 
        role = dbschema.MembershipRole.MEMBER.value
        status = dbschema.MembershipStatus.PROPOSED.value

        if self.person:
            ##XXX: (uniques) cprov 20041003
            Membership(personID=self.person.id,
                       teamID=self.context.id,
                       role=role,
                       status=status)
            
            ##XXX: (teamparticipation) cprov 20041003
            ## How to do it recursively as it is suposed to be,
            ## I mean flatten participation ...            
            TeamParticipation(personID=self.person.id,
                              teamID=self.context.id)
            return True
        
        return False

class TeamUnjoinView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)
            
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
        
                    
class PersonView(object):
    ## XXX:  cprov 20041101
    ## Use the already done malone portlet !!!!
    bugsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-bugs.pt')

    teamsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-teams.pt')

    subteamsPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-subteams.pt')

    membershipPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-membership.pt')


    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)
        self.permission = getPermission(self.person, self.context)
        
    def is_member(self):

        if self.person and self.context.person.teamowner:

            membership = Membership.selectBy(personID=self.person.id,
                                             teamID=self.context.id)
            if membership.count() > 0:
                return True
        
        return False

class PersonPackagesView(object):
    packagesPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-packages.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request

        self.person = IPerson(self.request.principal, None)
        self.permission = getPermission(self.person, self.context)


class PersonEditView(object):
    emailPortlet = ViewPageTemplateFile(
        '../launchpad/templates/portlet-person-email.pt')

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

        user = IPerson(self.request.principal, None)
        self.permission = getPermission(user, self.context)
            
    def email_action(self):

        if not self.permission:
            return False

        email = self.request.get("email", "")
        new_email = self.request.get("new_email", "")
        operation = self.request.get("operation", "")
        valid = int(dbschema.EmailAddressStatus.VALIDATED)
        person = self.context.person.id

        if operation == 'add' and new_email:

            res = EmailAddress(email=new_email,
                               personID=person,
                               status=valid)                              
            return res

        elif operation == 'edit' and new_email:

            result = EmailAddress.selectBy(email=email)[0]
            result.email = new_email 
            return result

        elif operation == 'delete':
            result = EmailAddress.selectBy(email=email)[0]
            result.destroySelf()
            return True
        else:
            return False
        


    def edit_action(self):
        enable_edited = False
        if not self.permission:
            return False

        displayname = self.request.get("displayname", "")
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
        
        ##XXX: (uniques) cprov 20041003
        if displayname :
            self.context.person.displayname = displayname
            self.context.person.givenname = givenname
            self.context.person.familyname = familyname
            self.context.person.teamdescription = teamdescription
            enable_edited = True            

            #WikiName
            if self.context.wiki:
                self.context.wiki.wiki = wiki
                self.context.wiki.wikiname = wikiname
                enable_edited = True
            else:
                if wiki or wikiname:
                    person = self.context.person.id
                    self.context.wiki = WikiName(personID=person,
                                                 wiki=wiki,
                                                 wikiname=wikiname)
                    enable_edited = True
                else:
                    self.context.wiki = None

            #IrcID
            if self.context.irc:
                self.context.irc.network = network
                self.context.irc.nickname = nickname
                enable_edited = True
            else:
                if network or nickname:
                    person = self.context.person.id
                    self.context.irc = IrcID(personID=person,
                                             network=network,
                                             nickname=nickname)
                    enable_edited = True
                else:
                    self.context.irc = None
                    
            #JabberID    
            if self.context.jabber:
                self.context.jabber.jabberid = jabberid
                enable_edited = True
            else:
                if jabberid:
                    person = self.context.person.id                    
                    self.context.jabber = JabberID(personID=person,
                                                   jabberid=jabberid)
                    enable_edited = True
                else:
                    self.context.jabber = None
                    
            #ArchUserID
            if self.context.archuser:
                self.context.archuser.archuserid = archuserid
                enable_edited = True
            else:
                if archuserid:
                    person = self.context.person.id                    
                    self.context.archuser = ArchUserID(personID=person,
                                                       archuserid=archuserid)
                    enable_edited = True
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

        return enable_edited


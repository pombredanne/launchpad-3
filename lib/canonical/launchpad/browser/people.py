# Copyright 2004 Canonical Ltd

# sqlobject/sqlos
from sqlobject import LIKE, AND, SQLObjectNotFound
from canonical.database.sqlbase import quote

# lp imports
from canonical.lp.dbschema import EmailAddressStatus, SSHKeyType
from canonical.lp.dbschema import LoginTokenType, MembershipRole
from canonical.lp.dbschema import MembershipStatus
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.auth.browser import well_formed_email

# database imports
from canonical.launchpad.database import WikiName
from canonical.launchpad.database import JabberID
from canonical.launchpad.database import TeamParticipation, Membership
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID
from canonical.launchpad.database import createTeam
from canonical.launchpad.database import Person
from canonical.launchpad.database import SSHKey

# interface import
from canonical.launchpad.interfaces import IPerson, IPersonSet
from canonical.launchpad.interfaces import ILaunchBag, ILoginTokenSet
from canonical.launchpad.interfaces import IPasswordEncryptor

from canonical.launchpad.mail.sendmail import simple_sendmail

# zope imports
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility

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
        name = self.request.get("name")
        searchfor = self.request.get("searchfor")

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


class TeamAddView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        AddView.__init__(self, context, request)
        self._nextURL = '.'

    def nextURL(self):
        return self._nextURL

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        person = IPerson(self.request.principal, None)
        team = createTeam(kw['displayname'], person.id,
                          kw['teamdescription'], kw['email'])
        notify(ObjectCreatedEvent(team))
        self._nextURL = '/foaf/people/%s' % team.name
        return team


class PersonView(object):
    """A simple View class to be used in Person's pages where we don't have
    actions and all we need is the context/request."""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def membershipOrRoles(self):
        # XXX: salgado, 2005-01-13: I'll find a better way to display
        # memberships and distro/distrorelease roles on a Person's page,
        # and then we're not going to need this method anymore.
        person = self.context
        return person.teams or person.distroroles or person.distroreleaseroles

    def sshkeysCount(self):
        return len(self.context.sshkeys)


class TeamView(object):
    """A simple View class to be used in Team's pages where we don't have
    actions and all we need is the context/request."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class PersonEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.user = getUtility(ILaunchBag).user

    def edit_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return False

        person = self.context
        request = self.request

        password = request.form.get("password")
        newpassword = request.form.get("newpassword")
        newpassword2 = request.form.get("newpassword2")
        displayname = request.form.get("displayname")

        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, person.password):
            self.errormessage = "Wrong password. Please try again."
            return False

        if not displayname:
            self.errormessage = "Your display name cannot be emtpy."
            return False

        if newpassword:
            if newpassword != newpassword2:
                self.errormessage = "New password didn't match."
                return False
            else:
                newpassword = encryptor.encrypt(newpassword)
                person.password = newpassword

        person.displayname = displayname
        person.givenname = request.form.get("givenname")
        person.familyname = request.form.get("familyname")

        wiki = request.form.get("wiki")
        wikiname = request.form.get("wikiname")
        network = request.form.get("network")
        nickname = request.form.get("nickname")
        jabberid = request.form.get("jabberid")
        archuserid = request.form.get("archuserid")

        #WikiName
        if person.wiki:
            person.wiki.wiki = wiki
            person.wiki.wikiname = wikiname
        elif wiki and wikiname:
            WikiName(personID=person.id, wiki=wiki, wikiname=wikiname)

        #IrcID
        if person.irc:
            person.irc.network = network
            person.irc.nickname = nickname
        elif network and nickname:
            IrcID(personID=person.id, network=network, nickname=nickname)

        #JabberID
        if person.jabber:
            person.jabber.jabberid = jabberid
        elif jabberid:
            JabberID(personID=person.id, jabberid=jabberid)

        #ArchUserID
        if person.archuser:
            person.archuser.archuserid = archuserid
        elif archuserid:
            ArchUserID(personID=person.id, archuserid=archuserid)

        return True


class EmailAddressEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = "Your changes have been saved."
        self.user = getUtility(ILaunchBag).user

    def formSubmitted(self):
        if "SUBMIT_CHANGES" in self.request.form:
            self.processEmailChanges()
            return True
        elif "VALIDATE_EMAIL" in self.request.form:
            self.processValidationRequest()
            return True
        else:
            return False

    def processEmailChanges(self):
        user = self.user
        password = self.request.form.get("password")
        encryptor = getUtility(IPasswordEncryptor)
        if not encryptor.validate(password, user.password):
            self.message = "Wrong password. Please try again."
            return

        newemail = self.request.form.get("newemail", "").strip()
        if newemail:
            if not well_formed_email(newemail):
                self.message = "'%s' is not a valid email address." % newemail
                return

            results = EmailAddress.selectBy(email=newemail)
            if results.count() > 0:
                email = results[0]
                self.message = ("The email address '%s' was already "
                                "registered by user '%s'. If you think this "
                                "is your email address, you can hijack it by "
                                "clicking here.") % \
                               (email.email, email.person.browsername())
                return

            login = getUtility(ILaunchBag).login
            logintokenset = getUtility(ILoginTokenSet)
            token = logintokenset.new(user, login, newemail, 
                                      LoginTokenType.VALIDATEEMAIL)
            sendEmailValidationRequest(token, self.request.getApplicationURL())
            self.message = ("A new message was sent to '%s', please follow "
                            "the instructions on that message to validate "
                            "your email address.") % newemail

        # XXX: salgado 2005-01-12: If we change the preferred email address,
        # the view is displaying the old preferred one, even that the change
        # is stored in the DB, as one can see by Reloading/Opening the page
        # again.
        id = self.request.form.get("PREFERRED_EMAIL")
        if id is not None:
            # XXX: salgado 2005-01-06: Ideally, any person that is able to
            # login *must* have a PREFERRED email, and this will not be
            # needed anymore. But for now we need this cause id may be "".
            id = int(id)
            if getattr(user.preferredemail, 'id', None) != id:
                email = EmailAddress.get(id)
                assert email.person == user
                assert email.status == int(EmailAddressStatus.VALIDATED)
                user.preferredemail = email

        ids = self.request.form.get("REMOVE_EMAIL")
        if ids is not None:
            # We can have multiple email adressess marked for deletion, and in
            # this case ids will be a list. Otherwise ids will be str or int
            # and we need to make a list with that value to use in the for 
            # loop.
            if not isinstance(ids, list):
                ids = [ids]

            for id in ids:
                email = EmailAddress.get(id)
                assert email.person == user
                if user.preferredemail != email:
                    email.destroySelf()

    def processValidationRequest(self):
        id = self.request.form.get("NOT_VALIDATED_EMAIL")
        email = EmailAddress.get(id)
        self.message = ("A new email was sent to '%s' with instructions "
                        "on how to validate it.") % email.email
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(self.user, login, email.email,
                                  LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token, self.request.getApplicationURL())


def sendEmailValidationRequest(token, appurl):
    template = open('lib/canonical/launchpad/templates/validate-email.txt').read()
    fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"

    replacements = {'longstring': token.token,
                    'requester': token.requester.browsername(),
                    'requesteremail': token.requesteremail,
                    'toaddress': token.email,
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Validate your email address"
    simple_sendmail(fromaddress, token.email, subject, message)


class GPGKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return self.context.gpg.pubkey


class SSHKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "\n".join([key.keytext for key in self.context.sshkeys])


class SSHKeyEditView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def form_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return ''

        action = self.request.form.get('action')
        if action == 'add':
            return self.add_action()
        elif action == 'remove':
            return self.remove_action()

    def add_action(self):
        sshkey = self.request.form.get('sshkey')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            return 'Invalid public key'
        
        if kind == 'ssh-rsa':
            keytype = int(SSHKeyType.RSA)
        elif kind == 'ssh-dss':
            keytype = int(SSHKeyType.DSA)
        else:
            return 'Invalid public key'
        
        SSHKey(personID=self.user.id, keytype=keytype, keytext=keytext,
               comment=comment)
        return 'SSH public key added.'

    def remove_action(self):
        try:
            id = self.request.form.get('key')
        except ValueError:
            return "Can't remove key that doesn't exist"

        try:
            sshkey = SSHKey.get(id)
        except SQLObjectNotFound:
            return "Can't remove key that doesn't exist"

        if sshkey.person != self.user:
            return "Cannot remove someone else's key"

        comment = sshkey.comment
        sshkey.destroySelf()
        return 'Key "%s" removed' % comment


class TeamMembersEditView:

    # XXX: salgado, 2005-01-12: Not yet ready for review. I'm working on
    # this.
    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self._actionMethods = {'authorize': self.authorizeProposed,
                               'notauthorize': self.removeMember,
                               'revokeadmin': self.revokeAdminiRole,
                               'removeadmin': self.removeMember,
                               'giveadmin': self.giveAdminRole,
                               'removemember': self.removeMember}


    def formSubmitted(self):
        if self.request.method != "POST":
            return False

        if "PROPOSED_MEMBERS_CHANGES" in self.request.form or \
           "ADMIN_CHANGES" in self.request.form or \
           "MEMBERS_CHANGES" in self.request.form:
            self.processChanges()
            return True
        else:
            return False

    def processChanges(self):
        action = self.request.form.get('action')
        people = self.request.form.get('selected')

        if not people:
            return 

        if not isinstance(people, list):
            people = [people]

        method = self._actionMethods[action]
        for personID in people:
            method(int(personID), self.context)

    def _getMembership(self, personID, teamID):
        membership = Membership.selectBy(personID=personID, teamID=teamID)
        assert membership.count() == 1
        return membership[0]

    def authorizeProposed(self, personID, team):
        membership = self._getMembership(personID, team.id)
        membership.status = int(MembershipStatus.CURRENT)
        membership.role = int(MembershipRole.MEMBER)

    def removeMember(self, personID, team):
        if personID == team.teamowner.id:
            return

        membership = self._getMembership(personID, team.id)
        membership.destroySelf()
        teampart = TeamParticipation.selectBy(personID=personID,
                                              teamID=team.id)
        assert teampart.count() == 1
        teampart[0].destroySelf()

    def giveAdminRole(self, personID, team):
        membership = self._getMembership(personID, team.id)
        membership.role = int(MembershipRole.ADMIN)

    def revokeAdminiRole(self, personID, team):
        membership = self._getMembership(personID, team.id)
        membership.role = int(MembershipRole.MEMBER)


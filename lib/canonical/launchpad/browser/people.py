# Copyright 2004 Canonical Ltd

# sqlobject/sqlos
from sqlobject import SQLObjectNotFound
from canonical.database.sqlbase import quote, flushUpdates

# lp imports
from canonical.lp.dbschema import EmailAddressStatus, SSHKeyType
from canonical.lp.dbschema import LoginTokenType
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.auth.browser import well_formed_email
from canonical.foaf.nickname import generate_nick

# database imports
from canonical.launchpad.database import WikiName
from canonical.launchpad.database import JabberID
from canonical.launchpad.database import EmailAddress, IrcID
from canonical.launchpad.database import GPGKey, ArchUserID
from canonical.launchpad.database import Person
from canonical.launchpad.database import SSHKey

# interface import
from canonical.launchpad.interfaces import IPerson, IPersonSet, IEmailAddressSet
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

    def getUbuntitesList(self):
        putil = getUtility(IPersonSet)
        results = putil.getUbuntites()
        return self._getBatchNavigator(list(results))

class PeopleListView(BaseListView):

    header = "People List"

    def getList(self):
        return self.getPeopleList()


class TeamListView(BaseListView):

    header = "Team List"

    def getList(self):
        return self.getTeamsList()

class UbuntiteListView(BaseListView):

    header = "Ubuntite List"

    def getList(self):
        return self.getUbuntitesList()


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


class RequestPeopleMergeView(AddView):
    """The view for the page where the user asks a merge of two accounts.

    If the dupe account have only one email address we send a message to that
    address and then redirect the user to other page saying that everything
    went fine. Otherwise we redirect the user to another page where we list
    all email addresses owned by the dupe account and the user selects which
    of those (s)he wants to claim.
    """

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

        user = getUtility(ILaunchBag).user
        dupeaccount = kw['dupeaccount']
        if dupeaccount == user:
            # Please, don't try to merge you into yourself.
            return

        emails = EmailAddress.selectBy(personID=dupeaccount.id)
        if emails.count() > 1:
            # The dupe account have more than one email address. Must redirect
            # the user to another page to ask which of those emails (s)he
            # wants to claim.
            self._nextURL = '+requestmerge-multiple?dupe=%d' % dupeaccount.id
            return

        assert emails.count() == 1
        email = emails[0]
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(user, login, email.email, 
                                  LoginTokenType.ACCOUNTMERGE)
        dupename = dupeaccount.name
        sendMergeRequestEmail(token, dupename, self.request.getApplicationURL())
        self._nextURL = './+mergerequest-sent'


class FinishedPeopleMergeRequestView(object):
    """A simple view for a page where we only tell the user that we sent the
    email with further instructions to complete the merge."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class RequestPeopleMergeMultipleEmailsView(object):
    """A view for the page where the user asks a merge and the dupe account
    have more than one email address."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.formProcessed = False

        dupe = self.request.form.get('dupe')
        if dupe is None:
            # We just got redirected to this page and we don't have the dupe
            # hidden field in request.form.
            dupe = self.request.get('dupe')
        self.dupe = getUtility(IPersonSet).get(int(dupe))
        emailaddrset = getUtility(IEmailAddressSet)
        self.dupeemails = emailaddrset.getByPerson(self.dupe.id)

    def processForm(self):
        if self.request.method != "POST":
            return

        self.formProcessed = True
        user = getUtility(ILaunchBag).user
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)

        ids = self.request.form.get("selected")
        if ids is not None:
            # We can have multiple email adressess selected, and in this case 
            # ids will be a list. Otherwise ids will be str or int and we need
            # to make a list with that value to use in the for loop.
            if not isinstance(ids, list):
                ids = [ids]

            for id in ids:
                email = EmailAddress.get(id)
                assert email in self.dupeemails
                token = logintokenset.new(user, login, email.email, 
                                          LoginTokenType.ACCOUNTMERGE)
                dupename = self.dupe.name
                url = self.request.getApplicationURL()
                sendMergeRequestEmail(token, dupename, url)


def sendMergeRequestEmail(token, dupename, appurl):
    template = open('lib/canonical/launchpad/templates/request-merge.txt').read()
    fromaddress = "Launchpad Account Merge <noreply@ubuntu.com>"

    replacements = {'longstring': token.token,
                    'dupename': dupename,
                    'requester': token.requester.name,
                    'requesteremail': token.requesteremail,
                    'toaddress': token.email,
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Merge of Accounts Requested"
    simple_sendmail(fromaddress, token.email, subject, message)


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
                                "registered by user '%s'. If you think that "
                                "is a duplicated account, you can go to the "
                                "<a href=\"../+requestmerge\">Merge Accounts"
                                "</a> page to claim this email address and "
                                "everything that is owned by that account.") % \
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

        id = self.request.form.get("PREFERRED_EMAIL")
        if id is not None:
            # XXX: salgado 2005-01-06: Ideally, any person that is able to
            # login *must* have a PREFERRED email, and this will not be
            # needed anymore. But for now we need this cause id may be "".
            id = int(id)
            if getattr(user.preferredemail, 'id', None) != id:
                email = EmailAddress.get(id)
                assert email.person == user
                assert email.status == EmailAddressStatus.VALIDATED
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
                    # The following lines are a *real* hack to make sure we
                    # don't let the user with no validated email address.
                    # Ideally, we wouldn't need this because all users would
                    # have a preferred email address.
                    if user.preferredemail is None and \
                       len(user.validatedemails) > 1:
                        # No preferred email set. We can only delete this
                        # email if it's not the last validated one.
                        email.destroySelf()
                    elif user.preferredemail is not None:
                        # This user have a preferred email and it's not this
                        # one, so we can delete it.
                        email.destroySelf()

        flushUpdates()

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


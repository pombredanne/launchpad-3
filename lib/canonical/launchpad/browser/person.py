# Copyright 2004 Canonical Ltd

__metaclass__ = type

import cgi
import sets

# sqlobject/sqlos
from canonical.database.sqlbase import flush_database_updates

# zope imports
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.app.form.browser.add import AddView
from zope.component import getUtility

# lp imports
from canonical.lp.dbschema import LoginTokenType, SSHKeyType
from canonical.lp.dbschema import EmailAddressStatus, GPGKeyAlgorithms
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

# interface import
from canonical.launchpad.interfaces import ISSHKeySet, IBugTaskSet
from canonical.launchpad.interfaces import IPersonSet, IEmailAddressSet
from canonical.launchpad.interfaces import IWikiNameSet, IJabberIDSet
from canonical.launchpad.interfaces import IIrcIDSet, IArchUserIDSet
from canonical.launchpad.interfaces import ILaunchBag, ILoginTokenSet
from canonical.launchpad.interfaces import IPasswordEncryptor, \
                                           ISignedCodeOfConduct,\
                                           ISignedCodeOfConductSet
from canonical.launchpad.interfaces import IGPGKeySet, IGpgHandler

from canonical.launchpad.helpers import well_formed_email, obfuscateEmail
from canonical.launchpad.helpers import convertToHtmlCode, shortlist
from canonical.launchpad.mail.sendmail import simple_sendmail

##XXX: (batch_size+global) cprov 20041003
## really crap constant definition for BatchPages
BATCH_SIZE = 40


class BaseListView:

    header = ""

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def _getBatchNavigator(self, list):
        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=list, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def getTeamsList(self):
        results = getUtility(IPersonSet).getAllTeams()
        return self._getBatchNavigator(results)

    def getPeopleList(self):
        results = getUtility(IPersonSet).getAllPersons()
        return self._getBatchNavigator(results)

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


class FOAFSearchView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.results = []

    def teamsCount(self):
        return getUtility(IPersonSet).teamsCount()

    def peopleCount(self):
        return getUtility(IPersonSet).peopleCount()

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

        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=results, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)

    def _findPeopleByName(self, name, peopleonly=False, teamsonly=False):
        # This method is somewhat weird, cause peopleonly and teamsonly
        # are mutually exclusive.
        if peopleonly:
            return getUtility(IPersonSet).findPersonByName(name)
        elif teamsonly:
            return getUtility(IPersonSet).findTeamByName(name)

        return getUtility(IPersonSet).findByName(name)


class PersonRdfView(object):
    """A view that sets its mime-type to application/rdf+xml"""
    def __init__(self, context, request):
        self.context = context
        self.request = request
        request.response.setHeader('content-type', 'application/rdf+xml')


class BasePersonView:
    """A base class to be used by all IPerson view classes."""

    viewsPortlet = ViewPageTemplateFile(
        '../templates/portlet-person-views.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-person-actions.pt')
    

class PersonView(BasePersonView):
    """A simple View class to be used in all Person's pages."""

    # restricted set of methods to be proxied by form_action()
    permitted_actions = ['import_gpg', 'claim_gpg', 'remove_gpg',
                         'add_ssh', 'remove_ssh']

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = None
        self.user = getUtility(ILaunchBag).user

    def assignedBugsToShow(self):
        """Return True if there's any bug assigned to this person that match
        the criteria of mostImportantBugTasks() or mostRecentBugTasks()."""
        return bool(self.mostImportantBugTasks() or self.mostRecentBugTasks())

    def mostRecentBugTasks(self):
        """Return up to 10 bug tasks (ordered by date assigned) that are 
        assigned to this person.

        These bug tasks are either the ones reported on packages/products this
        person is the maintainer or the ones assigned directly to him.
        """
        bts = getUtility(IBugTaskSet)
        orderBy = ('-dateassigned', '-priority', '-severity')
        results = bts.assignedBugTasks(
                        self.context, orderBy=orderBy, user=self.user)
        return results[:10]

    def mostImportantBugTasks(self):
        """Return up to 10 bug tasks (ordered by priority and severity) that
        are assigned to this person.

        These bug tasks are either the ones reported on packages/products this
        person is the maintainer or the ones assigned directly to him.
        """
        bts = getUtility(IBugTaskSet)
        orderBy = ('-priority', '-severity', '-dateassigned')
        results = bts.assignedBugTasks(
                        self.context, orderBy=orderBy, user=self.user)
        return results[:10]

    def bugTasksWithSharedInterest(self):
        """Return up to 10 bug tasks (ordered by date assigned) which this
        person and the logged in user share some interest.

        We assume they share some interest if they're both members of the
        maintainer or if one is the maintainer and the task is directly
        assigned to the other.
        """
        assert self.user is not None, (
                'This method should not be called without a logged in user')
        if self.context.id == self.user.id:
            return []

        bts = getUtility(IBugTaskSet)
        orderBy = ('-dateassigned', '-priority', '-severity')
        results = bts.bugTasksWithSharedInterest(
                self.context, self.user, orderBy=orderBy)
        return results[:10]

    def obfuscatedEmail(self):
        if self.context.preferredemail is not None:
            return obfuscateEmail(self.context.preferredemail.email)
        else:
            return None

    def htmlEmail(self):
        if self.context.preferredemail is not None:
            return convertToHtmlCode(self.context.preferredemail.email)
        else:
            return None

    def showSSHKeys(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "\n".join(["%s %s %s" % (key.keykind, key.keytext, key.comment)
                          for key in self.context.sshkeys])
    
    def sshkeysCount(self):
        return len(self.context.sshkeys)

    def showGPGKeys(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return "\n".join([key.pubkey for key in self.context.gpgkeys])

    def gpgkeysCount(self):
        return len(self.context.gpgkeys)

    def signatures(self):
        """Return a list of code-of-conduct signatures on record for this
        person."""
        # use utility to query on SignedCoCs
        sCoC_util = getUtility(ISignedCodeOfConductSet)
        return sCoC_util.searchByUser(self.context.id)

    def performCoCChanges(self):
        """Make changes to code-of-conduct signature records for this
        person."""
        sign_ids = self.request.form.get("DEACTIVE_SIGN")

        self.message = 'Deactivating: '

        if sign_ids is not None:
            sCoC_util = getUtility(ISignedCodeOfConductSet)

            # verify if we have multiple entries to deactive
            if not isinstance(sign_ids, list):
                sign_ids = [sign_ids]

            for sign_id in sign_ids:
                sign_id = int(sign_id)
                self.message += '%d,' % sign_id
                # Deactivating signature
                comment = 'Deactivated by Owner'
                sCoC_util.modifySignature(sign_id, self.user, comment, False)

            return True

    def form_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return ''
        action = self.request.form.get('action')

        # primary check on restrict set of 'form-like' methods.
        if action and (action not in self.permitted_actions):
            return 'Forbidden Form Method'
        
        # do not mask anything 
        return getattr(self, action)()       

    # XXX cprov 20050401
    # As "Claim GPG key" takes a lot of time, we should process it
    # throught the NotificationEngine.
    def claim_gpg(self):
        fingerprint = self.request.form.get('fingerprint')

        #XXX cprov 20050401
        # Add fingerprint checks before claim.
        
        return 'DEMO: GPG key "%s" claimed.' % fingerprint

    def import_gpg(self):
        pubkey = self.request.form.get('pubkey')

        gpghandler = getUtility(IGpgHandler)

        fingerprint = gpghandler.importPubKey(pubkey)        

        if fingerprint == None:
            return 'DEMO: GPG pubkey not recognized'

        keysize, algorithm, revoked = gpghandler.getKeyInfo(fingerprint)
        
        # XXX cprov 20050407
        # Keyid is totally obsolete        
        keyid = fingerprint[-8:]
        # EnumCol doesn't help in this case, at least
        algorithm_value = GPGKeyAlgorithms.items[algorithm]

        # See IGPGKeySet for further information
        getUtility(IGPGKeySet).new(self.user.id, keyid, pubkey, fingerprint,
                                   keysize, algorithm_value, revoked)
        
        return 'DEMO: %s imported' % fingerprint

    # XXX cprov 20050401
    # is it possible to remove permanently a key from our keyring
    # The best bet should be DEACTIVE it.
    def remove_gpg(self):
        keyid = self.request.form.get('keyid')
        # retrieve key info
        gpgkey = getUtility(IGPGKeySet).get(keyid)
        
        comment = 'DEMO: GPG key removed ("%s")' % gpgkey.fingerprint

        #gpgkey.destroySelf()

        return comment

    def add_ssh(self):
        sshkey = self.request.form.get('sshkey')
        try:
            kind, keytext, comment = sshkey.split(' ', 2)
        except ValueError:
            return 'Invalid public key'
        
        if kind == 'ssh-rsa':
            keytype = SSHKeyType.RSA
        elif kind == 'ssh-dss':
            keytype = SSHKeyType.DSA
        else:
            return 'Invalid public key'
        
        getUtility(ISSHKeySet).new(self.user.id, keytype, keytext, comment)
        return 'SSH public key added.'

    def remove_ssh(self):
        try:
            id = self.request.form.get('key')
        except ValueError:
            return "Can't remove key that doesn't exist"

        sshkey = getUtility(ISSHKeySet).get(id)
        if sshkey is None:
            return "Can't remove key that doesn't exist"

        if sshkey.person != self.user:
            return "Cannot remove someone else's key"

        comment = sshkey.comment
        sshkey.destroySelf()
        return 'Key "%s" removed' % comment


class PersonEditView(BasePersonView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.errormessage = None
        self.message = None
        self.badlyFormedEmail = None
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
            getUtility(IWikiNameSet).new(person.id, wiki, wikiname)

        #IrcID
        if person.irc:
            person.irc.network = network
            person.irc.nickname = nickname
        elif network and nickname:
            getUtility(IIrcIDSet).new(person.id, network, nickname)

        #JabberID
        if person.jabber:
            person.jabber.jabberid = jabberid
        elif jabberid:
            getUtility(IJabberIDSet).new(person.id, jabberid)

        #ArchUserID
        if person.archuser:
            person.archuser.archuserid = archuserid
        elif archuserid:
            getUtility(IArchUserIDSet).new(person.id, archuserid)

        return True

    def unvalidatedAndGuessedEmails(self):
        """Return a Set containing all unvalidated and guessed emails."""
        emailset = sets.Set()
        emailset = emailset.union([e.email for e in self.context.guessedemails])
        emailset = emailset.union([e for e in self.context.unvalidatedemails])
        return emailset

    def emailFormSubmitted(self):
        """Check if the user submitted the form and process it.

        Return True if the form was submitted or False if it was not.
        """
        form = self.request.form
        if "REMOVE_VALIDATED" in form:
            self._deleteValidatedEmail()
        elif "SET_PREFERRED" in form:
            self._setPreferred()
        elif "REMOVE_UNVALIDATED" in form:
            self._deleteUnvalidatedEmail()
        elif "VALIDATE" in form:
            self._validateEmail()
        elif "ADD_EMAIL" in form:
            self._addEmail()
        else:
            return False

        # Any self-posting page that updates the database and want to display
        # these updated values have to call flush_database_updates().
        flush_database_updates()
        return True

    def _validateEmail(self):
        """Send a validation url to the selected email address."""
        email = self.request.form.get("UNVALIDATED_SELECTED")
        if email is None:
            self.message = (
                "You must select the email address you want to confirm.")
            return

        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(self.context, login, email,
                                  LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token, self.request.getApplicationURL())
        self.message = ("A new email was sent to '%s' with instructions on "
                        "how to confirm that it belongs to you." % email)

    def _deleteUnvalidatedEmail(self):
        """Delete the selected email address, which is not validated.
        
        This email address can be either on the EmailAddress table marked with
        status new, or in the LoginToken table.
        """
        email = self.request.form.get("UNVALIDATED_SELECTED")
        if email is None:
            self.message = (
                "You must select the email address you want to remove.")
            return
        
        emailset = getUtility(IEmailAddressSet)
        logintokenset = getUtility(ILoginTokenSet)
        if email in [e.email for e in self.context.guessedemails]:
            emailaddress = emailset.getByEmail(email)
            # These asserts will fail only if someone tries to poison the form.
            assert emailaddress.person.id == self.context.id
            assert self.context.preferredemail.id != emailaddress.id
            emailaddress.destroySelf()

        if email in self.context.unvalidatedemails:
            logintokenset.deleteByEmailAndRequester(email, self.context)

        self.message = "The email address '%s' has been removed." % email

    def _deleteValidatedEmail(self):
        """Delete the selected email address, which is already validated."""
        email = self.request.form.get("VALIDATED_SELECTED")
        if email is None:
            self.message = (
                "You must select the email address you want to remove.")
            return

        emailset = getUtility(IEmailAddressSet)
        emailaddress = emailset.getByEmail(email)
        # These asserts will fail only if someone poisons the form.
        assert emailaddress.person.id == self.context.id
        assert self.context.preferredemail.id != emailaddress.id
        emailaddress.destroySelf()
        self.message = "The email address '%s' has been removed." % email

    def _addEmail(self):
        """Register a new email for the person in context.

        Check if the email is "well formed" and if it's not yet in our
        database and then register it to the person in context.
        """
        person = self.context
        emailset = getUtility(IEmailAddressSet)
        logintokenset = getUtility(ILoginTokenSet)
        newemail = self.request.form.get("newemail", "").strip().lower()
        if not well_formed_email(newemail):
            self.message = (
                "'%s' doesn't seem to be a valid email address." % newemail)
            self.badlyFormedEmail = newemail
            return

        email = emailset.getByEmail(newemail)
        if email is not None and email.person.id == person.id:
            self.message = (
                    "The email address '%s' is already registered as your "
                    "email address. This can be either because you already "
                    "added this email address before or because it have "
                    "been detected by our system as being yours. In case "
                    "it was detected by our systeam, it's probably shown "
                    "on this page and is waiting to be confirmed as being "
                    "yours." % email.email)
            return
        elif email is not None:
            # self.message is rendered using 'structure' on the page template,
            # so it's better escape browsername because people can put 
            # whatever they want in their name/displayname. On the other hand,
            # we don't need to escape email addresses because they are always
            # validated (which means they can't have html tags) before being
            # inserted in the database.
            browsername = cgi.escape(email.person.browsername)
            self.message = (
                    "The email address '%s' was already registered by user "
                    "'%s'. If you think that is a duplicated account, you "
                    "can go to the <a href=\"../+requestmerge\">Merge "
                    "Accounts</a> page to claim this email address and "
                    "everything that is owned by that account."
                    % (email.email, email.person.browsername))
            return

        login = getUtility(ILaunchBag).login
        token = logintokenset.new(person, login, newemail,
                                  LoginTokenType.VALIDATEEMAIL)
        sendEmailValidationRequest(token, self.request.getApplicationURL())
        self.message = (
                "A new message was sent to '%s', please follow the "
                "instructions on that message to confirm that this email "
                "address is yours." % newemail)

    def _setPreferred(self):
        """Set the selected email as preferred for the person in context."""
        email = self.request.form.get("VALIDATED_SELECTED")
        if email is None:
            self.message = (
                    "To set your contact address you have to choose an address "
                    "from the list of confirmed addresses and click on Set as "
                    "Contact Address.")
            return
        elif isinstance(email, list):
            self.message = (
                    "Only one email address can be set as your contact "
                    "address. Please select the one you want and click on "
                    "Set as Contact Address.")
            return

        emailset = getUtility(IEmailAddressSet)
        emailaddress = emailset.getByEmail(email)
        assert emailaddress.person.id == self.context.id
        assert emailaddress.status == EmailAddressStatus.VALIDATED
        self.context.preferredemail = emailaddress
        self.message = "Your contact address has been changed to: %s" % email


def sendEmailValidationRequest(token, appurl):
    template = open(
        'lib/canonical/launchpad/emailtemplates/validate-email.txt').read()
    fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"

    replacements = {'longstring': token.token,
                    'requester': token.requester.browsername,
                    'requesteremail': token.requesteremail,
                    'toaddress': token.email,
                    'appurl': appurl}
    message = template % replacements

    subject = "Launchpad: Validate your email address"
    simple_sendmail(fromaddress, token.email, subject, message)


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

        emails = getUtility(IEmailAddressSet).getByPerson(dupeaccount.id)
        if len(emails) > 1:
            # The dupe account have more than one email address. Must redirect
            # the user to another page to ask which of those emails (s)he
            # wants to claim.
            self._nextURL = '+requestmerge-multiple?dupe=%d' % dupeaccount.id
            return

        assert len(emails) == 1
        email = emails[0]
        login = getUtility(ILaunchBag).login
        logintokenset = getUtility(ILoginTokenSet)
        token = logintokenset.new(user, login, email.email, 
                                  LoginTokenType.ACCOUNTMERGE)
        dupename = dupeaccount.name
        sendMergeRequestEmail(token, dupename, self.request.getApplicationURL())
        self._nextURL = './+mergerequest-sent'


class FinishedPeopleMergeRequestView:
    """A simple view for a page where we only tell the user that we sent the
    email with further instructions to complete the merge."""

    def __init__(self, context, request):
        self.context = context
        self.request = request


class RequestPeopleMergeMultipleEmailsView:
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
        # XXX: salgado, 2005-05-06: As soon as we have a __contains__ method
        # in SelectResults we'll not need to listify self.dupeemails anymore.
        self.dupeemails = shortlist(emailaddrset.getByPerson(self.dupe.id))

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

            emailset = getUtility(IEmailAddressSet)
            for id in ids:
                email = emailset.get(id)
                assert email in self.dupeemails
                token = logintokenset.new(user, login, email.email, 
                                          LoginTokenType.ACCOUNTMERGE)
                dupename = self.dupe.name
                url = self.request.getApplicationURL()
                sendMergeRequestEmail(token, dupename, url)


def sendMergeRequestEmail(token, dupename, appurl):
    template = open(
        'lib/canonical/launchpad/emailtemplates/request-merge.txt').read()
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


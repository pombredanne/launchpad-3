# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'BaseListView',
    'PeopleListView',
    'TeamListView',
    'UbuntiteListView',
    'FOAFSearchView',
    'PersonRdfView',
    'PersonView',
    'TeamJoinView',
    'TeamLeaveView',
    'PersonEditView',
    'RequestPeopleMergeView',
    'FinishedPeopleMergeRequestView',
    'RequestPeopleMergeMultipleEmailsView',
    'ObjectReassignmentView',
    'TeamReassignmentView',
    ]

import cgi
import sets

from canonical.database.sqlbase import flush_database_updates

from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.app.form.utility import setUpWidgets
from zope.app.form.interfaces import (
        IInputWidget, ConversionError, WidgetInputError)
from zope.component import getUtility

from canonical.lp.dbschema import (
    LoginTokenType, SSHKeyType, EmailAddressStatus, TeamMembershipStatus,
    KarmaActionCategory, TeamSubscriptionPolicy)
from canonical.lp.z3batching import Batch
from canonical.lp.batching import BatchNavigator

from canonical.launchpad.interfaces import (
    ISSHKeySet, IBugTaskSet, IPersonSet, IEmailAddressSet, IWikiNameSet,
    IJabberIDSet, IIrcIDSet, IArchUserIDSet, ILaunchBag, ILoginTokenSet,
    IPasswordEncryptor, ISignedCodeOfConductSet, IGPGKeySet, IGPGHandler,
    IKarmaActionSet, IKarmaSet, UBUNTU_WIKI_URL, ITeamMembershipSet,
    IObjectReassignment, ITeamReassignment, IPollSubset, IPerson,
    ICalendarOwner)

from canonical.launchpad.helpers import (
        obfuscateEmail, convertToHtmlCode, sanitiseFingerprint)
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.mail.sendmail import simple_sendmail
from canonical.launchpad.event.team import JoinTeamRequestEvent
from canonical.launchpad.webapp import (
    StandardLaunchpadFacets, Link, DefaultLink)


class PersonFacets(StandardLaunchpadFacets):
    """The links that will appear in the facet menu for an IPerson.
    """

    usedfor = IPerson

    def overview(self):
        target = ''
        text = 'Overview'
        return DefaultLink(target, text)

    def bugs(self):
        target = '+bugsassigned'
        text = 'Bugs'
        return Link(target, text)

    def translations(self):
        target = '+translations'
        text = 'Translations'
        return Link(target, text)

    def calendar(self):
        target = '+calendar'
        text = 'Calendar'
        # only link to the calendar if it has been created
        linked = ICalendarOwner(self.context).calendar is not None
        return Link(target, text, linked=linked)


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
        results = getUtility(IPersonSet).getUbuntites()
        return self._getBatchNavigator(results)


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
            results = getUtility(IPersonSet).findByName(name)
        elif searchfor == "peopleonly":
            results = getUtility(IPersonSet).findPersonByName(name)
        elif searchfor == "teamsonly":
            results = getUtility(IPersonSet).findTeamByName(name)

        start = int(self.request.get('batch_start', 0))
        batch = Batch(list=results, start=start, size=BATCH_SIZE)
        return BatchNavigator(batch=batch, request=self.request)


class PersonRdfView:
    """A view that sets its mime-type to application/rdf+xml"""
    def __init__(self, context, request):
        self.context = context
        self.request = request
        request.response.setHeader('content-type', 'application/rdf+xml')
        request.response.setHeader('Content-Disposition',
                                   'attachment; filename=' + 
                                   self.context.name + '.rdf')


class PersonView:
    """A simple View class to be used in all Person's pages."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.message = None
        self.user = getUtility(ILaunchBag).user
        if context.isTeam():
            # These methods are called here because their return values are
            # going to be used in some other places (including
            # self.hasCurrentPolls()).
            pollsubset = IPollSubset(self.context)
            self.openpolls = pollsubset.getOpenPolls()
            self.closedpolls = pollsubset.getClosedPolls()
            self.notyetopenedpolls = pollsubset.getNotYetOpenedPolls()

    def hasCurrentPolls(self):
        """Return True if this team has any non-closed polls."""
        assert self.context.isTeam()
        return bool(len(self.openpolls) or len(self.notyetopenedpolls))

    def no_bounties(self):
        return not (self.context.ownedBounties or 
            self.context.reviewerBounties or
            self.context.subscribedBounties or
            self.context.claimedBounties)
    def activeMembersCount(self):
        return len(self.context.activemembers)

    def userIsOwner(self):
        """Return True if the user is the owner of this Team."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False

        return user.inTeam(self.context.teamowner)

    def userHasMembershipEntry(self):
        """Return True if the logged in user has a TeamMembership entry for
        this Team."""
        return bool(self._getMembershipForUser())

    def userIsActiveMember(self):
        """Return True if the user is an active member of this team."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False
        return user in self.context.activemembers

    def membershipStatusDesc(self):
        tm = self._getMembershipForUser()
        assert tm is not None, (
            'This method is not meant to be called for users which are not '
            'members of this team.')

        description = tm.status.description
        if tm.status == TeamMembershipStatus.DEACTIVATED and tm.reviewercomment:
            description += ("The reason for the deactivation is: '%s'"
                            % tm.reviewercomment)
        return description

    def userCanRequestToLeave(self):
        """Return true if the user can request to leave this team.

        A given user can leave a team only if he's an active member.
        """
        return self.userIsActiveMember()

    def userCanRequestToJoin(self):
        """Return true if the user can request to join this team.

        The user can request if it never asked to join this team, if it
        already asked and the subscription status is DECLINED or if the team's
        subscriptionpolicy is OPEN and the user is not an APPROVED or ADMIN
        member.
        """
        tm = self._getMembershipForUser()
        if tm is None:
            return True

        adminOrApproved = [TeamMembershipStatus.APPROVED,
                           TeamMembershipStatus.ADMIN]
        open = TeamSubscriptionPolicy.OPEN
        if tm.status == TeamMembershipStatus.DECLINED or (
            tm.status not in adminOrApproved and
            tm.team.subscriptionpolicy == open):
            return True
        else:
            return False

    def _getMembershipForUser(self):
        user = getUtility(ILaunchBag).user
        if user is None:
            return None
        tms = getUtility(ITeamMembershipSet)
        return tms.getByPersonAndTeam(user.id, self.context.id)

    def joinAllowed(self):
        """Return True if this is not a restricted team."""
        restricted = TeamSubscriptionPolicy.RESTRICTED
        return self.context.subscriptionpolicy != restricted

    def actionCategories(self):
        return KarmaActionCategory.items

    def actions(self, actionCategory):
        """Return a list of actions of the given category performed by 
        this person."""
        kas = getUtility(IKarmaActionSet)
        return kas.selectByCategoryAndPerson(actionCategory, self.context)

    def actionsCount(self, action):
        """Return the number of times this person performed this action."""
        karmaset = getUtility(IKarmaSet)
        return len(karmaset.selectByPersonAndAction(self.context, action))

    def setUpBugTasksToShow(self):
        """Setup the bugtasks we will always show."""
        self.recentBugTasks = self.mostRecentBugTasks()
        self.importantBugTasks = self.mostImportantBugTasks()
        # XXX: Because of the following 2 lines, a warning is going to be 
        # raised saying that we're getting a slice of an unordered set, and
        # this means we probably have a bug hiding somewhere, because both
        # sets are ordered here.
        self.assignedBugsToShow = bool(
            self.recentBugTasks or self.importantBugTasks)

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
                self.context, self.user, user=self.user, orderBy=orderBy)
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

    def gpgkeysCount(self):
        return len(self.context.gpgkeys)

    def signedcocsCount(self):
        return len(self.context.signedcocs)

    def performCoCChanges(self):
        """Make changes to code-of-conduct signature records for this
        person."""
        sig_ids = self.request.form.get("DEACTIVATE_SIGNATURE")

        if sig_ids is not None:
            sCoC_util = getUtility(ISignedCodeOfConductSet)

            # verify if we have multiple entries to deactive
            if not isinstance(sig_ids, list):
                sig_ids = [sig_ids]

            for sig_id in sig_ids:
                sig_id = int(sig_id)
                # Deactivating signature
                comment = 'Deactivated by Owner'
                sCoC_util.modifySignature(sig_id, self.user, comment, False)

            return True

    # restricted set of methods to be proxied by form_action()
    permitted_actions = ['claim_gpg', 'deactivate_gpg', 'remove_gpgtoken',
                         'revalidate_gpg', 'add_ssh', 'remove_ssh']

    def form_action(self):
        if self.request.method != "POST":
            # Nothing to do
            return ''
        
        action = self.request.form.get('action')

        # primary check on restrict set of 'form-like' methods.
        if action and (action not in self.permitted_actions):
            return 'Forbidden Form Method: %s' % action
        
        # do not mask anything 
        return getattr(self, action)()       

    # XXX cprov 20050401
    # As "Claim GPG key" takes a lot of time, we should process it
    # throught the NotificationEngine.
    def claim_gpg(self):
        fingerprint = self.request.form.get('fingerprint')

        sanitisedfpr = sanitiseFingerprint(fingerprint)

        if not sanitisedfpr:
            return 'Malformed fingerprint:<code>%s</code>' % fingerprint

        fingerprint = sanitisedfpr

        gpgkeyset = getUtility(IGPGKeySet)
                
        if gpgkeyset.getByFingerprint(fingerprint):
            return 'GPG key <code>%s</code> already imported' % fingerprint

        # import the key to the local keyring
        gpghandler = getUtility(IGPGHandler)
        result, key = gpghandler.retrieveKey(fingerprint)
        
        if not result:
            # use the content ok 'key' for debug proposes
            return (
                "Launchpad could not import GPG key, the reason was:"
                "<code>%s</code>."
                "Check if you published it correctly in the global key ring "
                "(using <kbd>gpg --send-keys KEY</kbd>) and that you add "
                "entered the fingerprint correctly (as produced by <kbd>"
                "gpg --fingerprint YOU</kdb>). Try later or cancel your "
                "request." % (key))

        self._validateGPG(key)

        return ('A message has been sent to <code>%s</code>, encrypted with '
                'the key <code>%s<code>. To confirm the key is yours, decrypt '
                'the message and follow the link inside.'
                % (self.context.preferredemail.email, key.displayname))


    def deactivate_gpg(self):
        keyids = self.request.form.get('DEACTIVATE_GPGKEY')
        
        if keyids is not None:
            comment = 'Key(s):<code>'
            
            # verify if we have multiple entries to deactive
            if not isinstance(keyids, list):
                keyids = [keyids]

            gpgkeyset = getUtility(IGPGKeySet)

            for keyid in keyids:
                gpgkeyset.deactivateGpgKey(keyid)
                gpgkey = gpgkeyset.get(keyid)
                comment += ' %s' % gpgkey.displayname

            comment += '</code> deactivated'
            flush_database_updates()            
            return comment

        return 'No Key(s) selected for deactivation.'

    def remove_gpgtoken(self):
        tokenfprs = self.request.form.get('REMOVE_GPGTOKEN')
        
        if tokenfprs is not None:
            comment = 'Token(s) for:<code>'
            logintokenset = getUtility(ILoginTokenSet)

            # verify if we have multiple entries to deactive
            if not isinstance(tokenfprs, list):
                tokenfprs = [tokenfprs]

            for tokenfpr in tokenfprs:
                # retrieve token info
                logintokenset.deleteByFingerprintAndRequester(tokenfpr,
                                                              self.user)
                comment += ' %s' % tokenfpr
                
            comment += '</code> key fingerprint(s) deleted.'
            return comment

        return 'No Token(s) selected for deletion.'

    def revalidate_gpg(self):
        keyids = self.request.form.get('REVALIDATE_GPGKEY')

        if keyids is not None:
            found = []
            notfound = []
            # verify if we have multiple entries to deactive
            if not isinstance(keyids, list):
                keyids = [keyids]
                
            gpghandler = getUtility(IGPGHandler)
            keyset = getUtility(IGPGKeySet)
            
            for keyid in keyids:
                # retrieve key info from LP
                gpgkey = keyset.get(keyid)
                result, key = gpghandler.retrieveKey(gpgkey.fingerprint)
                if not result:
                    notfound.append(gpgkey.fingerprint) 
                    continue
                self._validateGPG(key)
                found.append(key.displayname)
                
            comment = ''
            if len(found):
                comment += ('Key(s):<code>%s</code> revalidation email sent '
                            'to %s .' % (' '.join(found),
                                         self.context.preferredemail.email))
            if len(notfound):
                comment += ('Key(s):<code>%s</code> were skiped because could '
                            'not be retrived by Launchpad, verify if the key '
                            'is correctly published in the global key ring.' %
                            (''.join(notfound)))

            return comment

        return 'No Key(s) selected for revalidation.'

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

    def _validateGPG(self, key):
        logintokenset = getUtility(ILoginTokenSet)
        bag = getUtility(ILaunchBag)

        preferredemail = bag.user.preferredemail.email
        login = bag.login

        token = logintokenset.new(self.context, login,
                                  preferredemail,
                                  LoginTokenType.VALIDATEGPG,
                                  fingerprint=key.fingerprint)

        appurl = self.request.getApplicationURL()
        token.sendGpgValidationRequest(appurl, key, encrypt=True)


class TeamJoinView(PersonView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToJoin():
            # Nothing to do
            return

        user = getUtility(ILaunchBag).user
        if self.request.form.get('join'):
            user.join(self.context)
            appurl = self.request.getApplicationURL()
            notify(JoinTeamRequestEvent(user, self.context, appurl))

        self.request.response.redirect('./')


class TeamLeaveView(PersonView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToLeave():
            # Nothing to do
            return

        user = getUtility(ILaunchBag).user
        if self.request.form.get('leave'):
            user.leave(self.context)

        self.request.response.redirect('./')


class PersonEditView:

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

        # XXX: wiki is hard-coded for Launchpad 1.0
        #      - Andrew Bennetts, 2005-06-14
        #wiki = request.form.get("wiki")
        wikiname = request.form.get("wikiname")
        network = request.form.get("network")
        nickname = request.form.get("nickname")
        jabberid = request.form.get("jabberid")
        archuserid = request.form.get("archuserid")

        #WikiName
        # Assertions that should be true at least until 1.0
        assert person.wiki, 'People should always have wikinames'
        if person.wiki.wikiname != wikiname:
            if getUtility(IWikiNameSet).exists(wikiname):
                self.errormessage = (
                    'The wikiname %s for %s is already taken' 
                    % (wikiname, UBUNTU_WIKI_URL,))
                return False
            person.wiki.wikiname = wikiname

        #IrcID
        if (network and not nickname) or (nickname and not network):
            self.errormessage = ('You cannot provide the irc nickname without '
                                 'an irc network, or the irc network without '
                                 'a nickname.')
            return False
        elif network and nickname and person.irc is not None:
            person.irc.network = network
            person.irc.nickname = nickname
        elif network and nickname and person.irc is None:
            getUtility(IIrcIDSet).new(person.id, network, nickname)
        elif person.irc is not None:
            person.irc.destroySelf()

        #JabberID
        if jabberid and person.jabber is not None:
            person.jabber.jabberid = jabberid
        elif jabberid and person.jabber is None:
            getUtility(IJabberIDSet).new(person.id, jabberid)
        elif person.jabber is not None:
            person.jabber.destroySelf()

        #ArchUserID
        if archuserid and person.archuser is not None:
            person.archuser.archuserid = archuserid
        elif archuserid and person.archuser is None:
            getUtility(IArchUserIDSet).new(person.id, archuserid)
        elif person.archuser is not None:
            person.archuser.destroySelf()

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

        token = getUtility(ILoginTokenSet).new(
                    self.context, getUtility(ILaunchBag).login, email,
                    LoginTokenType.VALIDATEEMAIL)
        token.sendEmailValidationRequest(self.request.getApplicationURL())

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
            # These asserts will fail only if someone poisons the form.
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
        assert self.context.preferredemail is not None
        if self.context.preferredemail == emailaddress:
            # This will happen only if a person is submitting a stale page.
            self.message = (
                "You can't remove %s because it's your contact email "
                "address." % self.context.preferredemail.email)
            return
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
        if not valid_email(newemail):
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
                    % (email.email, browsername))
            return

        token = logintokenset.new(
                    person, getUtility(ILaunchBag).login, newemail,
                    LoginTokenType.VALIDATEEMAIL)
        token.sendEmailValidationRequest(self.request.getApplicationURL())

        self.message = (
                "An e-mail message was sent to '%s'. Follow the "
                "instructions in that message to confirm that the "
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


class ObjectReassignmentView:
    """A view class used when reassigning an object that implements IHasOwner.

    By default we assume that the owner attribute is IHasOwner.owner and the
    vocabulary for the owner widget is ValidPersonOrTeam (which is the one
    used in IObjectReassignment). If any object has special needs, it'll be
    necessary to subclass ObjectReassignmentView and redefine the schema 
    and/or ownerOrMaintainerAttr attributes.

    Subclasses can also specify a callback to be called after the reassignment
    takes place. This callback must accept three arguments (in this order):
    the object whose owner is going to be changed, the old owner and the new
    owner.

    Also, if the object for which you're using this view doesn't have a
    displayname or name attribute, you'll have to subclass it and define the
    contextName attribute in your subclass constructor.
    """

    ownerOrMaintainerAttr = 'owner'
    schema = IObjectReassignment
    callback = None

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ''
        self.ownerOrMaintainer = getattr(context, self.ownerOrMaintainerAttr)
        setUpWidgets(self, self.schema, IInputWidget)
        self.contextName = (getattr(self.context, 'displayname', None) or
                            getattr(self.context, 'name', None))

    def processForm(self):
        if self.request.method == 'POST':
            self.changeOwner()

    def changeOwner(self):
        """Change the owner of self.context to the one choosen by the user."""
        newOwner = self._getNewOwner()
        if newOwner is None:
            return

        oldOwner = getattr(self.context, self.ownerOrMaintainerAttr)
        setattr(self.context, self.ownerOrMaintainerAttr, newOwner)
        if callable(self.callback):
            self.callback(self.context, oldOwner, newOwner)
        self.request.response.redirect('.')

    def _getNewOwner(self):
        """Return the new owner for self.context, as specified by the user.
        
        If anything goes wrong, return None and assign an error message to
        self.errormessage to inform the user about what happened.
        """
        personset = getUtility(IPersonSet)
        request = self.request
        owner_name = request.form.get(self.owner_widget.name)
        if not owner_name:
            self.errormessage = (
                "You have to specify the name of the person/team that's "
                "going to be the new %s." % self.ownerOrMaintainerAttr)
            return None

        if request.form.get('existing') == 'existing':
            try:
                # By getting the owner using getInputValue() we make sure
                # it's valid according to the vocabulary of self.schema's
                # owner widget.
                owner = self.owner_widget.getInputValue()
            except WidgetInputError:
                self.errormessage = (
                    "The person/team named '%s' is not a valid owner for %s."
                    % (owner_name, self.contextName))
                return None
            except ConversionError:
                self.errormessage = (
                    "There's no person/team named '%s' in Launchpad."
                    % owner_name)
                return None
        else:
            if personset.getByName(owner_name):
                self.errormessage = (
                    "There's already a person/team with the name '%s' in "
                    "Launchpad. Please choose a different name or select "
                    "the option to make that person/team the new owner, "
                    "if that's what you want." % owner_name)
                return None

            owner = personset.newTeam(
                    teamownerID=self.user.id, name=owner_name,
                    displayname=owner_name.capitalize())

        return owner


class TeamReassignmentView(ObjectReassignmentView):

    ownerOrMaintainerAttr = 'teamowner'
    schema = ITeamReassignment

    def __init__(self, context, request):
        ObjectReassignmentView.__init__(self, context, request)
        self.contextName = self.context.browsername
        self.callback = self._addOwnerAsMember

    def _addOwnerAsMember(self, team, oldOwner, newOwner):
        """Add the new and the old owners as administrators of the team.

        When a user creates a new team, he is added as an administrator of
        that team. To be consistent with this, we must make the new owner an
        administrator of the team.
        Also, the ObjectReassignment spec says that we must make the old owner
        an administrator of the team, and so we do.
        """
        team.addMember(newOwner)
        team.setMembershipStatus(newOwner, TeamMembershipStatus.ADMIN)
        team.addMember(oldOwner)
        team.setMembershipStatus(oldOwner, TeamMembershipStatus.ADMIN)


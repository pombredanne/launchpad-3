# Copyright 2004 Canonical Ltd

__metaclass__ = type

from datetime import datetime, timedelta

import pytz

# zope imports
from zope.schema import TextLine
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope.i18nmessageid import MessageIDFactory
_ = MessageIDFactory('launchpad')

# interface import
from canonical.launchpad.interfaces import IPersonSet, ILaunchBag, ITeam
from canonical.launchpad.interfaces import IEmailAddressSet
from canonical.launchpad.interfaces import ILoginTokenSet
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import ITeamMembershipSubset
from canonical.launchpad.interfaces import ILaunchpadCelebrities

from canonical.config import config
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.validators.email import valid_email
from canonical.launchpad.event.team import JoinTeamRequestEvent
from canonical.launchpad.mail.sendmail import simple_sendmail

# lp imports
from canonical.lp.dbschema import TeamMembershipStatus, LoginTokenType
from canonical.lp.dbschema import TeamSubscriptionPolicy

from canonical.database.sqlbase import flush_database_updates


class TeamEditView(SQLObjectEditView):

    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)
        self.team = self.context


class TeamEmailView:
    """A View to edit a team's contact email address."""

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.team = self.context
        self.wrongemail = None
        self.errormessage = ""
        self.feedback = ""

    def processForm(self):
        """Process the form, if it was submitted."""
        # Any self-posting form that updates the database and want to display
        # these updated values have to flush all db updates. This is why we
        # call flush_database_updates() here.

        request = self.request
        if request.method != "POST":
            # Nothing to do
            return

        emailset = getUtility(IEmailAddressSet)

        if request.form.get('ADD_EMAIL') or request.form.get('CHANGE_EMAIL'):
            emailaddress = request.form.get('newcontactemail', "")
            emailaddress = emailaddress.lower().strip()
            if not valid_email(emailaddress):
                self.errormessage = (
                    "The email address you're trying to add doesn't seem to "
                    "be valid. Please make sure it's correct and try again.")
                # We want to display the invalid address so the user can just
                # fix what's wrong and send again.
                self.wrongemail = emailaddress
                return

            email = emailset.getByEmail(emailaddress)
            if email is not None:
                if email.person.id != self.team.id:
                    self.errormessage = (
                        "The email address you're trying to add is already "
                        "registered in Launchpad for %s."
                        % email.person.browsername())
                else:
                    self.errormessage = (
                        "This is the current contact email address of this "
                        "team. There's no need to add it again.")
                return

            self._sendEmailValidationRequest(emailaddress)
            flush_database_updates()
            return
        elif request.form.get('REMOVE_EMAIL'):
            if self.team.preferredemail is None:
                self.errormessage = "This team has no contact email address."
                return
            self.team.preferredemail.destroySelf()
            self.feedback = (
                "The contact email address of this team has been removed. "
                "From now on, all notifications directed to this team will "
                "be sent to all team members.")
            flush_database_updates()
            return
        elif (request.form.get('REMOVE_UNVALIDATED') or
              request.form.get('VALIDATE')):
            email = self.request.form.get("UNVALIDATED_SELECTED")
            if email is None:
                self.feedback = ("You must select the email address you want "
                                 "to remove/confirm.")
                return

            if request.form.get('REMOVE_UNVALIDATED'):
                getUtility(ILoginTokenSet).deleteByEmailAndRequester(
                    email, self.context)
                self.feedback = (
                    "The email address '%s' has been removed." % email)
            elif request.form.get('VALIDATE'):
                self._sendEmailValidationRequest(email)

            flush_database_updates()
            return

    def _sendEmailValidationRequest(self, email):
        """Send a validation message to <email> and update self.feedback."""
        appurl = self.request.getApplicationURL()
        sendEmailValidationRequest(self.team, email, appurl)
        self.feedback = (
            "A new message was sent to '%s', please follow the instructions "
            "on that message to validate the new contact email address of "
            "this team." % email)


class ITeamCreation(ITeam):
    """An interface to be used by the team creation form.

    We need this special interface so we can allow people to specify a contact
    email address for a team upon its creation.
    """

    contactemail = TextLine(
        title=_("Contact Email Address"), required=False, readonly=False,
        description=_(
            "This is the email address we'll send all notifications to this "
            "team. If no contact address is chosen, notifications directed to "
            "this team will be sent to all team members. After finishing the "
            "team creation, a new message will be sent to this address with "
            "instructions on how to finish its registration."))


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

        email = kw.pop('contactemail', None)
        kw['teamownerID'] = getUtility(ILaunchBag).user.id
        team = getUtility(IPersonSet).newTeam(**kw)
        notify(ObjectCreatedEvent(team))

        if email is not None:
            appurl = self.request.getApplicationURL()
            sendEmailValidationRequest(team, email, appurl)

        self._nextURL = '/people/%s' % team.name
        return team


def sendEmailValidationRequest(team, email, appurl):
    """Send a validation message to <email>, so it can be registered to <team>.

    We create the necessary LoginToken entry and then send the message to
    <email>, with <team> as the requester. The user which actually made the
    request in behalf of the team is also shown on the message.
    """
    template = open(
        'lib/canonical/launchpad/emailtemplates/validate-teamemail.txt').read()

    fromaddress = "Launchpad Email Validator <noreply@ubuntu.com>"
    subject = "Launchpad: Validate your team's contact email address"
    login = getUtility(ILaunchBag).login
    user = getUtility(ILaunchBag).user
    token = getUtility(ILoginTokenSet).new(
                team, login, email, LoginTokenType.VALIDATETEAMEMAIL)

    replacements = {'longstring': token.token,
                    'team': token.requester.browsername,
                    'requester': '%s (%s)' % (user.browsername, user.name),
                    'toaddress': token.email,
                    'appurl': appurl,
                    'admin_email': config.admin_address}
    message = template % replacements
    simple_sendmail(fromaddress, token.email, subject, message)


class TeamView:
    """A simple View class to be used in Team's pages where we don't have
    actions to process.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.team = self.context

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
        """Return True if the logged in user has a TeamParticipation entry
        for this Team. This implies a membership status of either ADMIN or
        APPROVED."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False

        return user.inTeam(self.context)

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

        The user can request only if its subscription status is APPROVED or
        ADMIN.
        """
        tm = self._getMembershipForUser()
        if tm is None:
            return False

        allowed = [TeamMembershipStatus.APPROVED, TeamMembershipStatus.ADMIN]
        if tm.status in allowed:
            return True
        else:
            return False

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


class TeamJoinView(TeamView):

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


class TeamLeaveView(TeamView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToLeave():
            # Nothing to do
            return

        user = getUtility(ILaunchBag).user
        if self.request.form.get('leave'):
            user.leave(self.context)

        self.request.response.redirect('./')


class TeamMembersView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.team = self.context.team
        self.tmsubset = ITeamMembershipSubset(self.team)

    def allMembersCount(self):
        return getUtility(ITeamMembershipSet).getTeamMembersCount(self.team.id)

    def activeMembersCount(self):
        return len(self.team.activemembers)

    def proposedMembersCount(self):
        return len(self.team.proposedmembers)

    def inactiveMembersCount(self):
        return len(self.team.inactivemembers)

    def activeMemberships(self):
        return self.tmsubset.getActiveMemberships()

    def proposedMemberships(self):
        return self.tmsubset.getProposedMemberships()

    def inactiveMemberships(self):
        return self.tmsubset.getInactiveMemberships()


class ProposedTeamMembersEditView:

    def __init__(self, context, request):
        self.context = context
        self.team = context.team
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def processProposed(self):
        if self.request.method != "POST":
            return

        team = self.team
        expires = team.defaultexpirationdate
        for person in team.proposedmembers:
            action = self.request.form.get('action_%d' % person.id)
            membership = _getMembership(person.id, team.id)
            if action == "approve":
                status = TeamMembershipStatus.APPROVED
            elif action == "decline":
                status = TeamMembershipStatus.DECLINED
            elif action == "hold":
                continue

            team.setMembershipStatus(person, status, expires,
                                     reviewer=self.user)

        # Need to flush all changes we made, so subsequent queries we make
        # with this transaction will see this changes and thus they'll be
        # displayed on the page that calls this method.
        flush_database_updates()


def _getMembership(personID, teamID):
    tms = getUtility(ITeamMembershipSet)
    membership = tms.getByPersonAndTeam(personID, teamID)
    assert membership is not None
    return membership


class AddTeamMemberView(AddView):

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.alreadyMember = None
        self.addedMember = None
        added = self.request.get('added')
        notadded = self.request.get('notadded')
        if added:
            self.addedMember = getUtility(IPersonSet).get(added)
        elif notadded:
            self.alreadyMember = getUtility(IPersonSet).get(notadded)
        AddView.__init__(self, context, request)

    def nextURL(self):
        if self.addedMember:
            return '+add?added=%d' % self.addedMember.id
        elif self.alreadyMember:
            return '+add?notadded=%d' % self.alreadyMember.id
        else:
            return '+add'

    def createAndAdd(self, data):
        kw = {}
        for key, value in data.items():
            kw[str(key)] = value

        team = self.context.team
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN

        member = kw['newmember']
        if member.id == team.id:
            # Do not add this team as a member of itself, please.
            return

        expires = team.defaultexpirationdate
        if member.hasMembershipEntryFor(team):
            membership = _getMembership(member.id, team.id)
            if membership.status in (approved, admin):
                self.alreadyMember = member
            else:
                team.setMembershipStatus(member, approved, expires,
                                         reviewer=self.user)
                self.addedMember = member
        else:
            team.addMember(member, approved, reviewer=self.user)
            self.addedMember = member

class TeamMembershipEditView:

    monthnames = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                  5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                  10: 'October', 11: 'November', 12: 'December'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ""

    def userIsTeamOwnerOrLPAdmin(self):
        return (self.user.inTeam(self.context.team.teamowner) or
                self.user.inTeam(getUtility(ILaunchpadCelebrities).admin))

    def isActive(self):
        return self.context.status in [TeamMembershipStatus.APPROVED,
                                       TeamMembershipStatus.ADMIN]

    def isInactive(self):
        return self.context.status in [TeamMembershipStatus.EXPIRED,
                                       TeamMembershipStatus.DEACTIVATED]

    def isAdmin(self):
        return self.context.status == TeamMembershipStatus.ADMIN

    def isProposed(self):
        return self.context.status == TeamMembershipStatus.PROPOSED

    def isExpired(self):
        return self.context.status == TeamMembershipStatus.EXPIRED

    def isDeactivated(self):
        return self.context.status == TeamMembershipStatus.DEACTIVATED

    def canChangeExpirationDate(self):
        """Return True if the logged in user can change the expiration date of
        this membership. Team administrators can't change the expiration date
        of their own membership."""
        if self.userIsTeamOwnerOrLPAdmin():
            return True

        if self.user.id == self.context.person.id:
            return False
        else:
            return True

    def membershipExpires(self):
        """Return True if this membership is scheduled to expire one day."""
        if self.context.dateexpires is None:
            return False
        else:
            return True

    def _getExpirationDate(self):
        """Return a datetime with the expiration date selected on the form.

        Return None if the selected date was empty. Also raises ValueError if
        the date selected is invalid.
        """
        if self.request.form.get('expires') == 'never':
            return None

        year = int(self.request.form.get('year'))
        month = int(self.request.form.get('month'))
        day = int(self.request.form.get('day'))
        return datetime(year, month, day, tzinfo=pytz.timezone('UTC'))

    def _setMembershipData(self, status):
        """Set all data specified on the form, for this TeamMembership.

        Get all data from the form, together with the given status and set
        them for this TeamMembership object.
        """
        team = self.context.team
        member = self.context.person
        comment = self.request.form.get('comment')
        try:
            expires = self._getExpirationDate()
        except ValueError, err:
            self.errormessage = 'Expiration date: %s' % err
            return

        team.setMembershipStatus(member, status, expires,
                                 reviewer=self.user, comment=comment)

    def processInactiveMember(self):
        assert self.context.status in (TeamMembershipStatus.EXPIRED,
                                       TeamMembershipStatus.DEACTIVATED)

        self._setMembershipData(TeamMembershipStatus.APPROVED)
        self.request.response.redirect('../')

    def processProposedMember(self):
        assert self.context.status == TeamMembershipStatus.PROPOSED

        action = self.request.form.get('editproposed')
        if action == 'Decline':
            status = TeamMembershipStatus.DECLINED
        else:
            status = TeamMembershipStatus.APPROVED
        self._setMembershipData(status)
        self.request.response.redirect('../')

    def processActiveMember(self):
        assert self.context.status in (TeamMembershipStatus.ADMIN,
                                       TeamMembershipStatus.APPROVED)

        if self.request.form.get('editactive') == 'Deactivate':
            team = self.context.team
            member = self.context.person
            deactivated = TeamMembershipStatus.DEACTIVATED
            comment = self.request.form.get('comment')
            expires = self.context.dateexpires
            team.setMembershipStatus(member, deactivated, expires,
                                     reviewer=self.user, comment=comment)
            self.request.response.redirect('../')
            return
            
        # XXX: salgado, 2005-03-15: I would like to just write this as 
        # "status = self.context.status", but it doesn't work because
        # self.context.status is security proxied.
        status = TeamMembershipStatus.items[self.context.status.value]

        # XXX: salgado, 2005-03-15: This is a hack to make sure only the
        # teamowner can promote a given member to admin, while we don't have a
        # specific permission setup for this.
        if self.context.status == TeamMembershipStatus.ADMIN:
            if self.request.form.get('admin') == 'no':
                status = TeamMembershipStatus.APPROVED
        else:
            if (self.request.form.get('admin') == 'yes' and 
                self.userIsTeamOwnerOrLPAdmin()):
                status = TeamMembershipStatus.ADMIN

        self._setMembershipData(status)
        self.request.response.redirect('../')

    def processForm(self):
        if not self.request.method == 'POST':
            return
        
        if self.request.form.get('editactive'):
            self.processActiveMember()
        elif self.request.form.get('editproposed'):
            self.processProposedMember()
        elif self.request.form.get('editinactive'):
            self.processInactiveMember()

    def dateChooserForExpiredMembers(self):
        expires = self.context.team.defaultrenewedexpirationdate
        return self.buildDateChooser(expires)

    def dateChooserForProposedMembers(self):
        expires = self.context.team.defaultexpirationdate
        return self.buildDateChooser(expires)

    def dateChooserWithCurrentExpirationSelected(self):
        return self.buildDateChooser(self.context.dateexpires)

    # XXX: salgado, 2005-03-15: This will be replaced as soon as we have
    # browser:form.
    def buildDateChooser(self, selected=None):
        html = '<select name="day">'
        html += '<option value="0"></option>'
        for day in range(1, 32):
            if selected and day == selected.day:
                html += '<option selected value="%d">%d</option>' % (day, day)
            else:
                html += '<option value="%d">%d</option>' % (day, day)
        html += '</select>'

        html += '<select name=month>'
        html += '<option value="0"></option>'
        for month in range(1, 13):
            monthname = self.monthnames[month]
            if selected and month == selected.month:
                html += ('<option selected value="%d">%s</option>' % 
                         (month, monthname))
            else:
                html += ('<option value="%d">%s</option>' % 
                         (month, monthname))
        html += '</select>'

        # XXX: salgado, 2005-03-16: We need to define it somewhere else, but
        # it's not that urgent, so I'll leave it here for now.
        max_year = 2050
        html += '<select name="year">'
        html += '<option value="0"></option>'
        for year in range(datetime.utcnow().year, max_year):
            if selected and year == selected.year:
                html += '<option selected value="%d">%d</option>' % (year, year)
            else:
                html += '<option value="%d">%d</option>' % (year, year)
        html += '</select>'

        return html


def traverseTeam(team, request, name):
    if name == '+members':
        return ITeamMembershipSubset(team)


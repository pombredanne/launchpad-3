# Copyright 2004 Canonical Ltd

__metaclass__ = type

from datetime import datetime, timedelta

# zope imports
from zope.event import notify
from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile

# interface import
from canonical.launchpad.interfaces import IPersonSet, ILaunchBag
from canonical.launchpad.interfaces import IEmailAddressSet
from canonical.launchpad.interfaces import ILoginTokenSet
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import ITeamMembershipSubset
from canonical.launchpad.interfaces import ILaunchpadCelebrities

from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.helpers import well_formed_email
from canonical.launchpad.event.team import JoinTeamRequestEvent
from canonical.launchpad.mail.sendmail import simple_sendmail

# lp imports
from canonical.lp.dbschema import TeamMembershipStatus, LoginTokenType
from canonical.lp.dbschema import TeamSubscriptionPolicy

from canonical.database.sqlbase import flush_database_updates


class TeamEditView(SQLObjectEditView):

    viewsPortlet = ViewPageTemplateFile(
        '../templates/portlet-person-views.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-team-actions.pt')

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

    def formSuccessfullyProcessed(self):
        """Return True if the form was submitted and processed successfully.
        
        Return False if the form wasn't submitted or not processed
        successfully."""
        if self.request.method != "POST":
            # Nothing to do
            return False

        request = self.request
        emailset = getUtility(IEmailAddressSet)
        logintokenset = getUtility(ILoginTokenSet)

        if request.form.get('ADD_EMAIL') or request.form.get('CHANGE_EMAIL'):
            emailaddress = request.form.get('newcontactemail', "")
            emailaddress = emailaddress.lower().strip()
            if not well_formed_email(emailaddress):
                self.errormessage = (
                        "The email address you're trying to add doesn't seem "
                        "to be valid. Please make sure it's correct and try "
                        "again.")
                # We want to display the invalid address so the user can just
                # fix what's wrong and send again.
                self.wrongemail = emailaddress
                return False

            email = emailset.getByEmail(emailaddress)
            if email is not None:
                if email.person.id != self.team.id:
                    self.errormessage = (
                            "The email address you're trying to add is "
                            "already registered in Launchpad for %s."
                            % email.person.browsername())
                else:
                    self.errormessage = (
                            "This is the current contact email address of "
                            "this team. There's no need to add it again.")
                return False

            login = getUtility(ILaunchBag).login
            token = logintokenset.new(self.team, login, emailaddress,
                                      LoginTokenType.VALIDATETEAMEMAIL)
            sendEmailValidationRequest(token, request.getApplicationURL())
            self.feedback = (
                    "A new message was sent to '%s', please follow the "
                    "instructions on that message to validate the new "
                    "contact email address of this team." % emailaddress)
            # We want to see the new contact email address on this page, so we
            # have to flush all db updates.
            flush_database_updates()
            return True
        elif request.form.get('REMOVE_EMAIL'):
            if self.team.preferredemail is None:
                self.errormessage = (
                        "This team have no contact email address.")
                return False
            self.team.preferredemail.destroySelf()
            self.feedback = (
                    "The contact email address of this team have been "
                    "removed. From now on, all notifications directed to "
                    "this team will be sent to all team members.")
            # We want to see in this page that the team doesn't have a contact
            # email address anymore, so we have to flush all db updates.
            flush_database_updates()
            return True


def sendEmailValidationRequest(token, appurl):
    # XXX: must use another template.
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



class TeamView:
    """A simple View class to be used in Team's pages where we don't have
    actions to process.
    """

    viewsPortlet = ViewPageTemplateFile(
        '../templates/portlet-person-views.pt')

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-team-actions.pt')

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

    def userHaveMembershipEntry(self):
        """Return True if the logged in user have a TeamMembership entry for
        this Team."""
        return bool(self._getMembershipForUser())

    def userIsActiveMember(self):
        """Return True if the logged in user have a TeamParticipation entry
        for this Team. This implies a membership status of either ADMIN or
        APPROVED."""
        user = getUtility(ILaunchBag).user
        if user is None:
            return False

        return user.inTeam(self.context)

    def subscriptionPolicyDesc(self):
        policy = self.context.subscriptionpolicy
        if policy == TeamSubscriptionPolicy.RESTRICTED:
            return "Restricted team. Only administrators can add new members"
        elif policy == TeamSubscriptionPolicy.MODERATED:
            return ("Moderated team. New subscriptions are subjected to "
                    "approval by one of the team's administrators.")
        elif policy == TeamSubscriptionPolicy.OPEN:
            return "Open team. Any user can join and no approval is required"

    def membershipStatusDesc(self):
        tm = self._getMembershipForUser()
        if tm is None:
            return "You are not a member of this team."

        if tm.status == TeamMembershipStatus.PROPOSED:
            desc = ("You are currently a proposed member of this team."
                    "Your subscription depends on approval by one of the "
                    "team's administrators.")
        elif tm.status == TeamMembershipStatus.APPROVED:
            desc = ("You are currently an approved member of this team.")
        elif tm.status == TeamMembershipStatus.ADMIN:
            desc = ("You are currently an administrator of this team.")
        elif tm.status == TeamMembershipStatus.DEACTIVATED:
            desc = "Your subscription for this team is currently deactivated."
            if tm.reviewercomment is not None:
                desc += "The reason provided for the deactivation is: '%s'" % \
                        tm.reviewercomment
        elif tm.status == TeamMembershipStatus.EXPIRED:
            desc = ("Your subscription for this team is currently expired, "
                    "waiting for renewal by one of the team's administrators.")
        elif tm.status == TeamMembershipStatus.DECLINED:
            desc = ("Your subscription for this team is currently declined. "
                    "Clicking on the 'Join' button will put you on the "
                    "proposed members queue, waiting for the approval of one "
                    "of the team's administrators")

        return desc

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

    actionsPortlet = ViewPageTemplateFile(
        '../templates/portlet-team-actions.pt')

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
        return datetime(year, month, day)

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


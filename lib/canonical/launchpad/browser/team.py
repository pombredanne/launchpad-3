# Copyright 2004 Canonical Ltd

from datetime import datetime, timedelta

# lp imports
from canonical.lp.dbschema import TeamMembershipStatus
from canonical.lp.dbschema import TeamSubscriptionPolicy

from canonical.database.sqlbase import flushUpdates

from canonical.foaf.nickname import generate_nick

# interface import
from canonical.launchpad.interfaces import IPersonSet, ILaunchBag
from canonical.launchpad.interfaces import ITeamMembershipSet
from canonical.launchpad.interfaces import ITeamMembershipSubset

from canonical.launchpad.browser.editview import SQLObjectEditView

# zope imports
from zope.event import notify
from zope.app.event.objectevent import ObjectCreatedEvent
from zope.app.form.browser.add import AddView
from zope.component import getUtility


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

        # XXX: salgado, 2005-02-04: For now, we're using the email only for 
        # generating the nickname. We must decide if we need or not to 
        # require an email address for each team.
        email = kw.pop('email')
        kw['name'] = generate_nick(email)
        kw['teamownerID'] = getUtility(ILaunchBag).user.id
        team = getUtility(IPersonSet).newTeam(**kw)
        notify(ObjectCreatedEvent(team))
        self._nextURL = '/people/%s' % team.name
        return team


class TeamEditView(SQLObjectEditView):

    def __init__(self, context, request):
        SQLObjectEditView.__init__(self, context, request)


class TeamView(object):
    """A simple View class to be used in Team's pages where we don't have
    actions to process.
    """

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def activeMembersCount(self):
        return len(self.context.approvedmembers + self.context.administrators)

    def userIsOwner(self):
        """Return True if the user is the owner of this Team."""
        user = getUtility(ILaunchBag).user
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


class TeamMembersView(object):

    def __init__(self, context, request):
        self.context = context
        self.team = self.context.team
        self.request = request

    def activeMembersCount(self):
        return len(self.team.approvedmembers + self.team.administrators)

    def proposedMembersCount(self):
        return len(self.team.proposedmembers)

    def inactiveMembersCount(self):
        return len(self.team.expiredmembers +
                   self.team.deactivatedmembers)

    def activeMemberships(self):
        status = TeamMembershipStatus.ADMIN
        admins = self.team.getMembershipsByStatus(status)

        status = TeamMembershipStatus.APPROVED
        members = self.team.getMembershipsByStatus(status)
        return admins + members

    def proposedMemberships(self):
        status = TeamMembershipStatus.PROPOSED
        return self.team.getMembershipsByStatus(status)

    def inactiveMemberships(self):
        status = TeamMembershipStatus.EXPIRED
        expired = self.team.getMembershipsByStatus(status)

        status = TeamMembershipStatus.DEACTIVATED
        deactivated = self.team.getMembershipsByStatus(status)
        return expired + deactivated


class ProposedTeamMembersEditView:

    def __init__(self, context, request):
        self.context = context
        self.team = context.team
        self.request = request
        self.user = getUtility(ILaunchBag).user

    def allPeople(self):
        return getUtility(IPersonSet).getAll()

    def defaultExpirationDate(self):
        days = self.team.defaultmembershipperiod
        if days:
            return (datetime.utcnow() + timedelta(days)).date()
        else:
            return None

    def processProposed(self):
        if self.request.method != "POST":
            return

        team = self.team
        for person in team.proposedmembers:
            action = self.request.form.get('action_%d' % person.id)
            membership = _getMembership(person.id, team.id)
            if action == "approve":
                status = TeamMembershipStatus.APPROVED
            elif action == "decline":
                status = TeamMembershipStatus.DECLINED
            elif action == "hold":
                continue

            team.setMembershipStatus(person, status, reviewer=self.user)

        flushUpdates()


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

        if member.hasMembershipEntryFor(team):
            membership = _getMembership(member.id, team.id)
            if membership.status in (approved, admin):
                self.alreadyMember = member
            else:
                team.setMembershipStatus(member, approved,
                                         reviewer=self.user)
                self.addedMember = member
        else:
            team.addMember(member, approved, reviewer=self.user)
            self.addedMember = member

class TeamMembershipEditView(object):

    monthnames = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                  5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                  10: 'October', 11: 'November', 12: 'December'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ""

    def userIsTeamOwner(self):
        return self.user.inTeam(self.context.team.teamowner)

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

    def _getExpirationDate(self):
        """Return a datetime with the expiration date selected on the form.

        Return None if the selected date was empty. Also raises ValueError if
        the date selected is invalid.
        """
        year = int(self.request.form.get('year'))
        month = int(self.request.form.get('month'))
        day = int(self.request.form.get('day'))
        if year or month or day:
            return datetime(year, month, day)
        else:
            return None

    def _setMembershipData(self, status):
        """Set all data specified on the form, for this TeamMembership.

        Get all data from the form, together with the given status and set
        them for this TeamMembership object.
        """
        team = self.context.team
        member = self.context.person
        comment = self.request.form.get('comment')
        try:
            date = self._getExpirationDate()
        except ValueError, err:
            self.errormessage = 'Expiration date: %s' % err
            return

        team.setMembershipStatus(member, status, expires=date,
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
            team.setMembershipStatus(member, deactivated, reviewer=self.user,
                                     comment=comment)
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
                self.userIsTeamOwner()):
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
        days = self.context.team.defaultrenewalperiod
        expires = datetime.utcnow() + timedelta(days=days)
        return self.buildDateChooser(expires)

    def dateChooserForProposedMembers(self):
        days = self.context.team.defaultmembershipperiod
        expires = datetime.utcnow() + timedelta(days=days)
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
    if name == 'members':
        return ITeamMembershipSubset(team)


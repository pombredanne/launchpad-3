# Copyright 2004 Canonical Ltd

from datetime import datetime, timedelta

# lp imports
from canonical.lp.dbschema import TeamMembershipStatus
from canonical.lp.dbschema import TeamSubscriptionPolicy

from canonical.database.sqlbase import flushUpdates

from canonical.foaf.nickname import generate_nick

# database imports
from canonical.launchpad.database import TeamParticipation, TeamMembership

# interface import
from canonical.launchpad.interfaces import IPersonSet, ILaunchBag

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

    def activeMemberships(self):
        status = int(TeamMembershipStatus.ADMIN)
        admins = self.context.getMembershipsByStatus(status)

        status = int(TeamMembershipStatus.APPROVED)
        members = self.context.getMembershipsByStatus(status)
        return admins + members

    def userIsOwner(self):
        """Return True if the user is the owner of this Team."""
        return self.context.teamowner == getUtility(ILaunchBag).user

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
        if policy == int(TeamSubscriptionPolicy.RESTRICTED):
            return "Restricted team. Only administrators can add new members"
        elif policy == int(TeamSubscriptionPolicy.MODERATED):
            return ("Moderated team. New subscriptions are subjected to "
                    "approval by one of the team's administrators.")
        elif policy == int(TeamSubscriptionPolicy.OPEN):
            return "Open team. Any user can join and no approval is required"

    def membershipStatusDesc(self):
        tm = self._getMembershipForUser()
        if tm is None:
            return "You are not a member of this team."

        if tm.status == int(TeamMembershipStatus.PROPOSED):
            desc = ("You are currently a proposed member of this team."
                    "Your subscription depends on approval by one of the "
                    "team's administrators.")
        elif tm.status == int(TeamMembershipStatus.APPROVED):
            desc = ("You are currently an approved member of this team.")
        elif tm.status == int(TeamMembershipStatus.ADMIN):
            desc = ("You are currently an administrator of this team.")
        elif tm.status == int(TeamMembershipStatus.DEACTIVATED):
            desc = "Your subscription for this team is currently deactivated."
            if tm.reviewercomment is not None:
                desc += "The reason provided for the deactivation is: '%s'" % \
                        tm.reviewercomment
        elif tm.status == int(TeamMembershipStatus.EXPIRED):
            desc = ("Your subscription for this team is currently expired, "
                    "waiting for renewal by one of the team's administrators.")
        elif tm.status == int(TeamMembershipStatus.DECLINED):
            desc = ("Your subscription for this team is currently declined. "
                    "Clicking on the 'Join' button will put you on the "
                    "proposed members queue, waiting for approval by one of "
                    "the team's administrators")

        return desc

    def userCanRequestToUnjoin(self):
        """Return true if the user can request to unjoin this team.

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
        tm = TeamMembership.selectBy(personID=user.id, teamID=self.context.id)
        if tm.count() == 1:
            return tm[0]
        else:
            return None

    def joinAllowed(self):
        """Return True if this is not a restricted team."""
        restricted = int(TeamSubscriptionPolicy.RESTRICTED)
        return self.context.subscriptionpolicy != restricted


class TeamJoinView(TeamView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToJoin():
            # Nothing to do
            return

        user = getUtility(ILaunchBag).user
        if self.request.form.get('join'):
            user.joinTeam(self.context)

        self.request.response.redirect('./')


class TeamUnjoinView(TeamView):

    def processForm(self):
        if self.request.method != "POST" or not self.userCanRequestToUnjoin():
            # Nothing to do
            return

        user = getUtility(ILaunchBag).user
        if self.request.form.get('unjoin'):
            user.unjoinTeam(self.context)

        self.request.response.redirect('./')


class TeamMembersEditView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.addedMembers = []
        self.alreadyMembers = []

    def allPeople(self):
        return getUtility(IPersonSet).getAll()

    def proposedCount(self):
        return len(self.context.proposedmembers)

    def approvedCount(self):
        return len(self.context.approvedmembers)

    def adminCount(self):
        return len(self.context.administrators)

    def expiredCount(self):
        return len(self.context.expiredmembers)

    def deactivatedCount(self):
        return len(self.context.deactivatedmembers)

    def defaultExpirationDate(self):
        days = self.context.defaultmembershipperiod
        if days:
            return (datetime.utcnow() + timedelta(days)).date()
        else:
            return None

    def processProposed(self):
        if self.request.method != "POST":
            return

        team = self.context
        for person in team.proposedmembers:
            action = self.request.form.get('action_%d' % person.id)
            membership = self._getMembership(person.id, team.id)
            expires = None
            if action == "approve":
                status = int(TeamMembershipStatus.APPROVED)
                days = int(self.request.form.get('period_%d' % person.id))
                if days:
                    expires = datetime.utcnow() + timedelta(days)
            elif action == "decline":
                status = int(TeamMembershipStatus.DECLINED)
            elif action == "leave":
                continue

            team.setMembershipStatus(person, status, expires=expires,
                                     reviewer=self.user)

        flushUpdates()

    def addMembers(self):
        if self.request.method != "POST":
            return
        
        team = self.context
        names = self.request.form.get('people')
        if not isinstance(names, (list, tuple)):
            names = [names]
        approved = int(TeamMembershipStatus.APPROVED)
        admin = int(TeamMembershipStatus.ADMIN)
        personset = getUtility(IPersonSet)
        for name in names:
            person = personset.getByName(name)
            if person == team:
                # Do not add this team as a member of itself, please.
                continue

            if person.hasMembershipEntryFor(team):
                membership = self._getMembership(person.id, team)
                if membership.status in (approved, admin):
                    self.alreadyMembers.append(person)
                else:
                    team.setMembershipStatus(person, approved,
                                             reviewer=self.user)
                    self.addedMembers.append(person)
            else:
                team.addMember(person, approved, reviewer=self.user)
                self.addedMembers.append(person)

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
        membership = TeamMembership.selectBy(personID=personID, teamID=teamID)
        assert membership.count() == 1
        return membership[0]

    def authorizeProposed(self, personID, team):
        membership = self._getMembership(personID, team.id)
        membership.status = int(TeamMembershipStatus.APPROVED)

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
        membership.status = int(TeamMembershipStatus.ADMIN)

    def revokeAdminiRole(self, personID, team):
        membership = self._getMembership(personID, team.id)
        membership.role = int(TeamMembershipRole.MEMBER)



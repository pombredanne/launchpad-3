# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TeamMembershipSubsetNavigation',
    'TeamMembersView',
    'ProposedTeamMembersEditView',
    'AddTeamMemberView',
    'TeamMembershipEditView',
]

import pytz
import datetime

from zope.app.form.browser.add import AddView
from zope.component import getUtility
from zope.i18nmessageid import MessageIDFactory

from canonical.lp.dbschema import TeamMembershipStatus
from canonical.database.sqlbase import flush_database_updates

from canonical.launchpad import _
from canonical.launchpad.webapp import Navigation
from canonical.launchpad.interfaces import (
    IPersonSet, ILaunchBag, ITeamMembershipSet, ITeamMembershipSubset,
    ILaunchpadCelebrities)


class TeamMembershipSubsetNavigation(Navigation):

    usedfor = ITeamMembershipSubset

    def traverse(self, name):
        return self.context.getByPersonName(name)


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
        team = self.context.team
        approved = TeamMembershipStatus.APPROVED
        admin = TeamMembershipStatus.ADMIN

        newmember = data['newmember']
        # If we get to this point with the member being the team itself,
        # it means the ValidTeamMemberVocabulary is broken.
        assert newmember != team, newmember

        if newmember in team.activemembers:
            self.alreadyMember = newmember
            return

        expires = team.defaultexpirationdate
        if newmember.hasMembershipEntryFor(team):
            team.setMembershipStatus(newmember, approved, expires,
                                     reviewer=self.user)
        else:
            team.addMember(newmember, approved, reviewer=self.user)

        self.addedMember = newmember


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

    def allowChangeAdmin(self):
        return self.userIsTeamOwnerOrLPAdmin() or self.isAdmin()

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

    def isDeclined(self):
        return self.context.status == TeamMembershipStatus.DECLINED

    def isExpired(self):
        return self.context.status == TeamMembershipStatus.EXPIRED

    def isDeactivated(self):
        return self.context.status == TeamMembershipStatus.DEACTIVATED

    def adminIsSelected(self):
        """Whether the admin radiobutton should be selected or not"""
        request_admin = self.request.get('admin')
        if request_admin:
            return request_admin == 'yes'
        return self.isAdmin()

    def expiresIsSelected(self):
        """Whether the expires radiobutton should be selected or not"""
        request_expires = self.request.get('expires')
        if request_expires:
            return request_expires == 'date'
        if self.isExpired():
            # Always return false when expired, because there's another
            # radiobutton in that situation.
            return False
        return self.membershipExpires()

    def neverExpiresIsSelected(self):
        """Whether the expires radiobutton should be selected or not"""
        request_expires = self.request.get('expires')
        if request_expires:
            return request_expires == 'never'
        if self.isExpired():
            # Always return false when expired, because there's another
            # radiobutton in that situation.
            return False
        return not self.membershipExpires()

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

    def processForm(self):
        if self.request.method != 'POST':
            return

        if self.request.form.get('editactive'):
            self.processActiveMember()
        elif self.request.form.get('editproposed'):
            self.processProposedMember()
        elif self.request.form.get('editinactive'):
            self.processInactiveMember()

    def processActiveMember(self):
        assert self.context.status in (TeamMembershipStatus.ADMIN,
                                       TeamMembershipStatus.APPROVED)

        if self.request.form.get('editactive') == 'Deactivate':
            team = self.context.team
            member = self.context.person
            deactivated = TeamMembershipStatus.DEACTIVATED
            comment = self.request.form.get('comment')
            # XXX: should we not get the expiry date set in the form?
            #   -- kiko, 2005-10-10
            expires = self.context.dateexpires
            team.setMembershipStatus(member, deactivated, expires,
                                     reviewer=self.user, comment=comment)
            self.request.response.redirect('../')
            return

        # XXX: salgado, 2005-03-15: I would like to just write this as 
        # "status = self.context.status", but it doesn't work because
        # self.context.status is security proxied.
        status = TeamMembershipStatus.items[self.context.status.value]

        if (self.context.status == TeamMembershipStatus.ADMIN
            and self.request.form.get('admin') == 'no'):
            status = TeamMembershipStatus.APPROVED
        elif (self.context.status == TeamMembershipStatus.APPROVED
              and self.userIsTeamOwnerOrLPAdmin()
              and self.request.form.get('admin') == 'yes'):
            # XXX: salgado, 2005-03-15: This is a hack to make sure only
            # the teamowner can promote a given member to admin, while
            # we don't have a specific permission setup for this.
            status = TeamMembershipStatus.ADMIN
        else:
            # A form reload or race happened, but it's harmless
            pass

        if self._setMembershipData(status):
            self.request.response.redirect('../')

    def processProposedMember(self):
        assert self.context.status == TeamMembershipStatus.PROPOSED

        action = self.request.form.get('editproposed')
        if action == 'Decline':
            status = TeamMembershipStatus.DECLINED
        else:
            status = TeamMembershipStatus.APPROVED
        if self._setMembershipData(status):
            self.request.response.redirect('../')

    def processInactiveMember(self):
        assert self.context.status in (TeamMembershipStatus.EXPIRED,
                                       TeamMembershipStatus.DEACTIVATED)

        if self._setMembershipData(TeamMembershipStatus.APPROVED):
            self.request.response.redirect('../')

    def dateChooserForExpiredMembers(self):
        expires = self.context.team.defaultrenewedexpirationdate
        return self._buildDateChooser(expires)

    def dateChooserForProposedMembers(self):
        expires = self.context.team.defaultexpirationdate
        return self._buildDateChooser(expires)

    def dateChooserWithCurrentExpirationSelected(self):
        return self._buildDateChooser(self.context.dateexpires)

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

        if 0 in (year, month, day):
            raise ValueError("incomplete date provided.")

        return datetime.datetime(year, month, day, tzinfo=pytz.timezone('UTC'))

    def _setMembershipData(self, status):
        """Set all data specified on the form, for this TeamMembership.

        Get all data from the form, together with the given status and set
        them for this TeamMembership object.

        Returns True if we successfully set the data, False otherwise.
        Callsites should not commit the transaction if we return False.
        """
        team = self.context.team
        member = self.context.person
        comment = self.request.form.get('comment')
        try:
            expires = self._getExpirationDate()
        except ValueError, err:
            self.errormessage = 'Expiration date: %s' % err
            return False

        team.setMembershipStatus(member, status, expires,
                                 reviewer=self.user, comment=comment)
        return True

    # XXX: salgado, 2005-03-15: This will be replaced as soon as we have
    # browser:form.
    def _buildDateChooser(self, selected=None):
        # XXX: get form values and use them as the selected value
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
        for year in range(datetime.datetime.utcnow().year, max_year):
            if selected and year == selected.year:
                html += '<option selected value="%d">%d</option>' % (year, year)
            else:
                html += '<option value="%d">%d</option>' % (year, year)
        html += '</select>'

        return html


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



# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TeamMembershipEditView',
    'TeamMembershipSHP',
    ]

import pytz
import datetime

from zope.component import getUtility

from canonical.launchpad import _
from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadCelebrities, TeamMembershipStatus,
    UnexpectedFormData)
from canonical.launchpad.browser.launchpad import (
    StructuralHeaderPresentation)


class TeamMembershipSHP(StructuralHeaderPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.team.title


class TeamMembershipEditView:

    monthnames = {1: 'January', 2: 'February', 3: 'March', 4: 'April',
                  5: 'May', 6: 'June', 7: 'July', 8: 'August', 9: 'September',
                  10: 'October', 11: 'November', 12: 'December'}

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ""

    #
    # Boolean helpers
    #

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
        this membership.

        Team administrators can't change the expiration date of their own
        membership.
        """
        return self.context.canChangeExpirationDate(self.user)

    def membershipExpires(self):
        """Return True if this membership is scheduled to expire one day."""
        if self.context.dateexpires is None:
            return False
        else:
            return True

    #
    # Form post handlers and helpers
    #

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
        # This method checks the current status to ensure that we don't
        # crash because of users reposting a form.
        form = self.request.form
        context = self.context
        if form.get('deactivate'):
            if self.context.status == TeamMembershipStatus.DEACTIVATED:
                # This branch and redirect is necessary because
                # TeamMembership.setStatus() does not allow us to set an
                # already-deactivated account to deactivated, causing
                # double form posts to crash there. We instead manually
                # ensure that the double-post is harmless.
                self.request.response.redirect(
                    '%s/+members' % canonical_url(context.team))
                return
            new_status = TeamMembershipStatus.DEACTIVATED
        elif form.get('change'):
            if (form.get('admin') == "no" and
                context.status == TeamMembershipStatus.ADMIN):
                new_status = TeamMembershipStatus.APPROVED
            elif (form.get('admin') == "yes" and
                  context.status == TeamMembershipStatus.APPROVED
                  # XXX: salgado 2005-03-15: The clause below is a hack
                  # to make sure only the teamowner can promote a given
                  # member to admin, while we don't have a specific
                  # permission setup for this.
                  and self.userIsTeamOwnerOrLPAdmin()):
                new_status = TeamMembershipStatus.ADMIN
            else:
                # No status change will happen
                new_status = self.context.status
        else:
            raise UnexpectedFormData(
                "None of the expected actions were found.")

        if self._setMembershipData(new_status):
            self.request.response.redirect(
                '%s/+members' % canonical_url(context.team))

    def processProposedMember(self):
        if self.context.status != TeamMembershipStatus.PROPOSED:
            # Catch a double-form-post.
            self.errormessage = _(
                'The membership request for %s has already been processed.' %
                    self.context.person.displayname)
            return

        assert self.context.status == TeamMembershipStatus.PROPOSED

        action = self.request.form.get('editproposed')
        if self.request.form.get('decline'):
            status = TeamMembershipStatus.DECLINED
        elif self.request.form.get('approve'):
            status = TeamMembershipStatus.APPROVED
        else:
            raise UnexpectedFormData(
                "None of the expected actions were found.")
        if self._setMembershipData(status):
            self.request.response.redirect(
                '%s/+members' % canonical_url(self.context.team))

    def processInactiveMember(self):
        if self.context.status not in (TeamMembershipStatus.EXPIRED,
                                       TeamMembershipStatus.DEACTIVATED):
            # Catch a double-form-post.
            self.errormessage = _(
                'The membership request for %s has already been processed.' %
                    self.context.person.displayname)
            return

        if self._setMembershipData(TeamMembershipStatus.APPROVED):
            self.request.response.redirect(
                '%s/+members' % canonical_url(self.context.team))

    def _setMembershipData(self, status):
        """Set all data specified on the form, for this TeamMembership.

        Get all data from the form, together with the given status and set
        them for this TeamMembership object.

        Returns True if we successfully set the data, False otherwise.
        Callsites should not commit the transaction if we return False.
        """
        if self.canChangeExpirationDate():
            if self.request.form.get('expires') == 'never':
                expires = None
            else:
                try:
                    expires = self._getExpirationDate()
                except ValueError, err:
                    self.errormessage = (
                        'Invalid expiration: %s. '
                        'Please fix this and resubmit your changes.' % err)
                    return False
        else:
            expires = self.context.dateexpires

        self.context.setExpirationDate(expires, self.user)
        self.context.setStatus(
            status, self.user, self.request.form_ng.getOne('comment'))
        return True

    def _getExpirationDate(self):
        """Return a datetime with the expiration date selected on the form.

        Raises ValueError if the date selected is invalid. The use of
        that exception is unusual but allows us to present a consistent
        API to the caller, who needs to check only for that specific
        exception.
        """
        year = int(self.request.form.get('year'))
        month = int(self.request.form.get('month'))
        day = int(self.request.form.get('day'))

        if 0 in (year, month, day):
            raise ValueError('incomplete date provided')

        expires = datetime.datetime(year, month, day,
                                    tzinfo=pytz.timezone('UTC'))

        now = datetime.datetime.now(pytz.timezone('UTC'))
        if expires <= now:
            raise ValueError('date provided is in the past')

        return expires

    #
    # Helper methods for widgets and processing
    #

    def dateChooserForExpiredMembers(self):
        expires = self.context.team.defaultrenewedexpirationdate
        return self._buildDateChooser(expires)

    def dateChooserForProposedMembers(self):
        expires = self.context.team.defaultexpirationdate
        return self._buildDateChooser(expires)

    def dateChooserWithCurrentExpirationSelected(self):
        return self._buildDateChooser(self.context.dateexpires)

    # XXX: salgado 2005-03-15: This will be replaced as soon as we have
    # browser:form.
    def _buildDateChooser(self, selected=None):
        # Get form values and use them as the selected value.
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

        # XXX: salgado 2005-03-16: We need to define it somewhere else, but
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


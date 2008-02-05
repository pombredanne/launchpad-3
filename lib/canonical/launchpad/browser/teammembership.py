# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'TeamMembershipEditView',
    'TeamMembershipSHP',
    ]

import pytz
from datetime import datetime

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import InputErrors
from zope.component import getUtility
from zope.formlib import form
from zope.schema import Date

from canonical.launchpad import _
from canonical.launchpad.webapp import canonical_url

from canonical.launchpad.interfaces import (
    ILaunchBag, ILaunchpadCelebrities, TeamMembershipStatus,
    UnexpectedFormData)
from canonical.launchpad.browser.launchpad import (
    StructuralHeaderPresentation)

from canonical.widgets import DateWidget


class TeamMembershipSHP(StructuralHeaderPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.team.title


class TeamMembershipEditView:

    def __init__(self, context, request):
        self.context = context
        self.request = request
        self.user = getUtility(ILaunchBag).user
        self.errormessage = ""
        self.prefix = 'membership'
        self.max_year = 2050
        fields = form.Fields(Date(
            __name__='expirationdate', title=_('Expiration date')))
        expiration_field = fields['expirationdate']
        expiration_field.custom_widget = CustomWidgetFactory(DateWidget)
        expires = self.context.dateexpires
        UTC = pytz.timezone('UTC') 
        if self.isExpired():
            # For expired members, we will present the team's default
            # renewal date.
            expires = self.context.team.defaultrenewedexpirationdate
        if self.isDeactivated():
            # For members who were deactivated, we present by default
            # their original expiration date, or, if that has passed, or
            # never set, the team's default renewal date.
            if expires is None or expires < datetime.now(UTC):
                expires = self.context.team.defaultrenewedexpirationdate
        if expires is not None:
            # We get a datetime from the database, but we want to use a
            # datepicker so we must feed it a plain date without time.
            expires = expires.date()
        data = {'expirationdate': expires}
        self.widgets = form.setUpWidgets(
            fields, self.prefix, context, request, ignore_request=False,
            data=data)
        self.expiration_widget = self.widgets['expirationdate']
        # Set the acceptable date range for expiration.
        self.expiration_widget.from_date = datetime.now(UTC).date()
        # Disable the date widget if there is no current or required
        # expiration
        if not expires:
            self.expiration_widget.disabled = True

    # Boolean helpers
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
        """Whether the admin radiobutton should be selected."""
        request_admin = self.request.get('admin')
        if request_admin == 'yes':
            return 'checked'
        if self.isAdmin():
            return 'checked'
        return ''

    def adminIsNotSelected(self):
        """Whether the not-admin radiobutton should be selected."""
        if self.adminIsSelected() != 'checked':
            return 'checked'
        return ''

    def expiresIsSelected(self):
        """Whether the expiration date radiobutton should be selected."""
        request_expires = self.request.get('expires')
        if request_expires == 'date':
            return 'checked'
        if self.isExpired():
            # Never checked when expired, because there's another
            # radiobutton in that situation.
            return ''
        if self.membershipExpires():
            return 'checked'
        return ''

    def neverExpiresIsSelected(self):
        """Whether the never-expires radiobutton should be selected."""
        request_expires = self.request.get('expires')
        if request_expires == 'never':
            return 'checked'
        if self.isExpired():
            # Never checked when expired, because there's another
            # radiobutton in that situation.
            return ''
        if not self.membershipExpires():
            return 'checked'
        return ''

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

    @property
    def date_picker_trigger(self):
        """JavaScript function call to trigger the date picker."""
        return """pickDate('membership.expirationdate', %s);
         document.getElementById('membership.expirationdate').disabled=false;
         """ % (self.expiration_widget.daterange)

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
                        'Invalid expiration: %s' % err)
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
        expires = None
        try:
            expires = self.expiration_widget.getInputValue()
        except InputErrors, value:
            # Handle conversion errors. We have to do this explicitly here
            # because we are not using the full form machinery which would
            # put the relevant error message into the field error. We are
            # mixing the zope3 widget stuff with a hand-crafted form
            # processor, so we need to trap this manually.
            raise ValueError(value.doc())
        if expires is None:
            return None

        # We used a date picker, so we have a date. What we want is a
        # datetime in UTC
        UTC = pytz.timezone('UTC')
        expires = datetime(expires.year, expires.month, expires.day,
                           tzinfo=UTC)
        return expires


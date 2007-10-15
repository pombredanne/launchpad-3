# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes related to bug nominations."""

__metaclass__ = type

__all__ = [
    'BugNominationContextMenu',
    'BugNominationView',
    'BugNominationEditView',
    'BugNominationTableRowView']

import datetime

import pytz

from zope.component import getUtility
from zope.publisher.interfaces import NotFound

from canonical.launchpad import _
from canonical.launchpad.browser import BugContextMenu
from canonical.launchpad.interfaces import (
    ICveSet, ILaunchBag, IBug, IBugNomination, IBugNominationForm,
    INullBugTask)

from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, LaunchpadFormView, custom_widget, action)
from canonical.launchpad.webapp.authorization import check_permission

from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget

class BugNominationView(LaunchpadFormView):

    schema = IBugNominationForm
    initial_focus_widget = None
    custom_widget('nominatable_serieses', LabeledMultiCheckBoxWidget)

    def __init__(self, context, request):
        self.current_bugtask = context
        LaunchpadFormView.__init__(self, context, request)

    def initialize(self):
        if INullBugTask.providedBy(self.current_bugtask):
            # It shouldn't be possible to nominate a bug that hasn't
            # been reported yet.
            raise NotFound(self.current_bugtask, '+nominate', self.request)
        LaunchpadFormView.initialize(self)

    @property
    def label(self):
        """Return a nomination or targeting label.

        The label returned depends on the user's privileges.
        """
        if self.userIsReleaseManager():
            return "Target bug #%d to series" % self.context.bug.id
        else:
            return "Nominate bug #%d for series" % self.context.bug.id

    def userIsReleaseManager(self):
        """Does the current user have release management privileges?"""
        current_bugtask = getUtility(ILaunchBag).bugtask
        return check_permission(
            "launchpad.Driver", current_bugtask.target)

    def userCanChangeDriver(self):
        """Can the current user set the release management team?"""
        return check_permission(
            "launchpad.Edit", self.getReleaseContext())

    def getReleaseManager(self):
        """Return the IPerson or ITeam that does release management."""
        # XXX: Brad Bollenbach 2006-10-31:
        # Ignoring the "drivers" attribute for now, which includes the
        # project-wide driver for upstreams because I'm guessing it's
        # hardly used, and would make displaying release managers a
        # little harder.
        return self.getReleaseContext().driver

    def getReleaseContext(self):
        """Get the distribution or product for release management."""
        launchbag = getUtility(ILaunchBag)
        return launchbag.product or launchbag.distribution

    @action(_("Submit"), name="submit")
    def nominate(self, action, data):
        """Nominate bug for series."""
        serieses = data["nominatable_serieses"]
        nominated_serieses = []
        approved_nominations = []

        for series in serieses:
            nomination = self.context.bug.addNomination(
                target=series, owner=self.user)

            # If the user has the permission to approve the nomination,
            # then nomination was approved automatically.
            if nomination.isApproved():
                approved_nominations.append(
                    nomination.target.bugtargetdisplayname)
            else:
                nominated_serieses.append(series.bugtargetdisplayname)

        if approved_nominations:
            self.request.response.addNotification(
                "Targeted bug to: %s" %
                ", ".join(approved_nominations))
        if nominated_serieses:
            self.request.response.addNotification(
                "Added nominations for: %s" %
                ", ".join(nominated_serieses))

    @property
    def next_url(self):
        return canonical_url(getUtility(ILaunchBag).bugtask)


class BugNominationTableRowView(LaunchpadView):
    """Browser view class for rendering a nomination table row."""
    def getNominationPerson(self):
        """Return the IPerson associated with this nomination.

        Return the "decider" (the person who approved or declined the
        nomination), if there is one, otherwise return the owner.
        """
        return self.context.decider or self.context.owner

    def getNominationEditLink(self):
        """Return a link to the nomination edit form."""
        return (
            "%s/nominations/%d/+editstatus" % (
                canonical_url(getUtility(ILaunchBag).bugtask),
                self.context.id))

    def getApproveDeclineLinkText(self):
        """Return a string used for the approve/decline form expander link."""
        if self.context.isProposed():
            return "approve/decline"
        elif self.context.isDeclined():
            return "approve"
        else:
            assert (
                "Expected nomination to be Proposed or Declined. "
                "Got status: %s" % self.context.status.title)

    def getNominationDurationSinceCreatedOrDecided(self):
        """Return a duration since this nomination was created or decided.

        So if the nomination is currently Proposed, the duration will be from
        date_created to now, and if the nomination is Approved/Declined, the
        duration will be from date_decided until now.

        This allows us to present a human-readable version of how long ago
        the nomination was created or approved/declined.
        """
        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)
        bugnomination = self.context

        if bugnomination.date_decided:
            return now - bugnomination.date_decided

        return now - bugnomination.date_created

    def userCanMakeDecisionForNomination(self):
        """Can the user approve/decline this nomination?"""
        return check_permission("launchpad.Driver", self.context)

    def displayNominationEditLinks(self):
        """Return true if the Nomination edit links should be shown."""
        return self.request.getNearest(ICveSet) == (None, None)


class BugNominationEditView(LaunchpadView):
    """Browser view class for approving and declining nominations."""

    def __init__(self, context, request):
        LaunchpadView.__init__(self, context, request)
        self.current_bugtask = getUtility(ILaunchBag).bugtask

    def getFormAction(self):
        """Get the string used as the form action."""
        return (
            "%s/nominations/%d/+edit-form" % (
                canonical_url(self.current_bugtask), self.context.id))

    def processNominationDecision(self):
        """Process the decision, Approve or Decline, made on this nomination."""
        form = self.request.form
        approve_nomination = form.get("approve")
        decline_nomination = form.get("decline")

        if not (approve_nomination or decline_nomination):
            return

        if approve_nomination:
            self.context.approve(self.user)
            self.request.response.addNotification(
                "Approved nomination for %s" %
                    self.context.target.bugtargetdisplayname)
        elif decline_nomination:
            self.context.decline(self.user)
            self.request.response.addNotification(
                "Declined nomination for %s" %
                    self.context.target.bugtargetdisplayname)

        self.request.response.redirect(
            canonical_url(getUtility(ILaunchBag).bugtask))

    def shouldShowApproveButton(self):
        """Should the approve button be shown?"""
        return self.context.isProposed() or self.context.isDeclined()

    def shouldShowDeclineButton(self):
        """Should the decline button be shown?"""
        return self.context.isProposed()

    def getCurrentBugTaskURL(self):
        """Return the URL of the current bugtask."""
        return canonical_url(getUtility(ILaunchBag).bugtask)


class BugNominationContextMenu(BugContextMenu):
    usedfor = IBugNomination

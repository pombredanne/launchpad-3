# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Browser view classes related to bug nominations."""

__metaclass__ = type

__all__ = [
    'BugNominationContextMenu',
    'BugNominationView',
    'BugNominationEditView',
    'BugNominationTableRowView']

import datetime
from operator import attrgetter

import pytz

from zope.app.form import CustomWidgetFactory
from zope.app.form.interfaces import IInputWidget
from zope.app.form.utility import setUpWidget
from zope.component import getUtility
from zope.schema import Choice
from zope.schema.vocabulary import SimpleTerm, SimpleVocabulary

from canonical.lp import dbschema
from canonical.launchpad import helpers, _
from canonical.launchpad.browser import BugContextMenu
from canonical.launchpad.interfaces import (
    ILaunchBag, IBug, IDistribution, IBugNomination, IBugNominationForm)
from canonical.launchpad.webapp import (
    canonical_url, LaunchpadView, LaunchpadFormView, custom_widget, action)
from canonical.widgets.itemswidgets import LabeledMultiCheckBoxWidget

class BugNominationView(LaunchpadFormView):

    schema = IBugNominationForm
    initial_focus_widget = None
    custom_widget('nominatable_releases', LabeledMultiCheckBoxWidget)

    def __init__(self, context, request):
        LaunchpadFormView.__init__(self, IBug(context), request)

    @property
    def label(self):
        """Return a nomination or targeting label.

        The label returned depends on the user's privileges.
        """
        if self.userIsReleaseManager():
            return "Target bug #%d to releases" % self.context.id
        else:
            return "Nominate bug #%d for releases" % self.context.id

    def userIsReleaseManager(self):
        """Does the current user have release management privileges?"""
        current_bugtask = getUtility(ILaunchBag).bugtask
        return helpers.check_permission(
            "launchpad.Driver", current_bugtask.target)

    def userCanChangeDriver(self):
        """Can the current user set the release management team?"""
        return helpers.check_permission(
            "launchpad.Edit", self.getReleaseContext())

    def getReleaseManager(self):
        """Return the IPerson or ITeam that does release management."""
        # XXX: Ignoring the "drivers" attribute for now, which includes the
        # project-wide driver for upstreams because I'm guessing it's
        # hardly used, and would make displaying release managers a
        # little harder. -- Brad Bollenbach, 2006-10-31
        return self.getReleaseContext().driver

    def getReleaseContext(self):
        """Get the distribution or product for release management."""
        launchbag = getUtility(ILaunchBag)
        return launchbag.product or launchbag.distribution

    @action(_("Submit"), name="submit")
    def nominate(self, action, data):
        """Nominate distro releases or product series for this bug."""
        releases = data["nominatable_releases"]
        nominated_releases = []
        approved_nominations = []

        for release in releases:
            nomination = self.context.addNomination(
                target=release, owner=self.user)

            # If the user has the permission to approve or decline the
            # nomination, then approve the nomination right now.
            if helpers.check_permission("launchpad.Driver", nomination):
                nomination.approve(self.user)
                approved_nominations.append(nomination.target.bugtargetname)
            else:
                nominated_releases.append(release.bugtargetname)

        if approved_nominations:
            self.request.response.addNotification(
                "Targeted bug to: %s" %
                ", ".join(approved_nominations))
        if nominated_releases:
            self.request.response.addNotification(
                "Added nominations for: %s" %
                ", ".join(nominated_releases))

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
        return helpers.check_permission("launchpad.Driver", self.context)


class BugNominationEditView(LaunchpadView):
    """Browser view class for approving and declining nominations."""

    def getFormAction(self):
        """Get the string used as the form action."""
        current_bugtask = getUtility(ILaunchBag).bugtask
        return (
            "%s/nominations/%d/+edit-form" % (
                canonical_url(current_bugtask), self.context.id))

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
                "Approved nomination for %s" % self.context.target.bugtargetname)
        elif decline_nomination:
            self.context.decline(self.user)
            self.request.response.addNotification(
                "Declined nomination for %s" % self.context.target.bugtargetname)

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

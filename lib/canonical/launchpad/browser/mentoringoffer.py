# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Mentorship views."""

__metaclass__ = type

__all__ = [
    'CanBeMentoredView',
    'HasMentoringOffersView',
    'MentoringOfferSetFacets',
    'MentoringOfferSetOverviewMenu',
    'MentoringOfferSetSOP',
    'MentoringOfferSetView',
    'MentoringOfferView',
    'RetractMentoringOfferView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad import _

from canonical.launchpad.interfaces import (
    IBug,
    IBugTask,
    IMentoringOffer,
    IMentoringOfferSet,
    ILaunchBag,
    )
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation,
    StandardLaunchpadFacets, ApplicationMenu, enabled_with_permission,
    LaunchpadView, LaunchpadFormView, action)
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.webapp.batching import BatchNavigator
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation


class MentoringOfferSetFacets(StandardLaunchpadFacets):

    usedfor = IMentoringOfferSet

    enable_only = ['overview']


class MentoringOfferSetOverviewMenu(ApplicationMenu):

    usedfor = IMentoringOfferSet
    facet = 'overview'
    links = ['current', 'successful']

    def current(self):
        text = 'Current offers'
        return Link('+mentoring', text, icon='info')

    def successful(self):
        text = 'Recent successes'
        return Link('+success', text, icon='info')


class MentoringOfferSetSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.title

    def listChildren(self, num):
        return []

    def listAltChildren(self, num):
        return None


class CanBeMentoredView:
    """Used as a mixin on any view for something that can be mentored."""

    def userCanMentor(self):
        """Is the user able to offer mentorship?"""
        return self.context.canMentor(self.user)

    def userIsMentor(self):
        """Is the user offering mentorship on this bug?"""
        return self.context.isMentor(self.user)


class MentoringOfferView(LaunchpadFormView):
    """This view will be used for objects that can be mentored, that
    includes IBug, IBugTask and ISpecification
    """

    schema = IMentoringOffer
    label = "Offer to mentor this work"
    field_names = ['team',]
    mentoring_offer = None

    def validate(self, data):
        team = data.get('team')
        if not self.user.inTeam(team):
            # person must be a participant in team
            self.setFieldError('team',
                'You can only offer mentorship for teams in which you are '
                'a member.')

    @action(_('Offer Mentoring'), name='add')
    def add_action(self, action, data):
        user = self.user
        team = data.get('team')
        self.mentoring_offer = self.context.offerMentoring(user, team)
        self.request.response.addInfoNotification(
            'Thank you for this mentorship offer.')

    @property
    def next_url(self):
        assert self.mentoring_offer is not None, 'No mentorship recorded'
        return canonical_url(self.context)


class RetractMentoringOfferView(LaunchpadFormView, CanBeMentoredView):
    """This view is used to retract the offer of mentoring."""

    schema = IMentoringOffer
    label = "Retract your offer of mentorship"
    field_names = []

    @action(_('Retract Mentoring'), name='retract')
    def add_action(self, action, data):
        user = self.user
        if self.context.isMentor(user):
            self.context.retractMentoring(user)
            self.request.response.addInfoNotification(
                'You are no longer offering mentoring on this work.')

    @property
    def next_url(self):
        return canonical_url(self.context)


class HasMentoringOffersView(LaunchpadView):

    def batched_offers(self):
        return BatchNavigator(self.context.mentoring_offers, self.request)


class MentoringOfferSetView(HasMentoringOffersView):

    def batched_successes(self):
        return BatchNavigator(self.context.recent_completed_mentorships,
                              self.request)



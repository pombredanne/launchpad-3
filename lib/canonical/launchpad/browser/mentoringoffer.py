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
    'MentoringOfferAddView',
    'MentoringOfferRetractView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad import _

from canonical.launchpad.interfaces import (
    IBug,
    IBugTask,
    IDistribution,
    IMentoringOffer,
    IMentoringOfferSet,
    ILaunchBag,
    IPerson,
    IProduct,
    IProject,
    ISpecification,
    ITeam,
    PersonVisibility,
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


class MentoringOfferAddView(LaunchpadFormView):
    """This view will be used for objects that can be mentored, that
    includes IBug, IBugTask and ISpecification
    """

    schema = IMentoringOffer
    label = "Offer to mentor this work"
    field_names = ['team', 'subscription_request']
    mentoring_offer = None

    def validate(self, data):
        team = data.get('team')
        if (not self.user.inTeam(team)
            or not (team.visibility is None
                    or team.visibility == PersonVisibility.PUBLIC)):
            # person must be a participant in team
            self.setFieldError('team',
                'You can only offer mentorship for public teams in '
                'which you are a member.')

    @action(_('Offer Mentoring'), name='add')
    def add_action(self, action, data):
        user = self.user
        team = data.get('team')
        self.mentoring_offer = self.context.offerMentoring(user, team)
        subscribe = data.get('subscription_request')
        if subscribe:
            if not self.context.isSubscribed(user):
                # XXX Tom Berger 2007-07-15: IBugTask
                # and ISpecification (and everything
                # else you can subscribe to) should
                # implement a common interface and
                # have the same signature for their
                # subscribe method.
                if IBugTask.providedBy(self.context):
                    self.context.subscribe(user)
                elif ISpecification.providedBy(self.context):
                    self.context.subscribe(user, user, False)
                else:
                    raise AssertionError, (
                        '%s does not provide IBugTask or ISpecification' %
                        self.context)
                self.request.response.addInfoNotification(
                    'You have subscribed to this item.')
        self.request.response.addInfoNotification(
            'Thank you for this mentorship offer.')

    @property
    def next_url(self):
        assert self.mentoring_offer is not None, 'No mentorship recorded'
        return canonical_url(self.context)


class MentoringOfferRetractView(LaunchpadFormView, CanBeMentoredView):
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

    # these flags determine which columns will be displayed. In the
    # initialise() method, some columns may be disabled based on the type of
    # context (person, team, project, mentorship manager)
    show_person = True
    show_team = True
    show_date = True
    show_work = True

    # these flags govern some of the content of the spec page, which allows
    # us to vary the text flow slightly without creating large numbers of
    # template fragments
    is_person = False
    is_team = False
    is_pillar = False
    is_manager = False

    def initialize(self):
        if IPerson.providedBy(self.context):
            if self.context.teamowner is None:
                self.is_person = True
                self.show_person = False
            else:
                self.is_team = True
                self.show_team = False
        elif (IDistribution.providedBy(self.context) or
              IProduct.providedBy(self.context) or
              IProject.providedBy(self.context)):
            self.is_pillar = True
        elif IMentoringOfferSet.providedBy(self.context):
            self.is_manager = True
        else:
            raise AssertionError, 'Unknown mentorship listing site'
        mapping = {'name': self.context.displayname}
        if self.is_person:
            self.title = _('Mentoring offered by $name', mapping=mapping)
        else:
            self.title = _('Offers of mentoring for $name', mapping=mapping)

    def batched_offers(self):
        if self.is_team:
            resultset = self.context.team_mentorships
        else:
            resultset = self.context.mentoring_offers
        return BatchNavigator(resultset, self.request)


class MentoringOfferSetView(HasMentoringOffersView):

    def batched_successes(self):
        return BatchNavigator(self.context.recent_completed_mentorships,
                              self.request)



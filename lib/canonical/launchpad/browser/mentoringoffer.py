# Copyright 2005 Canonical Ltd.  All rights reserved.

"""CVE views."""

__metaclass__ = type

__all__ = [
    'MentorshipManagerFacets',
    'MentorshipManagerSOP',
    'MentoringOfferView',
    'RetractMentoringOfferView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad.interfaces import (
    IBug,
    IBugTask,
    IMentoringOffer,
    IMentorshipManager,
    ILaunchBag,
    )
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation,
    StandardLaunchpadFacets)
from canonical.launchpad.webapp.generalform import GeneralFormView
from canonical.launchpad.webapp.authorization import check_permission
from canonical.launchpad.browser.launchpad import StructuralObjectPresentation


class MentorshipManagerFacets(StandardLaunchpadFacets):

    usedfor = IMentorshipManager

    enable_only = ['overview']


class MentorshipManagerSOP(StructuralObjectPresentation):

    def getIntroHeading(self):
        return None

    def getMainHeading(self):
        return self.context.title

    def listChildren(self, num):
        return []

    def listAltChildren(self, num):
        return None


class MentoringOfferView(GeneralFormView):
    """This view will be used for objects that can be mentored, that
    includes IBug and ISpecification
    """

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        if IBugTask.providedBy(context):
            # in the case of seeing this on a bug task, we treat it as a Bug
            self.current_bugtask = context
            context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, team):
        user = getUtility(ILaunchBag).user
        self.context.offerMentoring(user, team)
        return 'Thank you for this mentorship offer.'


class RetractMentoringOfferView(GeneralFormView):
    """This view is used to retract the offer of mentoring."""

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        if IBugTask.providedBy(context):
            # in the case of seeing this on a bug task, we treat it as a Bug
            self.current_bugtask = context
            context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, confirmation):
        if confirmation:
            user = getUtility(ILaunchBag).user
            self.context.retractMentoring(user)
            return 'Mentoring retracted'



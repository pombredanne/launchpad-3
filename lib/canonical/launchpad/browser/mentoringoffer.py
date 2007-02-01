# Copyright 2005 Canonical Ltd.  All rights reserved.

"""CVE views."""

__metaclass__ = type

__all__ = [
    'MentoringOfferView',
    'RetractMentoringOfferView',
    ]

from zope.component import getUtility

from canonical.launchpad.webapp.batching import BatchNavigator

from canonical.launchpad.interfaces import IMentoringOffer, ILaunchBag, IBug
from canonical.launchpad.helpers import check_permission
from canonical.launchpad.webapp import (
    canonical_url, ContextMenu, Link, GetitemNavigation)
from canonical.launchpad.webapp.generalform import GeneralFormView


class MentoringOfferView(GeneralFormView):
    """This view will be used for objects that can be mentored, that
    includes IBug and ISpecification
    """

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, team):
        user = getUtility(ILaunchBag).user
        self.context.offerMentoring(user, team)
        return 'Thank you for offering to mentor Bug #%s' % (self.context.id)


class RetractMentoringOfferView(GeneralFormView):
    """This view is used to retract the offer of mentoring."""

    def __init__(self, context, request):
        self._nextURL = canonical_url(context)
        context = IBug(context)
        GeneralFormView.__init__(self, context, request)

    def process(self, confirmation):
        if confirmation:
            user = getUtility(ILaunchBag).user
            self.context.retractMentoring(user)
            return 'Mentoring retracted for bug #%d' % (self.context.id)



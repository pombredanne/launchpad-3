# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'KarmaActionEditView',
    'KarmaActionSetNavigation',
    'KarmaContextTopContributorsView',
    ]

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.interfaces import (
    IKarmaActionSet, TOP_CONTRIBUTORS_LIMIT, IProduct, IDistribution,
    IPersonSet)
from canonical.launchpad.browser.editview import SQLObjectEditView
from canonical.launchpad.webapp import (
    LaunchpadView, Navigation, canonical_url)


class KarmaActionSetNavigation(Navigation):

    usedfor = IKarmaActionSet

    def traverse(self, name):
        return self.context.getByName(name)


class KarmaActionEditView(SQLObjectEditView):

    def changed(self):
        self.request.response.redirect(canonical_url(self.context))


class KarmaContextContributor:

    def __init__(self, person, karmavalue):
        self.person = person
        self.karmavalue = karmavalue


class KarmaContextTopContributorsView(LaunchpadView):
    """List this KarmaContext's top contributors."""

    def initialize(self):
        context = self.context
        if IProduct.providedBy(context):
            self.context_name = 'Product'
        elif IDistribution.providedBy(context):
            self.context_name = 'Distribution'
        else:
            raise AssertionError(
                "Context is not a Product nor a Distribution: %r" % context)

    def top_contributors(self, limit=TOP_CONTRIBUTORS_LIMIT):
        results = getUtility(IPersonSet).getTopContributorsForContext(
            self.context, limit=limit)
        contributors = [KarmaContextContributor(person, karmavalue)
                        for person, karmavalue in results]
        return sorted(
            contributors, key=lambda item: item.karmavalue, reverse=True)

    def top_ten_contributors(self):
        return self.top_contributors(limit=10)

    @cachedproperty
    def top_contributors_by_category(self):
        contributors_by_category = {}
        personset = getUtility(IPersonSet)
        results = personset.getTopContributorsForContextGroupedByCategory(
            self.context)
        for category, people_and_karma in results.items():
            contributors = []
            for person, karmavalue in people_and_karma:
                contributors.append(KarmaContextContributor(
                    person, karmavalue))
            contributors.sort(key=lambda item: item.karmavalue, reverse=True)
            contributors_by_category[category.title] = contributors
        return contributors_by_category

    @property
    def sorted_categories(self):
        return sorted(self.top_contributors_by_category.keys())

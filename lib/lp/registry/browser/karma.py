# Copyright 2004 Canonical Ltd

__metaclass__ = type

__all__ = [
    'KarmaActionEditView',
    'KarmaActionSetNavigation',
    'KarmaContextTopContributorsView',
    ]

from operator import attrgetter

from zope.component import getUtility

from canonical.cachedproperty import cachedproperty
from canonical.launchpad import _
from lp.registry.interfaces.karma import IKarmaAction, IKarmaActionSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.project import IProject
from lp.registry.interfaces.distribution import IDistribution
from canonical.launchpad.webapp import (
    action, canonical_url, LaunchpadEditFormView, LaunchpadView, Navigation)


TOP_CONTRIBUTORS_LIMIT = 20


class KarmaActionSetNavigation(Navigation):

    usedfor = IKarmaActionSet

    def traverse(self, name):
        return self.context.getByName(name)


class KarmaActionEditView(LaunchpadEditFormView):

    schema = IKarmaAction
    label = "Edit karma action"
    field_names = ["name", "category", "points", "title", "summary"]

    @action(_("Change"), name="change")
    def change_action(self, action, data):
        self.updateContextFromData(data)
        self.next_url = canonical_url(getUtility(IKarmaActionSet))


class KarmaContextContributor:

    def __init__(self, person, karmavalue):
        self.person = person
        self.karmavalue = karmavalue


class KarmaContextTopContributorsView(LaunchpadView):
    """List this KarmaContext's top contributors."""

    def initialize(self):
        context = self.context
        if IProduct.providedBy(context):
            self.context_name = 'Project'
        elif IDistribution.providedBy(context):
            self.context_name = 'Distribution'
        elif IProject.providedBy(context):
            self.context_name = 'Project Group'
        else:
            raise AssertionError(
                "Context is not a Product, Project or Distribution: %r"
                % context)

    def _getTopContributorsWithLimit(self, limit=None):
        results = self.context.getTopContributors(limit=limit)
        contributors = [KarmaContextContributor(person, karmavalue)
                        for person, karmavalue in results]
        return sorted(
            contributors, key=attrgetter('karmavalue'), reverse=True)

    def getTopContributors(self):
        return self._getTopContributorsWithLimit(limit=TOP_CONTRIBUTORS_LIMIT)

    def getTopFiveContributors(self):
        return self._getTopContributorsWithLimit(limit=5)

    @cachedproperty
    def top_contributors_by_category(self):
        contributors_by_category = {}
        limit = TOP_CONTRIBUTORS_LIMIT
        results = self.context.getTopContributorsGroupedByCategory(
            limit=limit)
        for category, people_and_karma in results.items():
            contributors = []
            for person, karmavalue in people_and_karma:
                contributors.append(KarmaContextContributor(
                    person, karmavalue))
            contributors.sort(key=attrgetter('karmavalue'), reverse=True)
            contributors_by_category[category.title] = contributors
        return contributors_by_category

    @property
    def sorted_categories(self):
        return sorted(self.top_contributors_by_category.keys())

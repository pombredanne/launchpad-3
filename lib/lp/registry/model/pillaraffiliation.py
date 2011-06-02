# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters to figure out affiliations between people and pillars/bugs etc.

When using a person in a given context, for example as a selection item in a
picker used to choose a bug task assignee, it is important to provide an
indication as to how that person may be affiliated with the context. Amongst
other reasons, this provides a visual cue that the correct person is being
selected for example.

The adapters herein are provided for various contexts so that for a given
person, the relevant affiliation details may be determined.

"""

__metaclass__ = type

__all__ = [
    'IHasAffiliation',
    ]

from collections import namedtuple

from zope.component import adapter
from zope.interface import (
    implements,
    Interface,
    )

from lp.bugs.interfaces.bugtask import IBugTask


class IHasAffiliation(Interface):
    """The affiliation status of a person with a context."""

    def getAffiliationBadge(person):
        """Return the badge for the type of affiliation the person has.

        The return value is a tuple: (url, alt).

        If the person has no affiliation with this object, return None.
        """

BadgeDetails = namedtuple('url', 'alt_text')

@adapter(Interface)
class PillarAffiliation(object):
    """Default affiliation adapter.

    No affiliation is returned.
    """

    implements(IHasAffiliation)

    def __init__(self, context):
        self.context = context

    def getAffiliationBadge(self, person):
        return None


# XXX: wallyworld 2011-05-24 bug=81692: TODO Work is required to determine
# exactly what is required in terms of figuring out affiliation..

@adapter(IBugTask)
class BugTaskPillarAffiliation(PillarAffiliation):
    """An affiliation adapter for bug tasks."""

    def getAffiliationBadge(self, person):
        pillar = self.context.pillar
        affiliated = person.inTeam(pillar.owner)
        if not affiliated:
            return None
        if self.context.distribution or self.context.distroseries:
            return BadgeDetails(
                "distribution-badge", "Distribution affiliation")
        if self.context.product or self.context.productseries:
            return BadgeDetails(
                "product-badge", "Product affiliation")

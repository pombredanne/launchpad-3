# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

__all__ = [
    'IHasAffiliation',
    ]

from zope.component import adapter
from zope.interface import (
    implements,
    Interface,
    )

from lp.bugs.interfaces.bugtask import IBugTask


class IHasAffiliation(Interface):
    """The affiliation status of a person with a pillar."""

    def getAffiliationBadge(person):
        """Return the badge name for the type of affiliation the person has.

        If the person has no affiliation with this object, return None.
        """


@adapter(Interface)
class PillarAffiliation(object):

    implements(IHasAffiliation)

    def __init__(self, context):
        self.context = context

    def getAffiliationBadge(self, person):
        return None


@adapter(IBugTask)
class BugTaskPillarAffiliation(PillarAffiliation):
    """An affiliation adaptor for bug tasks."""

    def getAffiliationBadge(self, person):
        return "product-badge"

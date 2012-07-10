# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestonetag model class."""

__metaclass__ = type
__all__ = [
    'MilestoneTag',
    'ProjectGroupMilestoneTag',
    ]


from storm.locals import (
    DateTime,
    Int,
    Reference,
    Unicode,
    )
from zope.component import getUtility
from zope.interface import implements

from lp.blueprints.model.specification import Specification
from lp.registry.interfaces.milestonetag import IProjectGroupMilestoneTag
from lp.registry.model.milestone import (
    Milestone,
    MilestoneData,
    )
from lp.registry.model.product import Product
from lp.services.webapp.interfaces import (
    DEFAULT_FLAVOR,
    IStoreSelector,
    MAIN_STORE,
    )


class MilestoneTag(object):
    """A tag belonging to a milestone."""

    __storm_table__ = 'milestonetag'

    id = Int(primary=True)
    milestone_id = Int(name='milestone', allow_none=False)
    milestone = Reference(milestone_id, 'milestone.id')
    tag = Unicode(allow_none=False)
    created_by_id = Int(name='created_by', allow_none=False)
    created_by = Reference(created_by_id, 'person.id')
    date_created = DateTime(allow_none=False)

    def __init__(self, milestone, tag, created_by, date_created=None):
        self.milestone_id = milestone.id
        self.tag = tag
        self.created_by_id = created_by.id
        if date_created is not None:
            self.date_created = date_created


class ProjectGroupMilestoneTag(MilestoneData):

    implements(IProjectGroupMilestoneTag)

    def __init__(self, target, tags):
        self.target = target
        # Tags is a sequence of Unicode strings.
        self.tags = tags
        self.active = True
        self.dateexpected = None

    @property
    def name(self):
        return u','.join(self.tags)

    @property
    def displayname(self):
        """See IMilestone."""
        return "%s %s" % (self.target.displayname, u", ".join(self.tags))

    @property
    def title(self):
        """See IMilestoneData."""
        return self.displayname

    @property
    def specifications(self):
        """See IMilestoneData."""
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        results = []
        for tag in self.tags:
            result = store.find(
                Specification,
                Specification.milestone == Milestone.id,
                Milestone.product == Product.id,
                Product.project == self.target,
                MilestoneTag.milestone_id == Milestone.id,
                MilestoneTag.tag == tag)
            results.append(result)
        result = results.pop()
        for i in results:
            result = result.intersection(i)
        return result

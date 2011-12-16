# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestonetag model class."""

__metaclass__ = type
__all__ = [
    'MilestoneTag',
    'ProjectGroupMilestoneTag',
    ]


from zope.interface import implements

from lp.registry.interfaces.milestonetag import IProjectGroupMilestoneTag
from lp.registry.model.milestone import MilestoneData
from storm.locals import (
    DateTime,
    Int,
    Unicode,
    Reference,
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
        self.tags = tags

    @property
    def name(self):
        return u", ".join(self.tags)

    @property
    def title(self):
        """See IMilestoneData."""
        return self.displayname

    def bugtasks(self, user):
        raise NotImplementedError()

    def specifications(self):
        raise NotImplementedError()

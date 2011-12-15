# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Milestonetag model class."""

__metaclass__ = type
__all__ = [
    'ProjectGroupMilestoneTag',
    ]


from zope.interface import implements

from lp.registry.interfaces.milestonetag import IProjectGroupMilestoneTag
from lp.registry.model.milestone import MilestoneData


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

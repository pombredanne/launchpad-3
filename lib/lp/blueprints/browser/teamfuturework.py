# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upcoming team work views."""

__metaclass__ = type

__all__ = [
    'TeamFutureWorkView',
    ]
from lp.blueprints.enums import SpecificationWorkItemStatus
from lp.services.webapp import (
    LaunchpadView,
    )


class TeamFutureWorkView(LaunchpadView):
    """XXX"""

    @property
    def label(self):
        return self.context.displayname

    @property
    def page_title(self):
        return "Upcoming work for %s." % self.label

    @property
    def page_description(self):
        return "Work for %s in the near future." % self.label

    def overall_completion(self):
        # This is actually per-milestone and not overall.
        n_complete = 0
        total = 0
        for group in self.work_item_groups:
            for item in group.items:
                total += 1
                if item.is_complete:
                    n_complete += 1
        return total, n_complete

    @property
    def upcoming_bp_count(self):
        return len([1,2,3,4])

    @property
    def upcoming_wi_count(self):
        return len([1,2,3,4,5,6,7,8,9,0])

    @property
    def work_item_groups(self):
        # Here we're returning a single list, but we want them grouped by
        # milestone.
        milestone1_groups = [
            WorkItemGroup('Foo', 'project1', 'saglado', 'High', [
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project1'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.INPROGRESS, False, False, None, 'project1'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project1')]),
            WorkItemGroup('Bar', 'project2', 'salgado', 'Normal', [
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project2'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.INPROGRESS, False, False, None, 'project2'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project2')])]
        milestone2_groups = [
            WorkItemGroup('Foo', 'project1', 'saglado', 'High', [
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project1'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.INPROGRESS, False, False, None, 'project1'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project1')]),
            WorkItemGroup('Bar', 'project2', 'salgado', 'Normal', [
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project2'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.INPROGRESS, False, False, None, 'project2'),
                    WorkItemAbstraction(None, SpecificationWorkItemStatus.TODO, False, False, None, 'project2')])]
        return [MilestoneGroup('Milestone 1', milestone1_groups), MilestoneGroup('Milestone 2', milestone2_groups)]


class MilestoneGroup:

    def __init__(self, milestone, group):
        self.milestone = milestone
        self.group = group


class WorkItemGroup:

    def __init__(self, label, target, assignee, priority, items):
        self.label = label
        self.target = target
        self.assignee = assignee
        self.priority = priority
        self.is_future = False
        # Should this be ordered by state?
        self.items = items
        self.progressbar = object()  # What should we use here?
        # In case this is a Blueprint, we may not have all work items included
        # here (because they're targeted to a different milestone or targeted
        # to somebody who's not a member of this team), so here we'd store the
        # total count of work items on this BP.
        self.total_workitems = int()


class WorkItemAbstraction:

    def __init__(self, assignee, status, is_complete, is_foreign, priority, target):
        self.assignee = assignee
        self.status = status
        self.is_complete = is_complete
        self.is_foreign = is_foreign
        self.priority = priority
        self.target = target

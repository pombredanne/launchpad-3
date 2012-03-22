# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Upcoming team work views."""

__metaclass__ = type

__all__ = [
    'TeamFutureWorkView',
    ]

from operator import (
    attrgetter,
    itemgetter,
    )

from lp.services.webapp import (
    LaunchpadView,
    )

from datetime import datetime


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
    def work_item_containers(self):
        result = getWorkItemsDueBefore(
            self.context, datetime(2050, 1, 1), self.user)
        return sorted(result.items(), key=itemgetter(0))


class WorkItemContainer:
    """A container of work items, assigned to members of a team, whose
    milestone is due on a certain date.

    This might represent a Specification with its SpecificationWorkItems or
    just a collection of BugTasks.

    In the case of SpecificationWorkItems, their milestones should have the
    same due date but they should also come from the same Specification.

    In the case of BugTasks, the only thing they will have in common is the
    due date of their milestones.

    It is the responsibility of callsites to group the BugTasks and
    SpecificationWorkItems appropriately in as many WorkItemContainer objects
    are necessary.
    """

    def __init__(self, label, target, assignee, priority, is_future=False,
                 is_foreign=False):
        self.label = label
        self.target = target
        self.assignee = assignee
        self.priority = priority
        self._items = []

        # Is this container targeted to a milestone that is farther into the
        # future than the milestone to which .items are targeted to?
        self.is_future = is_future

        # Is this container assigned to a person which is not a member of the
        # team we're dealing with here?
        self.is_foreign = is_foreign

    @property
    def items(self):
        # TODO: Sort the items by priority.
        return self._items

    @property
    def percent_done(self):
        # TODO: Implement this.
        return 0

    def append(self, item):
        self._items.append(item)


class GenericWorkItem:
    """A generic piece of work.

    This can be either a BugTask or a SpecificationWorkItem.
    """

    def __init__(self, assignee, status, priority, target, title,
                 bugtask=None, work_item=None):
        self.assignee = assignee
        self.status = status
        self.priority = priority
        self.target = target
        self.title = title

        self._bugtask = bugtask
        self._work_item = work_item

    @classmethod
    def from_bugtask(cls, bugtask):
        return cls(
            bugtask.assignee, bugtask.status, bugtask.importance,
            bugtask.target, bugtask.title, bugtask=bugtask)

    @classmethod
    def from_workitem(cls, work_item):
        assignee = work_item.assignee
        if assignee is None:
            assignee = work_item.specification.assignee
        return cls(
            assignee, work_item.status, work_item.specification.priority,
            work_item.specification.target, work_item.title,
            work_item=work_item)

    @property
    def actual_workitem(self):
        if self._work_item is not None:
            return self._work_item
        else:
            return self._bugtask

    @property
    def is_done(self):
        return self.actual_workitem.is_complete


def getWorkItemsDueBefore(team, date, user):
    """See `IPerson`."""
    workitems = team.getAssignedSpecificationWorkItemsDueBefore(date)
    # Now we need to regroup our work items by specification and by date
    # because that's how they'll end up being displayed. While we do this
    # we store all the data we need into WorkItemContainer objects because
    # that's what we want to return.
    containers_by_date = {}
    containers_by_spec = {}
    for workitem in workitems:
        spec = workitem.specification
        milestone = workitem.milestone
        if milestone is None:
            milestone = spec.milestone
        if milestone.dateexpected not in containers_by_date:
            containers_by_date[milestone.dateexpected] = []
        container = containers_by_spec.get(spec)
        if container is None:
            is_future = False
            if spec.milestoneID != milestone.id:
                is_future = True
            is_foreign = False
            if spec.assigneeID not in team.participant_ids:
                is_foreign = True
            container = WorkItemContainer(
                spec.name, spec.target, spec.assignee, spec.priority,
                is_future=is_future, is_foreign=is_foreign)
            containers_by_spec[spec] = container
            containers_by_date[milestone.dateexpected].append(container)
        container.append(GenericWorkItem.from_workitem(workitem))

    # Sort our containers by priority.
    for date in containers_by_date:
        containers_by_date[date].sort(
            key=attrgetter('priority'), reverse=True)

    bugtasks = team.getAssignedBugTasksDueBefore(date, user)
    bug_containers_by_date = {}
    # Group all bug tasks by their milestone.dateexpected.
    for task in bugtasks:
        dateexpected = task.milestone.dateexpected
        container = bug_containers_by_date.get(dateexpected)
        if container is None:
            container = WorkItemContainer(
                'Aggregated bugs', None, None, None)
            bug_containers_by_date[dateexpected] = container
            # Also append our new container to the dictionary we're going
            # to return.
            if dateexpected not in containers_by_date:
                containers_by_date[dateexpected] = []
            containers_by_date[dateexpected].append(container)
        container.append(GenericWorkItem.from_bugtask(task))

    return containers_by_date

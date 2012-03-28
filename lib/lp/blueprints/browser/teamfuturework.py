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

from lp.app.browser.tales import format_link
from lp.services.webapp import (
    canonical_url,
    LaunchpadView,
    )

from datetime import (
    datetime,
    timedelta,
)


class TeamFutureWorkView(LaunchpadView):
    """This view displays work items and bugtasks that are due within 60 days
    and are assigned to a team.
    """

    # Defines the number of days in the future to look for milestones with work
    # items and bugtasks.
    DELTA = 60

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
        n_complete = 0
        total_workitems = 0
        total_containers = 0
        for date, containers in self.work_item_containers:
            for container in containers:
                total_containers += 1
                for item in container.items:
                    total_workitems += 1
                    if item.is_done:
                        n_complete += 1
        return total_containers, total_workitems, n_complete

    @property
    def upcoming_bp_count(self):
        # XXX: don't call overall_completion from both here and
        # upcoming_wi_count!
        n_blueprints, _, _ = self.overall_completion()
        return n_blueprints

    @property
    def upcoming_wi_count(self):
        _, n_workitems, _ = self.overall_completion()
        return n_workitems

    @property
    def work_item_containers(self):
        result = getWorkItemsDueBefore(
            self.context, self.wanted_date, self.user)
        return sorted(result.items(), key=itemgetter(0))

    @property
    def wanted_date(self):
        return datetime.today() + timedelta(days=self.DELTA)

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

    def __init__(self, spec, label, target, assignee, priority,
                 is_future=False, is_foreign=False):
        self.spec = spec
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
    def display_label(self):
        label = self.label
        if self.is_foreign:
            label += ' [FOREIGN] '
        if self.is_future:
            label += ' [FUTURE] '
        return label

    @property
    def html_link(self):
        return '<a href="%s">%s</a>' % (
            canonical_url(self.spec), self.display_label)

    @property
    def assignee_link(self):
        if self.assignee is None:
            return 'Nobody'
        return format_link(self.assignee)

    @property
    def target_link(self):
        return format_link(self.target)

    @property
    def priority_title(self):
        return self.priority.title

    @property
    def items(self):
        # TODO: Sort the items by priority.
        return self._items

    @property
    def percent_done(self):
        done_items = [w for w in self._items if w.is_done]
        return 100.0 * len(done_items)/len(self._items)

    @property
    def progress_bar(self):
        # XXX: move css to stylesheet
        # TODO: round the float in the mouse over text
        return """
            <div style="background-color: #bdbdbd;" title="%s %% complete">
              <div style="width:%s%%">
                <div style="background-color: green">&nbsp;</div>
              </div>
            </div>""" % (self.percent_done, self.percent_done)

    def append(self, item):
        self._items.append(item)


class AggregatedBugsContainer(WorkItemContainer):

    def __init__(self):
        super(AggregatedBugsContainer, self).__init__(
            spec=None, label=None, target=None, assignee=None, priority=None)

    @property
    def html_link(self):
        return 'Aggregated bugs'

    @property
    def assignee_link(self):
        return 'N/A'

    @property
    def target_link(self):
        return 'N/A'

    @property
    def priority_title(self):
        return 'N/A'


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
    """Return a dict mapping dates to lists of WorkItemContainers.

    This is a grouping, by milestone due date, of all work items
    (SpecificationWorkItems/BugTasks) assigned to any member of this
    team.

    Only work items whose milestone have a due date before the given date
    are included here.
    """
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
                spec, spec.name, spec.target, spec.assignee, spec.priority,
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
            container = AggregatedBugsContainer()
            bug_containers_by_date[dateexpected] = container
            # Also append our new container to the dictionary we're going
            # to return.
            if dateexpected not in containers_by_date:
                containers_by_date[dateexpected] = []
            containers_by_date[dateexpected].append(container)
        container.append(GenericWorkItem.from_bugtask(task))

    return containers_by_date

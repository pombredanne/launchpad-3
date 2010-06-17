# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Decorated model objects used in the browser code."""

__metaclass__ = type
__all__ = [
    'DecoratedBranch',
    'DecoratedBug',
    ]


from collections import defaultdict

from canonical.cachedproperty import cachedproperty
from canonical.launchpad.webapp.authorization import check_permission
from lazr.delegates import delegates

from lp.bugs.interfaces.bug import IBug
from lp.code.interfaces.branch import BzrIdentityMixin, IBranch


class DecoratedBug:
    """Provide some additional attributes to a normal bug."""
    delegates(IBug, 'bug')

    def __init__(self, bug, branch, tasks=None):
        self.bug = bug
        self.branch = branch
        self.tasks = tasks
        if self.tasks is None:
            self.tasks = self.bug.bugtasks

    @property
    def bugtasks(self):
        return self.tasks

    @property
    def default_bugtask(self):
        return self.tasks[0]

    def getBugTask(self, target):
        # Copied from Bug.getBugTarget to avoid importing.
        for bugtask in self.bugtasks:
            if bugtask.target == target:
                return bugtask
        return None

    @property
    def bugtask(self):
        """Return the bugtask for the branch project, or the default bugtask.
        """
        return self.branch.target.getBugTask(self)


class DecoratedBranch(BzrIdentityMixin):
    """Wrap a number of the branch accessors to cache results.

    This avoids repeated db queries.
    """
    delegates(IBranch, 'branch')

    def __init__(self, branch):
        self.branch = branch

    @cachedproperty
    def linked_bugs(self):
        bugs = defaultdict(list)
        for bug, task in self.branch.getLinkedBugsAndTasks():
            bugs[bug].append(task)
        return [DecoratedBug(bug, self.branch, tasks)
                for bug, tasks in bugs.iteritems()
                if check_permission('launchpad.View', bug)]

    @property
    def displayname(self):
        return self.bzr_identity

    @cachedproperty
    def bzr_identity(self):
        return super(DecoratedBranch, self).bzr_identity

    @cachedproperty
    def is_series_branch(self):
        # True if linked to a product series or suite source package.
        return (
            len(self.associated_product_series) > 0 or
            len(self.suite_source_packages) > 0)

    def associatedProductSeries(self):
        """Override the IBranch.associatedProductSeries."""
        return self.associated_product_series

    def associatedSuiteSourcePackages(self):
        """Override the IBranch.associatedSuiteSourcePackages."""
        return self.suite_source_packages

    @cachedproperty
    def associated_product_series(self):
        return list(self.branch.associatedProductSeries())

    @cachedproperty
    def suite_source_packages(self):
        return list(self.branch.associatedSuiteSourcePackages())

    @cachedproperty
    def upgrade_pending(self):
        return self.branch.upgrade_pending

    @cachedproperty
    def subscriptions(self):
        return list(self.branch.subscriptions)

    def hasSubscription(self, user):
        for sub in self.subscriptions:
            if sub.person == user:
                return True
        return False

    @cachedproperty
    def latest_revisions(self):
        return list(self.branch.latest_revisions())



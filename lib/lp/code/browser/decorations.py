# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Decorated model objects used in the browser code."""

__metaclass__ = type
__all__ = [
    'DecoratedBranch',
    'DecoratedBug',
    ]


from collections import defaultdict

from lazr.delegates import delegates

from canonical.launchpad.webapp.authorization import check_permission
from lp.bugs.interfaces.bug import IBug
from lp.code.interfaces.branch import (
    BzrIdentityMixin,
    IBranch,
    )
from lp.services.propertycache import cachedproperty


class DecoratedBug:
    """Provide some cached attributes to a normal bug.

    We provide cached properties where sensible, and override default bug
    behaviour where the cached properties can be used to avoid extra database
    queries.
    """
    delegates(IBug, 'bug')

    def __init__(self, bug, branch, tasks=None):
        self.bug = bug
        self.branch = branch
        if tasks is None:
            tasks = self.bug.bugtasks
        self.tasks = tasks

    @property
    def bugtasks(self):
        """This needs to be a property rather than an attribute.

        If we try to assign to self.bugtasks, the lazr.delegates things we are
        trying to assign to the property of the bug.
        """
        return self.tasks

    @property
    def default_bugtask(self):
        """Use the first bugtask.

        Use the cached tasks as calling default_bugtask on the bug object
        causes a DB query.
        """
        return self.bugtasks[0]

    def getBugTask(self, target):
        """Get the bugtask for a specific target.

        This method is overridden rather than letting it fall through to the
        underlying bug as the underlying implementation gets the bugtasks from
        self, which would in that case be the normal bug model object, which
        would then hit the database to get the tasks.
        """
        # Copied from Bug.getBugTarget to avoid importing.
        for bugtask in self.bugtasks:
            if bugtask.target == target:
                return bugtask
        return None

    @property
    def bugtask(self):
        """Return the bugtask for the branch project, or the default bugtask.

        This method defers the identitication of the appropriate task to the
        branch target.
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
        """Override the default behaviour of the branch object.

        The default behaviour is just to get the bugs.  We want to display the
        tasks however, and to avoid the extra database queries to get the
        tasks, we get them all at once, and provide decorated bugs (that have
        their tasks cached).
        """
        # To whomever it may concern, this function should be pushed down to
        # the model, and the related visibility checks made part of the query.
        # Alternatively it may be unused at this stage.
        bugs = defaultdict(list)
        for bug in self.branch.linked_bugs:
            bugs[bug.id].extend(bug.bugtasks)
        return [DecoratedBug(bug, self.branch, tasks)
                for bug, tasks in bugs.iteritems()
                if check_permission('launchpad.View', bug)]

    @property
    def displayname(self):
        """Override the default model property.

        If left to the underlying model, it would call the bzr_identity on the
        underlying branch rather than the cached bzr_identity on the decorated
        branch.  And that would cause two database queries.
        """
        return self.bzr_identity

    @cachedproperty
    def bzr_identity(self):
        """Cache the result of the bzr identity.

        The property is defined in the bzrIdentityMixin class.  This uses the
        associatedProductSeries and associatedSuiteSourcePackages methods.
        """
        return super(DecoratedBranch, self).bzr_identity

    @cachedproperty
    def is_series_branch(self):
        """A simple property to see if there are any series links."""
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
        """Cache the realized product series links."""
        return list(self.branch.associatedProductSeries())

    @cachedproperty
    def suite_source_packages(self):
        """Cache the realized suite source package links."""
        return list(self.branch.associatedSuiteSourcePackages())

    @cachedproperty
    def upgrade_pending(self):
        """Cache the result as the property hits the database."""
        return self.branch.upgrade_pending

    @cachedproperty
    def subscriptions(self):
        """Cache the realized branch subscription objects."""
        return list(self.branch.subscriptions)

    def hasSubscription(self, user):
        """Override the default branch implementation.

        The default implementation hits the database.  Since we have a full
        list of subscribers anyway, a simple check over the list is
        sufficient.
        """
        for sub in self.subscriptions:
            if sub.person == user:
                return True
        return False

    @cachedproperty
    def latest_revisions(self):
        """Cache the query result.

        When a tal:repeat is used, the method is called twice.  Firstly to
        check that there is something to iterate over, and secondly for the
        actual iteration.  Without the cached property, the database is hit
        twice.
        """
        return list(self.branch.latest_revisions())

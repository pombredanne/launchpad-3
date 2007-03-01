# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components related to bug tasks."""

__metaclass__ = type
__all__ = [
    'BugTaskDelta',
    'BugTaskToBugAdapter',
    'BugTaskMixin',
    'NullBugTask',
    ]

# XXX: see bug 49029 -- kiko, 2006-06-14
from zope.interface.declarations import alsoProvides
from zope.interface import implements

from canonical.launchpad.interfaces import (
    IBugTaskDelta, IUpstreamBugTask, IDistroBugTask, IDistroReleaseBugTask,
    INullBugTask)
from canonical.lp.dbschema import BugTaskStatus


class BugTaskDelta:
    """See canonical.launchpad.interfaces.IBugTaskDelta."""
    implements(IBugTaskDelta)
    def __init__(self, bugtask, product=None, sourcepackagename=None,
                 status=None, importance=None, assignee=None,
                 milestone=None, statusexplanation=None, bugwatch=None):
        self.bugtask = bugtask
        self.product = product
        self.sourcepackagename = sourcepackagename
        self.status = status
        self.importance = importance
        self.assignee = assignee
        self.target = milestone
        self.statusexplanation = statusexplanation
        self.bugwatch = bugwatch


class BugTaskMixin:
    """Mix-in class for some property methods of IBugTask implementations."""

    @property
    def title(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        title = 'Bug #%s in %s: "%s"' % (
            self.bug.id, self.targetname, self.bug.title)
        return title

    @property
    def targetname(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        return self.targetnamecache

    @property
    def target(self):
        # We explicitly reference attributes here (rather than, say,
        # IDistroBugTask.providedBy(self)), because we can't assume this
        # task has yet been marked with the correct interface.
        if self.product:
            return self.product
        elif self.productseries:
            return self.productseries
        elif self.distribution:
            if self.sourcepackagename:
                return self.distribution.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distribution
        elif self.distrorelease:
            if self.sourcepackagename:
                return self.distrorelease.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distrorelease
        else:
            raise AssertionError("Unable to determine bugtask target")

    @property
    def related_tasks(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        other_tasks = [
            task for task in self.bug.bugtasks if task != self]

        return other_tasks

    @property
    def related_pillar_bugtasks(self):
        """See IBugTask."""
        return [task for task in self.bug.bugtasks if task != self and (
            task.product is not None or task.distribution is not None)]


class NullBugTask(BugTaskMixin):
    """A null object for IBugTask.

    This class is used, for example, to be able to render a URL like:

      /products/evolution/+bug/5

    when bug #5 isn't yet reported in evolution.
    """
    implements(INullBugTask)

    def __init__(self, bug, product=None, productseries=None,
                 sourcepackagename=None, distribution=None,
                 distrorelease=None):
        self.bug = bug
        self.product = product
        self.productseries = productseries
        self.sourcepackagename = sourcepackagename
        self.distribution = distribution
        self.distrorelease = distrorelease

        # Mark the task with the correct interface, depending on its
        # context.
        if self.product:
            alsoProvides(self, IUpstreamBugTask)
        elif self.distribution:
            alsoProvides(self, IDistroBugTask)
        elif self.distrorelease:
            alsoProvides(self, IDistroReleaseBugTask)

        # Set a bunch of attributes to None, because it doesn't make
        # sense for these attributes to have a value when there is no
        # real task there. (In fact, it may make sense for these
        # values to be non-null, but I haven't yet found a use case
        # for it, and I don't think there's any point on designing for
        # that until we've encountered one.)
        self.id = None
        self.datecreated = None
        self.dateassigned = None
        self.age = None
        self.milestone = None
        self.status = None
        self.statusexplanation = None
        self.importance = None
        self.assignee = None
        self.bugwatch = None
        self.owner = None
        self.conjoined_master = None
        self.conjoined_slave = None

    @property
    def targetname(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        # For a INullBugTask, there is no targetname in the database, of
        # course, so we fallback on calculating the targetname in
        # Python.
        return self.target.bugtargetname


def BugTaskToBugAdapter(bugtask):
    """Adapt an IBugTask to an IBug."""
    return bugtask.bug


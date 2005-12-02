# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components related to bug tasks."""

__metaclass__ = type
__all__ = [
    'BugTaskDelta',
    'BugTaskToBugAdapter',
    'BugTaskMixin',
    'NullBugTask',
    'mark_task']

from zope.component import getUtility
from zope.interface import implements, directlyProvides, directlyProvidedBy

from canonical.launchpad.interfaces import (
    IBugTaskDelta, IMaintainershipSet, IUpstreamBugTask,
    IDistroBugTask, IDistroReleaseBugTask, 
    INullBugTask)
from canonical.lp.dbschema import BugTaskStatus

class BugTaskDelta:
    """See canonical.launchpad.interfaces.IBugTaskDelta."""
    implements(IBugTaskDelta)
    def __init__(self, bugtask, product=None, sourcepackagename=None,
                 binarypackagename=None, status=None, severity=None,
                 priority=None, assignee=None, milestone=None,
                 statusexplanation=None, bugwatch=None):
        self.bugtask = bugtask
        self.product = product
        self.sourcepackagename = sourcepackagename
        self.binarypackagename = binarypackagename
        self.status = status
        self.severity = severity
        self.priority = priority
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
    def maintainer(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        if self.product:
            return self.product.owner
        if self.distribution and self.sourcepackagename:
            maintainer = getUtility(IMaintainershipSet).get(
                distribution=self.distribution,
                sourcepackagename=self.sourcepackagename)
            return maintainer

        return None

    @property
    def maintainer_displayname(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        if self.maintainer:
            return self.maintainer.displayname
        else:
            return None

    @property
    def targetname(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        return self.targetnamecache

    # XXX 2005-06-25 kiko: if target actually works, we can probably
    # nuke this or simplify it significantly.
    def _calculate_targetname(self):
        """See canonical.launchpad.interfaces.IBugTask.

        Depending on whether the task has a distribution,
        distrorelease, sourcepackagename, binarypackagename, and/or
        product, the targetname will have one of these forms:
        * sourcepackagename.name (distribution.displayname)
        * sourcepackagename.name binarypackagename.name
            (distribution.displayname)
        * sourcepackagename.name (distrorelease.fullreleasename)
        * sourcepackagename.name binarypackagename.name
            (distrorelease.fullreleasename)
        * distribution.displayname
        * distrorelease.fullreleasename
        * product.name (upstream)
        """
        if self.distribution or self.distrorelease:
            if self.sourcepackagename is None:
                sourcepackagename_name = None
            else:
                sourcepackagename_name = self.sourcepackagename.name
            if self.binarypackagename is None:
                binarypackagename_name = None
            else:
                binarypackagename_name = self.binarypackagename.name
            L = []
            if self.sourcepackagename:
                L.append(sourcepackagename_name)
            if (binarypackagename_name and
                binarypackagename_name != sourcepackagename_name):
                L.append(binarypackagename_name)
            if L:
                name = " ".join(L)
                if self.distribution:
                    name += " (%s)" % self.distribution.displayname
                elif self.distrorelease:
                    name += " (%s)" % self.distrorelease.fullreleasename
                return name
            else:
                if self.distribution:
                    return self.distribution.displayname
                elif self.distrorelease:
                    return self.distrorelease.fullreleasename
        elif self.product:
            return '%s (upstream)' % self.product.name
        else:
            raise AssertionError("Unable to determine bugtask target")

    @property
    def target(self):
        if IUpstreamBugTask.providedBy(self):
            return self.product
        elif IDistroBugTask.providedBy(self):
            if self.sourcepackagename:
                return self.distribution.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distribution
        elif IDistroReleaseBugTask.providedBy(self):
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
    def statuselsewhere(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        related_tasks = self.related_tasks
        if related_tasks:
            fixes_found = len(
                [task for task in related_tasks
                 if (task.status == BugTaskStatus.FIXED or
                     task.status == BugTaskStatus.RELEASED)])
            if fixes_found:
                return "fixed in %d of %d places" % (
                    fixes_found, len(self.bug.bugtasks))
            else:
                if len(related_tasks) == 1:
                    return "filed in 1 other place"
                else:
                    return "filed in %d other places" % len(related_tasks)
        else:
            return "not filed elsewhere"


class NullBugTask(BugTaskMixin):
    """A null object for IBugTask.

    This class is used, for example, to be able to render a URL like:

      /products/evolution/+bug/5

    when bug #5 isn't yet reported in evolution.
    """
    implements(INullBugTask)

    def __init__(self, bug, product=None, sourcepackagename=None,
                 distribution=None, distrorelease=None):
        self.bug = bug
        self.product = product
        self.sourcepackagename = sourcepackagename
        self.distribution = distribution
        self.distrorelease = distrorelease

        # Mark the task with the correct interface, depending on its
        # context.
        if self.product:
            mark_task(self, IUpstreamBugTask)
        elif self.distribution:
            mark_task(self, IDistroBugTask)
        elif self.distrorelease:
            mark_task(self, IDistroReleaseBugTask)

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
        self.priority = None
        self.severity = None
        self.assignee = None
        self.binarypackagename = None
        self.bugwatch = None
        self.owner = None

    @property
    def targetname(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        # For a INullBugTask, there is no targetname in the database, of
        # course, so we fallback on calculating the targetname in Python.
        return self._calculate_targetname()

    @property
    def statusdisplayhtml(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        return u"Not reported in %s" % self.targetname


def BugTaskToBugAdapter(bugtask):
    """Adapt an IBugTask to an IBug."""
    return bugtask.bug


def mark_task(obj, iface):
    directlyProvides(obj, iface + directlyProvidedBy(obj))

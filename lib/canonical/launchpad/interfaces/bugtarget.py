# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Interfaces related to bugs."""

__metaclass__ = type


__all__ = [
    'IBugTarget',
    'BugDistroReleaseTargetDetails']


from zope.interface import Interface, Attribute


class IBugTarget(Interface):
    """An entity on which a bug can be reported.

    Examples include an IDistribution, an IDistroRelease and an
    IProduct.
    """
    def searchTasks(search_params):
        """Search the IBugTasks reported on this entity.

        :search_params: a BugTaskSearchParams object

        Return an iterable of matching results.

        Note: milestone is currently ignored for all IBugTargets
        except IProduct.
        """

    def createBug(owner, title, comment, security_related=False, private=False):
        """Create a new bug on this target.

        :title: The title of the bug, as a string.
        :comment: The initial comment/default description.
        :security_related: Is this a security vulnerability? A boolean
        value.
        :private: Should this bug be visible only to subscribers? A
        boolean value.
        """

    def getUsedBugTags():
        """Return the tags used by the context as a sorted list of strings."""

    open_bugtasks = Attribute("A list of open bugTasks for this target.")
    inprogress_bugtasks = Attribute("A list of in-progress bugTasks for this target.")
    critical_bugtasks = Attribute("A list of critical BugTasks for this target.")
    unconfirmed_bugtasks = Attribute("A list of Unconfirmed BugTasks for this target.")
    unassigned_bugtasks = Attribute("A list of unassigned BugTasks for this target.")
    all_bugtasks = Attribute("A list of all BugTasks ever reported for this target.")


class BugDistroReleaseTargetDetails:
    """The details of a bug targeted to a specific IDistroRelease.

    The following attributes are provided:

    :release: The IDistroRelease.
    :istargeted: Is there a fix targeted to this release?
    :sourcepackage: The sourcepackage to which the fix would be targeted.
    :assignee: An IPerson, or None if no assignee.
    :status: A BugTaskStatus dbschema item, or None, if release is not targeted.
    """
    def __init__(self, release, istargeted=False, sourcepackage=None,
                 assignee=None, status=None):
        self.release = release
        self.istargeted = istargeted
        self.sourcepackage = sourcepackage
        self.assignee = assignee
        self.status = status


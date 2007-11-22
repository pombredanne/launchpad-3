# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bugs."""

__metaclass__ = type


__all__ = [
    'IBugTarget',
    'BugDistroSeriesTargetDetails']

from zope.interface import Interface, Attribute


class IBugTarget(Interface):
    """An entity on which a bug can be reported.

    Examples include an IDistribution, an IDistroSeries and an
    IProduct.
    """
    # XXX Brad Bollenbach 2006-08-02 bug=54974: This attribute name smells.
    bugtargetdisplayname = Attribute("A display name for this bug target")
    bugtargetname = Attribute("The target as shown in mail notifications.")

    open_bugtasks = Attribute("A list of open bugTasks for this target.")
    closed_bugtasks = Attribute("A list of closed bugTasks for this target.")
    inprogress_bugtasks = Attribute("A list of in-progress bugTasks for this target.")
    critical_bugtasks = Attribute("A list of critical BugTasks for this target.")
    new_bugtasks = Attribute("A list of New BugTasks for this target.")
    unassigned_bugtasks = Attribute("A list of unassigned BugTasks for this target.")
    all_bugtasks = Attribute("A list of all BugTasks ever reported for this target.")

    def searchTasks(search_params):
        """Search the IBugTasks reported on this entity.

        :search_params: a BugTaskSearchParams object

        Return an iterable of matching results.

        Note: milestone is currently ignored for all IBugTargets
        except IProduct.
        """

    def getMostCommonBugs(user, limit=10):
        """Return the list of most commonly-reported bugs.

        This is the list of bugs that have the most dupes, ordered from
        most to least duped.
        """

    def createBug(bug_params):
        """Create a new bug on this target.

        bug_params is an instance of
        canonical.launchpad.interfaces.CreateBugParams.
        """

    def getUsedBugTags():
        """Return the tags used by the context as a sorted list of strings."""

    def getUsedBugTagsWithOpenCounts(user):
        """Return name and bug count of tags having open bugs.

        It returns a list of tuples contining the tag name, and the
        number of open bugs having that tag. Only the bugs that the user
        has permission to see are counted, and only tags having open
        bugs will be returned.
        """

    def getBugCounts(user, statuses=None):
        """Return a dict with the number of bugs in each possible status.

            :user: Only bugs the user has permission to view will be
                   counted.
            :statuses: Only bugs with these statuses will be counted. If
                       None, all statuses will be included.
        """


class BugDistroSeriesTargetDetails:
    """The details of a bug targeted to a specific IDistroSeries.

    The following attributes are provided:

    :series: The IDistroSeries.
    :istargeted: Is there a fix targeted to this series?
    :sourcepackage: The sourcepackage to which the fix would be targeted.
    :assignee: An IPerson, or None if no assignee.
    :status: A BugTaskStatus dbschema item, or None, if series is not targeted.
    """
    def __init__(self, series, istargeted=False, sourcepackage=None,
                 assignee=None, status=None):
        self.series = series
        self.istargeted = istargeted
        self.sourcepackage = sourcepackage
        self.assignee = assignee
        self.status = status


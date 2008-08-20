# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interfaces related to bugs."""

__metaclass__ = type


__all__ = [
    'BugDistroSeriesTargetDetails',
    'IBugTarget',
    'IHasBugs',
    ]

from zope.interface import Interface, Attribute
from zope.schema import Text

from canonical.launchpad import _
from canonical.lazr.rest.declarations import (
   call_with, collection_default_content, export_as_webservice_collection,
   export_as_webservice_entry, export_factory_operation,
   export_read_operation, export_write_operation, exported,
   operation_parameters, operation_returns_collection_of,
   operation_returns_entry, rename_parameters_as, REQUEST_USER,
   webservice_error)
from canonical.lazr.fields import CollectionField, Reference

class IHasBugs(Interface):
    """An entity which has a collection of bug tasks."""

    export_as_webservice_entry()

    open_bugtasks = exported(CollectionField(
        title=_("A list of open bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    closed_bugtasks = exported(CollectionField(
        title=_("A list of closed bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    inprogress_bugtasks = exported(CollectionField(
        title=_("A list of in-progress bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    critical_bugtasks = exported(CollectionField(
        title=_("A list of critical BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    new_bugtasks = exported(CollectionField(
        title=_("A list of New BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    unassigned_bugtasks = exported(CollectionField(
        title=_("A list of unassigned BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask
    all_bugtasks = exported(CollectionField(
        title=_("A list of all BugTasks ever reported for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=Interface))) # IBugTask

#     @operation_parameters()
#     @operation_returns_collection_of(Interface) # Actually, IBugTask
#     @export_read_operation()
    def searchTasks(search_params, user=None,
                    order_by=('-importance',), search_text=None,
                    status=[],
                    importance=None,
                    assignee=None, bug_reporter=None, bug_supervisor=None,
                    bug_commenter=None, bug_subscriber=None, owner=None,
                    has_patch=None, has_cve=None,
                    tags=None, tags_combinator_all=True,
                    omit_duplicates=True, omit_targeted=None,
                    status_upstream=None, milestone_assignment=None,
                    milestone=None, component=None, nominated_for=None,
                    distribution=None, scope=None, sourcepackagename=None,
                    has_no_package=None):
        """Search the IBugTasks reported on this entity.

        :search_params: a BugTaskSearchParams object

        Return an iterable of matching results.

        Note: milestone is currently ignored for all IBugTargets
        except IProduct.
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


class IBugTarget(IHasBugs):
    """An entity on which a bug can be reported.

    Examples include an IDistribution, an IDistroSeries and an
    IProduct.
    """

    export_as_webservice_entry()

    # XXX Brad Bollenbach 2006-08-02 bug=54974: This attribute name smells.
    bugtargetdisplayname = Attribute("A display name for this bug target")
    bugtargetname = Attribute("The target as shown in mail notifications.")

    bug_reporting_guidelines = Text(
        title=(
            u"If I\N{right single quotation mark}m reporting a bug, "
            u"I should include, if possible"),
        description=(
            u"These guidelines will be shown to anyone reporting a bug."),
        required=False, max_length=50000)

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

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
from zope.schema import (
    Bool, Choice, Datetime, Field, Int, List, Text, TextLine)

from canonical.launchpad import _
from canonical.launchpad.interfaces.bugtask import (
    IBugTask, IBugTaskSearch)
from canonical.launchpad.interfaces.person import IPerson
from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.interface import copy_field
from canonical.lazr.rest.declarations import (
   call_with, collection_default_content, export_as_webservice_collection,
   export_as_webservice_entry, export_factory_operation,
   export_read_operation, export_write_operation, exported,
   operation_parameters, operation_returns_collection_of,
   operation_returns_entry, rename_parameters_as, REQUEST_USER,
   webservice_error)


class IHasBugs(Interface):
    """An entity which has a collection of bug tasks."""

    export_as_webservice_entry()

    open_bugtasks = exported(CollectionField(
        title=_("A list of open bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    closed_bugtasks = exported(CollectionField(
        title=_("A list of closed bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    inprogress_bugtasks = exported(CollectionField(
        title=_("A list of in-progress bugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    critical_bugtasks = exported(CollectionField(
        title=_("A list of critical BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    new_bugtasks = exported(CollectionField(
        title=_("A list of New BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    unassigned_bugtasks = exported(CollectionField(
        title=_("A list of unassigned BugTasks for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))
    all_bugtasks = exported(CollectionField(
        title=_("A list of all BugTasks ever reported for this target."),
        readonly=True, required=False,
        value_type=Reference(schema=IBugTask)))

    @call_with(search_params=None, user=REQUEST_USER)
    @operation_parameters(
        order_by=List(
            title=_('List of fields by which the results are ordered.'),
            required=False),
        search_text=copy_field(IBugTaskSearch['searchtext']),
        status=copy_field(IBugTaskSearch['status']),
        importance=copy_field(IBugTaskSearch['importance']),
        assignee=Reference(schema=IPerson),
        bug_reporter=Reference(schema=IPerson),
        bug_supervisor=Reference(schema=IPerson),
        bug_commenter=Reference(schema=IPerson),
        bug_subscriber=Reference(schema=IPerson),
        owner=Reference(schema=IPerson),
        has_patch=copy_field(IBugTaskSearch['has_patch']),
        has_cve=copy_field(IBugTaskSearch['has_cve']),
        tags=copy_field(IBugTaskSearch['tag']),
        tags_combinator_all=Bool(
            title=_('All tags?'), required=False),
        omit_duplicates=copy_field(IBugTaskSearch['omit_dupes']),
        omit_targeted=copy_field(IBugTaskSearch['omit_targeted']),
        status_upstream=copy_field(IBugTaskSearch['status_upstream']),
        milestone_assignment=copy_field(
            IBugTaskSearch['milestone_assignment']),
        milestone=copy_field(IBugTaskSearch['milestone']),
        component=copy_field(IBugTaskSearch['component']),
        nominated_for=Reference(schema=Interface),
        distribution=Reference(schema=Interface), # IDistribution
        sourcepackagename=TextLine(title=_("Source Package"), required=False),
        has_no_package=copy_field(IBugTaskSearch['has_no_package']))
    @operation_returns_collection_of(IBugTask)
    @export_read_operation()
    def searchTasks(search_params, user=None,
                    order_by=['-importance'], search_text=None,
                    status=[],
                    importance=None,
                    assignee=None, bug_reporter=None, bug_supervisor=None,
                    bug_commenter=None, bug_subscriber=None, owner=None,
                    has_patch=None, has_cve=None,
                    tags=None, tags_combinator_all=True,
                    omit_duplicates=True, omit_targeted=None,
                    status_upstream=None, milestone_assignment=None,
                    milestone=None, component=None, nominated_for=None,
                    distribution=None, sourcepackagename=None,
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

IBugTask['target'].schema = IBugTarget


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

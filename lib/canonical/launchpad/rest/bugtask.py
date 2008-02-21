# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Resources having to do with Launchpad bugtasks."""

__metaclass__ = type
__all__ = [
    'BugTaskCollection',
    'BugTaskEntry',
    'IBugTaskEntry'
]


from zope.component import adapts
from zope.schema import Bool, Choice, Datetime, Int, Object, Text, TextLine

from canonical.lazr.interfaces import IEntry
from canonical.lazr.rest import Collection, Entry
from canonical.lazr.rest.schema import CollectionField

from canonical.launchpad.interfaces import (
    BugTaskImportance, BugTaskStatus, IBug, IBugTask, IPerson)
from canonical.lp import decorates


class IBugTaskEntry(IEntry):
    """The part of a bugtask that we expose through the web service."""

    bug = Object(schema=IBug)
    #product = Object(schema=IProject)
    #product_series = Object(schema=IProductSeries)
    #source_package_name = Object(schema=ISourcePackage)
    #distribution = Object(schema=IDistribution)
    #distro_series = Object(schema=IDistroSeries)
    #milestone = Object(schema=IMilestone)
    status = Choice(
        title=u'Status', vocabulary=BugTaskStatus,
        default=BugTaskStatus.NEW)
    importance = Choice(
        title=u'Importance', vocabulary=BugTaskImportance,
        default=BugTaskImportance.UNDECIDED)
    status_explanation = Text(
        title=u"Status notes (optional)", required=False)
    assignee = Object(schema=IPerson)
    bug_target_display_name = Text(
        title=u"The short, descriptive name of the target", readonly=True)
    bug_target_name = Text(
        title=u"The target as presented in mail notifications", readonly=True)
    #bugwatch = Object(schema=IBugWatch)
    date_assigned = Datetime(
        title=u"Date Assigned",
        description=u"The date on which this task was assigned to someone.")
    date_created = Datetime(
        title=u"Date Created",
        description=u"The date on which this task was created.")
    date_confirmed = Datetime(
        title=u"Date Confirmed",
        description=u"The date on which this task was marked Confirmed.")
    date_inprogress = Datetime(
        title=u"Date In Progress",
        description=u"The date on which this task was marked In Progress.")
    date_closed = Datetime(
        title=u"Date Closed",
        description=u"The date on which this task was marked either Fix "
        "Committed or Fix Released.")
    owner = Object(schema=IPerson)

    #target = Object(schema=IBugTarget)
    title = Text(title=u"The title of the bug related to this bugtask",
                         readonly=True)
    related_tasks = CollectionField(title=u"Other tasks on the same bug.",
                                    value_type=Object(schema=IBugTask))
    #pillar = Object(schema=IPillar)
    #other_affected_pillars = CollectionField(
    #    value_type=Object(schema=IPillar))

    conjoined_master = Object(schema=IBugTask)
    conjoined_slave = Object(schema=IBugTask)

    is_complete = Bool(
        title=u"Is all the work required on this bug task complete?")

    #subscribers
    #package_component


class BugTaskEntry(Entry):
    """A bugtask."""

    adapts(IBugTask)
    decorates(IBugTaskEntry)
    schema = IBugTaskEntry

    parent_collection_name = 'bugtasks'

    @property
    def status_explanation(self):
        """Perform a simple name mapping."""
        return self.context.statusexplanation

    @property
    def bug_target_display_name(self):
        """Perform a simple name mapping."""
        return self.context.bugtargetdisplayname

    @property
    def bug_target_name(self):
        """Perform a simple name mapping."""
        return self.context.bugtargetname

    @property
    def date_created(self):
        """Perform a simple name mapping."""
        return self.context.datecreated


class BugTaskCollection(Collection):
    """A collection of bugtasks."""

    def getEntryPath(self, entry):
        """See `ICollection`."""
        return str(entry.context.id)

    def lookupEntry(self, id):
        """Find a BugTask by ID."""
        return self.context.get(id)

    def find(self):
        """It makes little sense to expose a list of all the bugtasks."""
        return None



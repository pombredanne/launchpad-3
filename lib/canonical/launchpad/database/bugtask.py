# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
"""Classes that implement IBugTask and its related interfaces."""

__metaclass__ = type

__all__ = [
    'BugTaskDelta',
    'BugTaskToBugAdapter',
    'BugTaskMixin',
    'BugTask',
    'BugTaskSet',
    'NullBugTask',
    'bugtask_sort_key',
    'get_bug_privacy_filter',
    'search_value_to_where_condition']


import datetime

from sqlobject import (
    ForeignKey, StringCol, SQLObjectNotFound)
from sqlobject.sqlbuilder import SQLConstant

import pytz

from zope.component import getUtility
from zope.interface import implements, alsoProvides
from zope.security.proxy import isinstance as zope_isinstance

from canonical.config import config

from canonical.database.sqlbase import SQLBase, sqlvalues, quote, quote_like
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.enumcol import EnumCol

from canonical.lazr.enum import DBItem

from canonical.launchpad.searchbuilder import any, NULL, not_equals
from canonical.launchpad.database.pillar import pillar_sort_key
from canonical.launchpad.interfaces import (
    BugTaskSearchParams,
    ConjoinedBugTaskEditError,
    IBugTask,
    IBugTaskDelta,
    IBugTaskSet,
    IDistributionSourcePackage,
    IDistroBugTask,
    IDistroSeries,
    IDistroSeriesBugTask,
    ILaunchpadCelebrities,
    INullBugTask,
    IProductSeries,
    IProductSeriesBugTask,
    IProjectMilestone,
    ISourcePackage,
    IUpstreamBugTask,
    NotFoundError,
    RESOLVED_BUGTASK_STATUSES,
    UNRESOLVED_BUGTASK_STATUSES,
    BUG_CONTACT_BUGTASK_STATUSES,
    BugTaskStatus,
    BugTaskStatusSearch,
    )
from canonical.launchpad.helpers import shortlist
# XXX: kiko 2006-06-14 bug=49029

from canonical.lp.dbschema import (
    BugNominationStatus,
    BugTaskImportance,
    PackagePublishingStatus,
    )


debbugsseveritymap = {None:        BugTaskImportance.UNDECIDED,
                      'wishlist':  BugTaskImportance.WISHLIST,
                      'minor':     BugTaskImportance.LOW,
                      'normal':    BugTaskImportance.MEDIUM,
                      'important': BugTaskImportance.HIGH,
                      'serious':   BugTaskImportance.HIGH,
                      'grave':     BugTaskImportance.HIGH,
                      'critical':  BugTaskImportance.CRITICAL}


def bugtask_sort_key(bugtask):
    """A sort key for a set of bugtasks. We want:

          - products first, followed by their productseries tasks
          - distro tasks, followed by their distroseries tasks
          - ubuntu first among the distros
    """
    if bugtask.product:
        product_name = bugtask.product.name
        productseries_name = None
    elif bugtask.productseries:
        productseries_name = bugtask.productseries.name
        product_name = bugtask.productseries.product.name
    else:
        product_name = None
        productseries_name = None

    if bugtask.distribution:
        distribution_name = bugtask.distribution.name
    else:
        distribution_name = None

    if bugtask.distroseries:
        distroseries_name = bugtask.distroseries.version
        distribution_name = bugtask.distroseries.distribution.name
    else:
        distroseries_name = None

    if bugtask.sourcepackagename:
        sourcepackage_name = bugtask.sourcepackagename.name
    else:
        sourcepackage_name = None

    # Move ubuntu to the top.
    if distribution_name == 'ubuntu':
        distribution_name = '-'

    return (
        bugtask.bug.id, distribution_name, product_name, productseries_name,
        distroseries_name, sourcepackage_name)


class BugTaskDelta:
    """See `IBugTaskDelta`."""
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
    def bug_subscribers(self):
        """See `IBugTask`."""
        indirect_subscribers = self.bug.getIndirectSubscribers()
        return self.bug.getDirectSubscribers() + indirect_subscribers

    @property
    def bugtargetdisplayname(self):
        """See `IBugTask`."""
        return self.target.bugtargetdisplayname

    @property
    def bugtargetname(self):
        """See `IBugTask`."""
        return self.target.bugtargetname

    @property
    def target(self):
        """See `IBugTask`."""
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
        elif self.distroseries:
            if self.sourcepackagename:
                return self.distroseries.getSourcePackage(
                    self.sourcepackagename)
            else:
                return self.distroseries
        else:
            raise AssertionError("Unable to determine bugtask target.")

    @property
    def related_tasks(self):
        """See `IBugTask`."""
        other_tasks = [
            task for task in self.bug.bugtasks if task != self]

        return other_tasks

    @property
    def pillar(self):
        """See `IBugTask`."""
        if self.product is not None:
            return self.product
        elif self.productseries is not None:
            return self.productseries.product
        elif self.distribution is not None:
            return self.distribution
        else:
            return self.distroseries.distribution

    @property
    def other_affected_pillars(self):
        """See `IBugTask`."""
        result = set()
        this_pillar = self.pillar
        for task in self.bug.bugtasks:
            that_pillar = task.pillar
            if that_pillar != this_pillar:
                result.add(that_pillar)
        return sorted(result, key=pillar_sort_key)

    @property
    def mentoring_offers(self):
        """See `IHasMentoringOffers`."""
        # mentoring is on IBug as a whole, not on a specific task, so we
        # pass through to the bug
        return self.bug.mentoring_offers

    def canMentor(self, user):
        """See `ICanBeMentored`."""
        # mentoring is on IBug as a whole, not on a specific task, so we
        # pass through to the bug
        return self.bug.canMentor(user)

    def isMentor(self, user):
        """See `ICanBeMentored`."""
        # mentoring is on IBug as a whole, not on a specific task, so we
        # pass through to the bug
        return self.bug.isMentor(user)

    def offerMentoring(self, user, team):
        """See `ICanBeMentored`."""
        # mentoring is on IBug as a whole, not on a specific task, so we
        # pass through to the bug
        return self.bug.offerMentoring(user, team)

    def retractMentoring(self, user):
        """See `ICanBeMentored`."""
        # mentoring is on IBug as a whole, not on a specific task, so we
        # pass through to the bug
        return self.bug.retractMentoring(user)


class NullBugTask(BugTaskMixin):
    """A null object for IBugTask.

    This class is used, for example, to be able to render a URL like:

      /products/evolution/+bug/5

    when bug #5 isn't yet reported in evolution.
    """
    implements(INullBugTask)

    def __init__(self, bug, product=None, productseries=None,
                 sourcepackagename=None, distribution=None,
                 distroseries=None):
        """Initialize a NullBugTask."""
        self.bug = bug
        self.product = product
        self.productseries = productseries
        self.sourcepackagename = sourcepackagename
        self.distribution = distribution
        self.distroseries = distroseries

        # Mark the task with the correct interface, depending on its
        # context.
        if self.product:
            alsoProvides(self, IUpstreamBugTask)
        elif self.distribution:
            alsoProvides(self, IDistroBugTask)
        elif self.distroseries:
            alsoProvides(self, IDistroSeriesBugTask)
        elif self.productseries:
            alsoProvides(self, IProductSeriesBugTask)
        else:
            raise AssertionError('Unknown NullBugTask: %r.' % self)

        # Set a bunch of attributes to None, because it doesn't make
        # sense for these attributes to have a value when there is no
        # real task there. (In fact, it may make sense for these
        # values to be non-null, but I haven't yet found a use case
        # for it, and I don't think there's any point on designing for
        # that until we've encountered one.)
        self.id = None
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

        self.datecreated = None
        self.date_assigned = None
        self.date_confirmed = None
        self.date_last_updated = None
        self.date_inprogress = None
        self.date_closed = None

    @property
    def title(self):
        """See `IBugTask`."""
        return 'Bug #%s is not in %s: "%s"' % (
            self.bug.id, self.bugtargetdisplayname, self.bug.title)


def BugTaskToBugAdapter(bugtask):
    """Adapt an IBugTask to an IBug."""
    return bugtask.bug


class BugTask(SQLBase, BugTaskMixin):
    """See `IBugTask`."""
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = ['distribution', 'product', 'productseries',
                     'distrorelease', 'milestone', 'sourcepackagename']
    _CONJOINED_ATTRIBUTES = (
        "status", "importance", "assignee", "milestone",
        "date_assigned", "date_confirmed", "date_inprogress",
        "date_closed", "date_incomplete")
    _NON_CONJOINED_STATUSES = (BugTaskStatus.WONTFIX,)

    bug = ForeignKey(dbName='bug', foreignKey='Bug', notNull=True)
    product = ForeignKey(
        dbName='product', foreignKey='Product',
        notNull=False, default=None)
    productseries = ForeignKey(
        dbName='productseries', foreignKey='ProductSeries',
        notNull=False, default=None)
    sourcepackagename = ForeignKey(
        dbName='sourcepackagename', foreignKey='SourcePackageName',
        notNull=False, default=None)
    distribution = ForeignKey(
        dbName='distribution', foreignKey='Distribution',
        notNull=False, default=None)
    distroseries = ForeignKey(
        dbName='distrorelease', foreignKey='DistroSeries',
        notNull=False, default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone',
        notNull=False, default=None)
    status = EnumCol(
        dbName='status', notNull=True,
        schema=BugTaskStatus,
        default=BugTaskStatus.NEW)
    statusexplanation = StringCol(dbName='statusexplanation', default=None)
    importance = EnumCol(
        dbName='importance', notNull=True,
        schema=BugTaskImportance,
        default=BugTaskImportance.UNDECIDED)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        notNull=False, default=None)
    bugwatch = ForeignKey(dbName='bugwatch', foreignKey='BugWatch',
        notNull=False, default=None)
    date_assigned = UtcDateTimeCol(notNull=False, default=None)
    datecreated  = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    date_confirmed = UtcDateTimeCol(notNull=False, default=None)
    date_inprogress = UtcDateTimeCol(notNull=False, default=None)
    date_closed = UtcDateTimeCol(notNull=False, default=None)
    date_incomplete = UtcDateTimeCol(notNull=False, default=None)
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    # The targetnamecache is a value that is only supposed to be set
    # when a bugtask is created/modified or by the
    # update-bugtask-targetnamecaches cronscript. For this reason it's
    # not exposed in the interface, and client code should always use
    # the bugtargetname and bugtargetdisplayname properties.
    #
    # This field is actually incorrectly named, since it currently
    # stores the bugtargetdisplayname.
    targetnamecache = StringCol(
        dbName='targetnamecache', notNull=False, default=None)

    @property
    def title(self):
        """See `IBugTask`."""
        return 'Bug #%s in %s: "%s"' % (
            self.bug.id, self.bugtargetdisplayname, self.bug.title)

    @property
    def bugtargetdisplayname(self):
        """See `IBugTask`."""
        return self.targetnamecache

    @property
    def age(self):
        """See `IBugTask`."""
        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)

        return now - self.datecreated

    # Several other classes need to generate lists of bug tasks, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc
    completeness_clause =  """
        BugTask.status IN ( %s )
        """ % ','.join([str(a.value) for a in RESOLVED_BUGTASK_STATUSES])

    @property
    def is_complete(self):
        """See `IBugTask`.

        Note that this should be kept in sync with the completeness_clause
        above.
        """
        return self.status in RESOLVED_BUGTASK_STATUSES

    def subscribe(self, person):
        """See `IBugTask`."""
        return self.bug.subscribe(person)

    def isSubscribed(self, person):
        """See `IBugTask`."""
        return self.bug.isSubscribed(person)

    def _syncSourcePackages(self, prev_sourcepackagename):
        """Synchronize changes to source packages with other distrotasks.

        If one distroseriestask's source package is changed, all the
        other distroseriestasks with the same distribution and source
        package has to be changed, as well as the corresponding
        distrotask.
        """
        if self.distroseries is not None:
            distribution = self.distroseries.distribution
        else:
            distribution = self.distribution
        if distribution is not None:
            for bugtask in self.related_tasks:
                if bugtask.distroseries:
                    related_distribution = bugtask.distroseries.distribution
                else:
                    related_distribution = bugtask.distribution
                if (related_distribution == distribution and
                    bugtask.sourcepackagename == prev_sourcepackagename):
                    bugtask.sourcepackagename = self.sourcepackagename

    @property
    def conjoined_master(self):
        """See `IBugTask`."""
        conjoined_master = None
        if (IDistroBugTask.providedBy(self) and
            self.distribution.currentseries is not None):
            current_series = self.distribution.currentseries
            for bt in shortlist(self.bug.bugtasks):
                if (bt.distroseries == current_series and
                    bt.sourcepackagename == self.sourcepackagename):
                    conjoined_master = bt
                    break
        elif IUpstreamBugTask.providedBy(self):
            assert self.product.development_focus is not None, (
                'A product should always have a development series.')
            devel_focus = self.product.development_focus
            for bt in shortlist(self.bug.bugtasks):
                if bt.productseries == devel_focus:
                    conjoined_master = bt
                    break

        if (conjoined_master is not None and
            conjoined_master.status in self._NON_CONJOINED_STATUSES):
            conjoined_master = None
        return conjoined_master

    @property
    def conjoined_slave(self):
        """See `IBugTask`."""
        conjoined_slave = None
        if IDistroSeriesBugTask.providedBy(self):
            distribution = self.distroseries.distribution
            if self.distroseries != distribution.currentseries:
                # Only current series tasks are conjoined.
                return None
            for bt in shortlist(self.bug.bugtasks):
                if (bt.distribution == distribution and
                    bt.sourcepackagename == self.sourcepackagename):
                    conjoined_slave = bt
                    break
        elif IProductSeriesBugTask.providedBy(self):
            product = self.productseries.product
            if self.productseries != product.development_focus:
                # Only developement focus tasks are conjoined.
                return None
            for bt in shortlist(self.bug.bugtasks):
                if bt.product == product:
                    conjoined_slave = bt
                    break

        if (conjoined_slave is not None and
            self.status in self._NON_CONJOINED_STATUSES):
            conjoined_slave = None
        return conjoined_slave

    # XXX: Bjorn Tillenius 2006-10-31:
    # Conjoined bugtask synching methods. We override these methods
    # individually, to avoid cycle problems if we were to override
    # _SO_setValue instead. This indicates either a bug or design issue
    # in SQLObject.
    # Each attribute listed in _CONJOINED_ATTRIBUTES should have a
    # _set_foo method below.
    def _set_status(self, value):
        """Set status, and update conjoined BugTask."""
        if value not in self._NON_CONJOINED_STATUSES:
            self._setValueAndUpdateConjoinedBugTask("status", value)
        else:
            self._SO_set_status(value)

    def _set_assignee(self, value):
        """Set assignee, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("assignee", value)

    def _set_importance(self, value):
        """Set importance, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("importance", value)

    def _set_milestone(self, value):
        """Set milestone, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("milestone", value)

    def _set_sourcepackagename(self, value):
        """Set sourcepackagename, and update conjoined BugTask."""
        old_sourcepackagename = self.sourcepackagename
        self._setValueAndUpdateConjoinedBugTask("sourcepackagename", value)
        self._syncSourcePackages(old_sourcepackagename)

    def _set_date_assigned(self, value):
        """Set date_assigned, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_assigned", value)

    def _set_date_confirmed(self, value):
        """Set date_confirmed, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_confirmed", value)

    def _set_date_inprogress(self, value):
        """Set date_inprogress, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_inprogress", value)

    def _set_date_closed(self, value):
        """Set date_closed, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_closed", value)

    def _set_date_incomplete(self, value):
        """Set date_incomplete, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_incomplete", value)

    def _setValueAndUpdateConjoinedBugTask(self, colname, value):
        """Set a value, and update conjoined BugTask."""
        if self._isConjoinedBugTask():
            raise ConjoinedBugTaskEditError(
                "This task cannot be edited directly, it should be"
                " edited through its conjoined_master.")
        # The conjoined slave is updated before the master one because,
        # for distro tasks, conjoined_slave does a comparison on
        # sourcepackagename, and the sourcepackagenames will not match
        # if the conjoined master is altered before the conjoined slave!
        conjoined_bugtask = self.conjoined_slave
        if conjoined_bugtask:
            conjoined_attrsetter = getattr(
                conjoined_bugtask, "_SO_set_%s" % colname)
            conjoined_attrsetter(value)

        attrsetter = getattr(self, "_SO_set_%s" % colname)
        attrsetter(value)

    def _isConjoinedBugTask(self):
        """Return True when conjoined_master is not None, otherwise False."""
        return self.conjoined_master is not None

    def _syncFromConjoinedSlave(self):
        """Ensure the conjoined master is synched from its slave.

        This method should be used only directly after when the
        conjoined master has been created after the slave, to ensure
        that they are in sync from the beginning.
        """
        conjoined_slave = self.conjoined_slave

        for synched_attr in self._CONJOINED_ATTRIBUTES:
            slave_attr_value = getattr(conjoined_slave, synched_attr)
            # Bypass our checks that prevent setting attributes on
            # conjoined masters by calling the underlying sqlobject
            # setter methods directly.
            attrsetter = getattr(self, "_SO_set_%s" % synched_attr)
            attrsetter(slave_attr_value)

    def _init(self, *args, **kw):
        """Marks the task when it's created or fetched from the database."""
        SQLBase._init(self, *args, **kw)
        # We use the forbidden underscore attributes below because, with
        # SQLObject, hitting self.product means querying and
        # instantiating an object; prejoining doesn't help because this
        # happens when the bug task is being instantiated -- too early
        # in cases where we prejoin other things in.
        # XXX: kiko 2006-03-21:
        # we should use a specific SQLObject API here to avoid the
        # privacy violation.
        if self.productID is not None:
            alsoProvides(self, IUpstreamBugTask)
        elif self.productseriesID is not None:
            alsoProvides(self, IProductSeriesBugTask)
        elif self.distroseriesID is not None:
            alsoProvides(self, IDistroSeriesBugTask)
        elif self.distributionID is not None:
            # If nothing else, this is a distro task.
            alsoProvides(self, IDistroBugTask)
        else:
            raise AssertionError, "Task %d is floating." % self.id

    @property
    def target_uses_malone(self):
        """See `IBugTask`"""
        # XXX sinzui 2007-10-4 bug=149009:
        # This property is not needed. Code should inline this implementation.
        return self.pillar.official_malone

    def _SO_setValue(self, name, value, fromPython, toPython):
        """Set a SQLObject value and update the targetnamecache."""
        SQLBase._SO_setValue(self, name, value, fromPython, toPython)

        # The bug target may have just changed, so update the
        # targetnamecache.
        if name != 'targetnamecache':
            self.updateTargetNameCache()

    def set(self, **kw):
        """Update multiple attributes and update the targetnamecache."""
        # We need to overwrite this method to make sure the targetnamecache
        # column is updated when multiple attributes of a bugtask are
        # modified. We can't rely on event subscribers for doing this because
        # they can run in a unpredictable order.
        SQLBase.set(self, **kw)
        # We also can't simply update kw with the value we want for
        # targetnamecache because we need to access bugtask attributes
        # that may be available only after SQLBase.set() is called.
        SQLBase.set(
            self, **{'targetnamecache': self.target.bugtargetdisplayname})

    def setImportanceFromDebbugs(self, severity):
        """See `IBugTask`."""
        try:
            self.importance = debbugsseveritymap[severity]
        except KeyError:
            raise ValueError('Unknown debbugs severity "%s".' % severity)
        return self.importance

    def canTransitionToStatus(self, new_status, user):
        """See `IBugTask`."""
        celebrities = getUtility(ILaunchpadCelebrities)
        if (user.inTeam(self.pillar.bugcontact) or
            user.inTeam(self.pillar.owner) or
            user.id == celebrities.bug_watch_updater.id or
            user.id == celebrities.bug_importer.id):
            return True
        else:
            return new_status not in BUG_CONTACT_BUGTASK_STATUSES

    def transitionToStatus(self, new_status, user):
        """See `IBugTask`."""
        if not new_status:
            # This is mainly to facilitate tests which, unlike the
            # normal status form, don't always submit a status when
            # testing the edit form.
            return

        if not self.canTransitionToStatus(new_status, user):
            raise AssertionError(
                "Only Bug Contacts may change status to %s." % (
                    new_status.title,))

        if self.status == new_status:
            # No change in the status, so nothing to do.
            return

        old_status = self.status
        self.status = new_status

        if new_status == BugTaskStatus.UNKNOWN:
            # Ensure that all status-related dates are cleared,
            # because it doesn't make sense to have any values set for
            # date_confirmed, date_closed, etc. when the status
            # becomes UNKNOWN.
            self.date_confirmed = None
            self.date_inprogress = None
            self.date_closed = None
            self.date_incomplete = None

            return

        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)

        # Record the date of the particular kinds of transitions into
        # certain states.
        if ((old_status < BugTaskStatus.CONFIRMED) and
            (new_status >= BugTaskStatus.CONFIRMED)):
            # Even if the bug task skips the Confirmed status
            # (e.g. goes directly to Fix Committed), we'll record a
            # confirmed date at the same time anyway, otherwise we get
            # a strange gap in our data, and potentially misleading
            # reports.
            self.date_confirmed = now

        if ((old_status < BugTaskStatus.INPROGRESS) and
            (new_status >= BugTaskStatus.INPROGRESS)):
            # Same idea with In Progress as the comment above about
            # Confirmed.
            self.date_inprogress = now

        # Bugs can jump in and out of 'incomplete' status
        # and for just as long as they're marked incomplete
        # we keep a date_incomplete recorded for them.
        if new_status == BugTaskStatus.INCOMPLETE:
            self.date_incomplete = now
        else:
            self.date_incomplete = None

        if ((old_status in UNRESOLVED_BUGTASK_STATUSES) and
            (new_status in RESOLVED_BUGTASK_STATUSES)):
            self.date_closed = now

        # Ensure that we don't have dates recorded for state
        # transitions, if the bugtask has regressed to an earlier
        # workflow state. We want to ensure that, for example, a
        # bugtask that went New => Confirmed => New
        # has a dateconfirmed value of None.
        if new_status in UNRESOLVED_BUGTASK_STATUSES:
            self.date_closed = None

        if new_status < BugTaskStatus.CONFIRMED:
            self.date_confirmed = None

        if new_status < BugTaskStatus.INPROGRESS:
            self.date_inprogress = None

    def transitionToAssignee(self, assignee):
        """See `IBugTask`."""
        if assignee == self.assignee:
            # No change to the assignee, so nothing to do.
            return

        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)
        if self.assignee and not assignee:
            # The assignee is being cleared, so clear the date_assigned
            # value.
            self.date_assigned = None
        if not self.assignee and assignee:
            # The task is going from not having an assignee to having
            # one, so record when this happened
            self.date_assigned = now

        self.assignee = assignee

    def updateTargetNameCache(self):
        """See `IBugTask`."""
        targetname = self.target.bugtargetdisplayname
        if self.targetnamecache != targetname:
            self.targetnamecache = targetname

    def asEmailHeaderValue(self):
        """See `IBugTask`."""
        # Calculate an appropriate display value for the assignee.
        if self.assignee:
            if self.assignee.preferredemail:
                assignee_value = self.assignee.preferredemail.email
            else:
                # There is an assignee with no preferredemail, so we'll
                # "degrade" to the assignee.name. This might happen for teams
                # that don't have associated emails or when a bugtask was
                # imported from an external source and had its assignee set
                # automatically, even though the assignee may not even know
                # they have an account in Launchpad. :)
                assignee_value = self.assignee.name
        else:
            assignee_value = 'None'

        # Calculate an appropriate display value for the sourcepackage.
        if self.sourcepackagename:
            sourcepackagename_value = self.sourcepackagename.name
        else:
            # There appears to be no sourcepackagename associated with this
            # task.
            sourcepackagename_value = 'None'

        # Calculate an appropriate display value for the component, if the
        # target looks like some kind of source package.
        component = 'None'
        currentrelease = None
        if ISourcePackage.providedBy(self.target):
            currentrelease = self.target.currentrelease
        if IDistributionSourcePackage.providedBy(self.target):
            if self.target.currentrelease:
                target = self.target
                currentrelease = target.currentrelease.sourcepackagerelease

        if currentrelease:
            component = currentrelease.component.name

        if IUpstreamBugTask.providedBy(self):
            header_value = 'product=%s;' %  self.target.name
        elif IProductSeriesBugTask.providedBy(self):
            header_value = 'product=%s; productseries=%s;' %  (
                self.productseries.product.name, self.productseries.name)
        elif IDistroBugTask.providedBy(self):
            header_value = ((
                'distribution=%(distroname)s; '
                'sourcepackage=%(sourcepackagename)s; '
                'component=%(componentname)s;') %
                {'distroname': self.distribution.name,
                 'sourcepackagename': sourcepackagename_value,
                 'componentname': component})
        elif IDistroSeriesBugTask.providedBy(self):
            header_value = ((
                'distribution=%(distroname)s; '
                'distroseries=%(distroseriesname)s; '
                'sourcepackage=%(sourcepackagename)s; '
                'component=%(componentname)s;') %
                {'distroname': self.distroseries.distribution.name,
                 'distroseriesname': self.distroseries.name,
                 'sourcepackagename': sourcepackagename_value,
                 'componentname': component})
        else:
            raise AssertionError('Unknown BugTask context: %r.' % self)

        # We only want to have a milestone field in the header if there's
        # a milestone set for the bug.
        if self.milestone:
            header_value += ' milestone=%s;' % self.milestone.name

        header_value += ((
            ' status=%(status)s; importance=%(importance)s; '
            'assignee=%(assignee)s;') %
            {'status': self.status.title,
             'importance': self.importance.title,
             'assignee': assignee_value})

        return header_value

    def getDelta(self, old_task):
        """See `IBugTask`."""
        changes = {}
        if ((IUpstreamBugTask.providedBy(old_task) and
             IUpstreamBugTask.providedBy(self)) or
            (IProductSeriesBugTask.providedBy(old_task) and
             IProductSeriesBugTask.providedBy(self))):
            if old_task.product != self.product:
                changes["product"] = {}
                changes["product"]["old"] = old_task.product
                changes["product"]["new"] = self.product
        elif ((IDistroBugTask.providedBy(old_task) and
               IDistroBugTask.providedBy(self)) or
              (IDistroSeriesBugTask.providedBy(old_task) and
               IDistroSeriesBugTask.providedBy(self))):
            if old_task.sourcepackagename != self.sourcepackagename:
                old = old_task
                changes["sourcepackagename"] = {}
                changes["sourcepackagename"]["new"] = self.sourcepackagename
                changes["sourcepackagename"]["old"] = old.sourcepackagename
        else:
            raise TypeError(
                "Can't calculate delta on bug tasks of incompatible types: "
                "[%s, %s]." % (repr(old_task), repr(self)))

        # calculate the differences in the fields that both types of tasks
        # have in common
        for field_name in ("status", "importance",
                           "assignee", "bugwatch", "milestone"):
            old_val = getattr(old_task, field_name)
            new_val = getattr(self, field_name)
            if old_val != new_val:
                changes[field_name] = {}
                changes[field_name]["old"] = old_val
                changes[field_name]["new"] = new_val

        if changes:
            changes["bugtask"] = self
            return BugTaskDelta(**changes)
        else:
            return None


def search_value_to_where_condition(search_value):
    """Convert a search value to a WHERE condition.

        >>> search_value_to_where_condition(any(1, 2, 3))
        'IN (1,2,3)'
        >>> search_value_to_where_condition(any()) is None
        True
        >>> search_value_to_where_condition(not_equals('foo'))
        "!= 'foo'"
        >>> search_value_to_where_condition(1)
        '= 1'
        >>> search_value_to_where_condition(NULL)
        'IS NULL'

    """
    if zope_isinstance(search_value, any):
        # When an any() clause is provided, the argument value
        # is a list of acceptable filter values.
        if not search_value.query_values:
            return None
        return "IN (%s)" % ",".join(sqlvalues(*search_value.query_values))
    elif zope_isinstance(search_value, not_equals):
        return "!= %s" % sqlvalues(search_value.value)
    elif search_value is not NULL:
        return "= %s" % sqlvalues(search_value)
    else:
        # The argument value indicates we should match
        # only NULL values for the column named by
        # arg_name.
        return "IS NULL"


def get_bug_privacy_filter(user):
    """An SQL filter for search results that adds privacy-awareness."""
    if user is None:
        return "Bug.private = FALSE"
    admin_team = getUtility(ILaunchpadCelebrities).admin
    if user.inTeam(admin_team):
        return ""
    # A subselect is used here because joining through
    # TeamParticipation is only relevant to the "user-aware"
    # part of the WHERE condition (i.e. the bit below.) The
    # other half of this condition (see code above) does not
    # use TeamParticipation at all.
    return """
        (Bug.private = FALSE OR Bug.id in (
             SELECT BugSubscription.bug
             FROM BugSubscription, TeamParticipation
             WHERE TeamParticipation.person = %(personid)s AND
                   BugSubscription.person = TeamParticipation.team))
                     """ % sqlvalues(personid=user.id)


class BugTaskSet:
    """See `IBugTaskSet`."""
    implements(IBugTaskSet)

    _ORDERBY_COLUMN = {
        "id": "BugTask.bug",
        "importance": "BugTask.importance",
        "assignee": "BugTask.assignee",
        "targetname": "BugTask.targetnamecache",
        "status": "BugTask.status",
        "title": "Bug.title",
        "milestone": "BugTask.milestone",
        "dateassigned": "BugTask.dateassigned",
        "datecreated": "BugTask.datecreated",
        "date_last_updated": "Bug.date_last_updated",
        "date_closed": "BugTask.date_closed"}

    _open_resolved_upstream = """
                EXISTS (
                    SELECT TRUE FROM BugTask AS RelatedBugTask
                    WHERE RelatedBugTask.bug = BugTask.bug
                        AND RelatedBugTask.id != BugTask.id
                        AND ((
                            RelatedBugTask.bugwatch IS NOT NULL AND
                            RelatedBugTask.status %s)
                            OR (
                            RelatedBugTask.product IS NOT NULL AND
                            RelatedBugTask.bugwatch IS NULL AND
                            RelatedBugTask.status %s))
                    )
                """

    title = "A set of bug tasks"

    def get(self, task_id):
        """See `IBugTaskSet`."""
        try:
            bugtask = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist." %
                                str(task_id))
        return bugtask

    def findSimilar(self, user, summary, product=None, distribution=None,
                    sourcepackagename=None):
        """See `IBugTaskSet`."""
        # Avoid circular imports.
        from canonical.launchpad.database.bug import Bug
        search_params = BugTaskSearchParams(user)
        constraint_clauses = ['BugTask.bug = Bug.id']
        if product:
            search_params.setProduct(product)
            constraint_clauses.append(
                'BugTask.product = %s' % sqlvalues(product))
        elif distribution:
            search_params.setDistribution(distribution)
            constraint_clauses.append(
                'BugTask.distribution = %s' % sqlvalues(distribution))
            if sourcepackagename:
                search_params.sourcepackagename = sourcepackagename
                constraint_clauses.append(
                    'BugTask.sourcepackagename = %s' % sqlvalues(
                        sourcepackagename))
        else:
            raise AssertionError('Need either a product or distribution.')

        if not summary:
            return BugTask.select('1 = 2')

        search_params.fast_searchtext = nl_phrase_search(
            summary, Bug, ' AND '.join(constraint_clauses), ['BugTask'])
        return self.search(search_params)

    def _buildStatusClause(self, status):
        """Return the SQL query fragment for search by status.

        Called from `buildQuery` or recursively."""
        if zope_isinstance(status, any):
            return '(' + ' OR '.join(
                self._buildStatusClause(dbitem)
                for dbitem
                in status.query_values) + ')'
        elif zope_isinstance(status, not_equals):
            return '(NOT %s)' % self._buildStatusClause(status.value)
        elif zope_isinstance(status, DBItem):
            with_response = (
                status == BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE)
            without_response = (
                status == BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE)
            if with_response or without_response:
                status_clause = (
                    '(BugTask.status = %s) ' %
                    sqlvalues(BugTaskStatus.INCOMPLETE))
                if with_response:
                    status_clause += ("""
                        AND (Bug.date_last_message IS NOT NULL
                             AND BugTask.date_incomplete <=
                                 Bug.date_last_message)
                        """)
                elif without_response:
                    status_clause += ("""
                        AND (Bug.date_last_message IS NULL
                             OR BugTask.date_incomplete >
                                Bug.date_last_message)
                        """)
                else:
                    assert with_response != without_response
                return status_clause
            else:
                return '(BugTask.status = %s)' % sqlvalues(status)
        else:
            raise AssertionError(
                'Unrecognized status value: %s' % repr(status))

    def buildQuery(self, params):
        """Build and return an SQL query with the given parameters.

        Also return the clauseTables and orderBy for the generated query.
        """
        assert isinstance(params, BugTaskSearchParams)

        extra_clauses = ['Bug.id = BugTask.bug']
        clauseTables = ['BugTask', 'Bug']
        
        # These arguments can be processed in a loop without any other
        # special handling.
        standard_args = {
            'bug': params.bug,
            'importance': params.importance,
            'product': params.product,
            'distribution': params.distribution,
            'distrorelease': params.distroseries,
            'productseries': params.productseries,
            'assignee': params.assignee,
            'sourcepackagename': params.sourcepackagename,
            'owner': params.owner,
        }

        # Loop through the standard, "normal" arguments and build the
        # appropriate SQL WHERE clause. Note that arg_value will be one
        # of:
        #
        # * a searchbuilder.any object, representing a set of acceptable
        #   filter values
        # * a searchbuilder.NULL object
        # * an sqlobject
        # * a dbschema item
        # * None (meaning no filter criteria specified for that arg_name)
        #
        # XXX: kiko 2006-03-16:
        # Is this a good candidate for becoming infrastructure in
        # canonical.database.sqlbase?
        for arg_name, arg_value in standard_args.items():
            if arg_value is None:
                continue
            where_cond = search_value_to_where_condition(arg_value)
            if where_cond is not None:
                extra_clauses.append("BugTask.%s %s" % (arg_name, where_cond))

        if params.status is not None:
            extra_clauses.append(self._buildStatusClause(params.status))

        if params.milestone:
            if IProjectMilestone.providedBy(params.milestone):
                where_cond = """
                    IN (SELECT Milestone.id
                        FROM Milestone, Product
                        WHERE Milestone.product = Product.id
                            AND Product.project = %s
                            AND Milestone.name = %s)
                """ % sqlvalues(params.milestone.target,
                                params.milestone.name)

                # A bug may have bugtasks in more than one series, and these
                # bugtasks may have the same milestone value. To avoid
                # duplicate result rows for one bug, ensure that only that
                # bugtask is returned, that is directly assigned to the
                # product.
                extra_clauses.append("BugTask.product IS NOT null")
            else:
                where_cond = search_value_to_where_condition(params.milestone)
            extra_clauses.append("BugTask.milestone %s" % where_cond)

        if params.project:
            clauseTables.append("Product")
            extra_clauses.append("BugTask.product = Product.id")
            if isinstance(params.project, any):
                extra_clauses.append("Product.project IN (%s)" % ",".join(
                    [str(proj.id) for proj in params.project.query_values]))
            elif params.project is NULL:
                extra_clauses.append("Product.project IS NULL")
            else:
                extra_clauses.append("Product.project = %d" %
                                     params.project.id)

        if params.omit_dupes:
            extra_clauses.append("Bug.duplicateof is NULL")

        if params.omit_targeted:
            extra_clauses.append("BugTask.distrorelease is NULL AND "
                                 "BugTask.productseries is NULL")

        if params.has_cve:
            extra_clauses.append("BugTask.bug IN "
                                 "(SELECT DISTINCT bug FROM BugCve)")

        if params.attachmenttype is not None:
            clauseTables.append('BugAttachment')
            if isinstance(params.attachmenttype, any):
                where_cond = "BugAttachment.type IN (%s)" % ", ".join(
                    sqlvalues(*params.attachmenttype.query_values))
            else:
                where_cond = "BugAttachment.type = %s" % sqlvalues(
                    params.attachmenttype)
            extra_clauses.append("BugAttachment.bug = BugTask.bug")
            extra_clauses.append(where_cond)

        if params.searchtext:
            extra_clauses.append(self._buildSearchTextClause(params))

        if params.fast_searchtext:
            extra_clauses.append(self._buildFastSearchTextClause(params))

        if params.subscriber is not None:
            clauseTables.append('BugSubscription')
            extra_clauses.append("""Bug.id = BugSubscription.bug AND
                    BugSubscription.person = %(personid)s""" %
                    sqlvalues(personid=params.subscriber.id))

        if params.component:
            clauseTables += ["SourcePackagePublishingHistory",
                             "SourcePackageRelease"]
            distroseries = None
            if params.distribution:
                distroseries = params.distribution.currentseries
            elif params.distroseries:
                distroseries = params.distroseries
            assert distroseries, (
                "Search by component requires a context with a distribution "
                "or distroseries.")

            if zope_isinstance(params.component, any):
                component_ids = sqlvalues(*params.component.query_values)
            else:
                component_ids = sqlvalues(params.component)

            extra_clauses.extend(["""
            BugTask.sourcepackagename =
                SourcePackageRelease.sourcepackagename AND
            SourcePackageRelease.id =
                SourcePackagePublishingHistory.sourcepackagerelease AND
            SourcePackagePublishingHistory.distrorelease = %s AND
            SourcePackagePublishingHistory.archive IN %s AND
            SourcePackagePublishingHistory.component IN %s AND
            SourcePackagePublishingHistory.status = %s
            """ % sqlvalues(distroseries,
                            distroseries.distribution.all_distro_archive_ids,
                            component_ids,
                            PackagePublishingStatus.PUBLISHED)])

        upstream_clause = self._buildUpstreamClause(params)
        if upstream_clause:
            extra_clauses.append(upstream_clause)

        if params.tag:
            tags_clause = "BugTag.bug = BugTask.bug AND BugTag.tag %s" % (
                    search_value_to_where_condition(params.tag))
            extra_clauses.append(tags_clause)
            clauseTables.append('BugTag')

        if params.bug_contact:
            bug_contact_clause = """BugTask.id IN (
                SELECT BugTask.id FROM BugTask, Product
                WHERE BugTask.product = Product.id
                    AND Product.bugcontact = %(bug_contact)s
                UNION ALL
                SELECT BugTask.id
                FROM BugTask, PackageBugContact
                WHERE BugTask.distribution = PackageBugContact.distribution
                    AND BugTask.sourcepackagename =
                        PackageBugContact.sourcepackagename
                    AND PackageBugContact.bugcontact = %(bug_contact)s
                UNION ALL
                SELECT BugTask.id FROM BugTask, Distribution
                WHERE BugTask.distribution = Distribution.id
                    AND Distribution.bugcontact = %(bug_contact)s
                )""" % sqlvalues(bug_contact=params.bug_contact)
            extra_clauses.append(bug_contact_clause)

        if params.bug_reporter:
            bug_reporter_clause = (
                "BugTask.bug = Bug.id AND Bug.owner = %s" % sqlvalues(
                    params.bug_reporter))
            extra_clauses.append(bug_reporter_clause)

        if params.bug_commenter:
            bug_commenter_clause = """
            BugTask.id IN (
                SELECT BugTask.id FROM BugTask, BugMessage, Message
                WHERE Message.owner = %(bug_commenter)s
                    AND Message.id = BugMessage.message
                    AND BugTask.bug = BugMessage.bug
                    AND Message.id NOT IN (
                        SELECT BugMessage.message FROM BugMessage
                        WHERE BugMessage.bug = BugTask.bug
                        ORDER BY BugMessage.id
                        LIMIT 1
                    )
            )
            """ % sqlvalues(bug_commenter=params.bug_commenter)
            extra_clauses.append(bug_commenter_clause)

        if params.nominated_for:
            mappings = sqlvalues(
                target=params.nominated_for,
                nomination_status=BugNominationStatus.PROPOSED)
            if IDistroSeries.providedBy(params.nominated_for):
                mappings['target_column'] = 'distrorelease'
            elif IProductSeries.providedBy(params.nominated_for):
                mappings['target_column'] = 'productseries'
            else:
                raise AssertionError(
                    'Unknown nomination target: %r.' % params.nominated_for)
            nominated_for_clause = """
                BugNomination.bug = BugTask.bug AND
                BugNomination.%(target_column)s = %(target)s AND
                BugNomination.status = %(nomination_status)s
                """ % mappings
            extra_clauses.append(nominated_for_clause)
            clauseTables.append('BugNomination')

        clause = get_bug_privacy_filter(params.user)
        if clause:
            extra_clauses.append(clause)

        orderby_arg = self._processOrderBy(params)

        query = " AND ".join(extra_clauses)
        return query, clauseTables, orderby_arg

    def _buildUpstreamClause(self, params):
        """Return an clause for returning upstream data if the data exists.

        This method will handles BugTasks that do not have upstream BugTasks
        as well as thoses that do.
        """
        upstream_clauses = []
        if params.pending_bugwatch_elsewhere:
            if params.product:
                # Include only bugtasks that do no have bug watches that
                # belong to a product that does not use Malone.
                pending_bugwatch_elsewhere_clause = """
                    EXISTS (
                        SELECT TRUE 
                        FROM BugTask AS RelatedBugTask
                            LEFT OUTER JOIN Product AS OtherProduct
                                ON RelatedBugTask.product = OtherProduct.id
                        WHERE RelatedBugTask.bug = BugTask.bug
                            AND RelatedBugTask.id = BugTask.id
                            AND RelatedBugTask.bugwatch IS NULL
                            AND OtherProduct.official_malone IS FALSE
                            AND RelatedBugTask.status != %s)
                    """ % sqlvalues(BugTaskStatus.INVALID)
            else:
                # Include only bugtasks that have other bugtasks on targets
                # not using Malone, which are not Invalid, and have no bug
                # watch.
                pending_bugwatch_elsewhere_clause = """
                    EXISTS (
                        SELECT TRUE 
                        FROM BugTask AS RelatedBugTask
                            LEFT OUTER JOIN Distribution AS OtherDistribution
                                ON RelatedBugTask.distribution = 
                                    OtherDistribution.id
                            LEFT OUTER JOIN Product AS OtherProduct
                                ON RelatedBugTask.product = OtherProduct.id
                        WHERE RelatedBugTask.bug = BugTask.bug
                            AND RelatedBugTask.id != BugTask.id
                            AND RelatedBugTask.bugwatch IS NULL
                            AND (
                                OtherDistribution.official_malone IS FALSE
                                OR OtherProduct.official_malone IS FALSE)
                            AND RelatedBugTask.status != %s)
                    """ % sqlvalues(BugTaskStatus.INVALID)

            upstream_clauses.append(pending_bugwatch_elsewhere_clause)

        if params.has_no_upstream_bugtask:
            has_no_upstream_bugtask_clause = """
                BugTask.bug NOT IN (
                    SELECT DISTINCT bug FROM BugTask
                    WHERE product IS NOT NULL)
            """
            upstream_clauses.append(has_no_upstream_bugtask_clause)

        # Our definition of "resolved upstream" means:
        #
        # * bugs with bugtasks linked to watches that are invalid,
        #   fixed committed or fix released
        #
        # * bugs with upstream bugtasks that are fix committed or fix released
        #
        # This definition of "resolved upstream" should address the use
        # cases we gathered at UDS Paris (and followup discussions with
        # seb128, sfllaw, et al.)
        if params.resolved_upstream:
            statuses_for_watch_tasks = [
                BugTaskStatus.INVALID,
                BugTaskStatus.FIXCOMMITTED,
                BugTaskStatus.FIXRELEASED]
            statuses_for_upstream_tasks = [
                BugTaskStatus.FIXCOMMITTED,
                BugTaskStatus.FIXRELEASED]

            only_resolved_upstream_clause = self._open_resolved_upstream % (
                    search_value_to_where_condition(
                        any(*statuses_for_watch_tasks)),
                    search_value_to_where_condition(
                        any(*statuses_for_upstream_tasks)))
            upstream_clauses.append(only_resolved_upstream_clause)
        if params.open_upstream:
            statuses_for_open_tasks = [
                BugTaskStatus.NEW,
                BugTaskStatus.INCOMPLETE,
                BugTaskStatus.CONFIRMED,
                BugTaskStatus.INPROGRESS,
                BugTaskStatus.UNKNOWN]
            only_open_upstream_clause = self._open_resolved_upstream % (
                    search_value_to_where_condition(
                        any(*statuses_for_open_tasks)),
                    search_value_to_where_condition(
                        any(*statuses_for_open_tasks)))
            upstream_clauses.append(only_open_upstream_clause)

        if upstream_clauses:
            upstream_clause = " OR ".join(upstream_clauses)
            return '(%s)' % upstream_clause
        return None

    def _buildSearchTextClause(self, params):
        """Build the clause for searchtext."""
        assert params.fast_searchtext is None, (
            'Cannot use fast_searchtext at the same time as searchtext.')

        searchtext_quoted = quote(params.searchtext)
        searchtext_like_quoted = quote_like(params.searchtext)

        if params.orderby is None:
            # Unordered search results aren't useful, so sort by relevance
            # instead.
            params.orderby = [
                SQLConstant("-rank(Bug.fti, ftq(%s))" % searchtext_quoted),
                SQLConstant(
                    "-rank(BugTask.fti, ftq(%s))" % searchtext_quoted)]

        comment_clause = """BugTask.id IN (
            SELECT BugTask.id
            FROM BugTask, BugMessage,Message, MessageChunk
            WHERE BugMessage.bug = BugTask.bug
                AND BugMessage.message = Message.id
                AND Message.id = MessageChunk.message
                AND MessageChunk.fti @@ ftq(%s))""" % searchtext_quoted
        text_search_clauses = [
            "Bug.fti @@ ftq(%s)" % searchtext_quoted,
            "BugTask.fti @@ ftq(%s)" % searchtext_quoted,
            "BugTask.targetnamecache ILIKE '%%' || %s || '%%'" % (
                searchtext_like_quoted)]
        # Due to performance problems, whether to search in comments is
        # controlled by a config option.
        if config.malone.search_comments:
            text_search_clauses.append(comment_clause)
        return "(%s)" % " OR ".join(text_search_clauses)

    def _buildFastSearchTextClause(self, params):
        """Build the clause to use for the fast_searchtext criteria."""
        assert params.searchtext is None, (
            'Cannot use searchtext at the same time as fast_searchtext.')

        fast_searchtext_quoted = quote(params.fast_searchtext)

        if params.orderby is None:
            # Unordered search results aren't useful, so sort by relevance
            # instead.
            params.orderby = [
                SQLConstant("-rank(Bug.fti, ftq(%s))" %
                fast_searchtext_quoted)]

        return "Bug.fti @@ ftq(%s)" % fast_searchtext_quoted

    def search(self, params, *args):
        """See `IBugTaskSet`."""
        query, clauseTables, orderby = self.buildQuery(params)
        bugtasks = BugTask.select(
            query, clauseTables=clauseTables, orderBy=orderby)
        joins = self._getJoinsForSortingSearchResults()
        for arg in args:
            query, clauseTables, dummy = self.buildQuery(arg)
            bugtasks = bugtasks.union(BugTask.select(
                query, clauseTables=clauseTables), orderBy=orderby,
                joins=joins)
        bugtasks.prejoin(['sourcepackagename', 'product'])
        bugtasks.prejoinClauseTables(['Bug'])
        return bugtasks

    # XXX: salgado 2007-03-19:
    # This method exists only because sqlobject doesn't provide a better
    # way for sorting the results of a set operation by external table values.
    # It'll be removed, together with sqlobject, when we switch to storm.
    def _getJoinsForSortingSearchResults(self):
        """Return a list of join tuples suitable as the joins argument of
        sqlobject's set operation methods.

        These joins are necessary when we want to order the result of a set
        operaion like union() using values that are not part of our result
        set.
        """
        # Find out which tables we may need to join in order to cover all
        # possible sorting options we may want.
        tables = set()
        for value in self._ORDERBY_COLUMN.values():
            if '.' in value:
                table, col = value.split('.')
                tables.add(table)

        # Build the tuples expected by sqlobject for each table we may need.
        joins = []
        for table in tables:
            if table.lower() != 'bugtask':
                foreignkey_col = table
            else:
                foreignkey_col = 'id'
            joins.append((table, 'id', foreignkey_col))
        return joins

    def createTask(self, bug, owner, product=None, productseries=None,
                   distribution=None, distroseries=None,
                   sourcepackagename=None,
                   status=IBugTask['status'].default,
                   importance=IBugTask['importance'].default,
                   assignee=None, milestone=None):
        """See `IBugTaskSet`."""
        if not status:
            status = IBugTask['status'].default
        if not importance:
            importance = IBugTask['importance'].default
        if not assignee:
            assignee = None
        if not milestone:
            milestone = None

        if not bug.private and bug.security_related:
            if product and product.security_contact:
                bug.subscribe(product.security_contact)
            elif distribution and distribution.security_contact:
                bug.subscribe(distribution.security_contact)

        assert (product or productseries or distribution or distroseries), (
            'Got no bugtask target.')

        non_target_create_params = dict(
            bug=bug,
            status=status,
            importance=importance,
            assignee=assignee,
            owner=owner,
            milestone=milestone)
        bugtask = BugTask(
            product=product,
            productseries=productseries,
            distribution=distribution,
            distroseries=distroseries,
            sourcepackagename=sourcepackagename,
            **non_target_create_params)

        if distribution:
            # Create tasks for accepted nominations if this is a source
            # package addition.
            accepted_nominations = [
                nomination for nomination in bug.getNominations(distribution)
                if nomination.isApproved()]
            for nomination in accepted_nominations:
                accepted_series_task = BugTask(
                    distroseries=nomination.distroseries,
                    sourcepackagename=sourcepackagename,
                    **non_target_create_params)

        if bugtask.conjoined_slave:
            bugtask._syncFromConjoinedSlave()

        return bugtask

    def findExpirableBugTasks(self, min_days_old):
        """See `IBugTaskSet`.
        
        This implementation returns the master of the master-slave conjoined
        pairs of bugtasks. Slave conjoined bugtasks are not included in the
        list because they can only be expired by calling the master bugtask's
        transitionToStatus() method.
        """
        all_bugtasks = BugTask.select("""
            BugTask.id IN (
                SELECT BugTask.id
                FROM BugTask
                LEFT OUTER JOIN Distribution
                    ON distribution = Distribution.id
                    AND Distribution.official_malone IS TRUE
                LEFT OUTER JOIN DistroRelease
                    ON distrorelease = Distrorelease.id
                    AND DistroRelease.distribution IN (
                        SELECT id FROM Distribution
                        WHERE official_malone IS TRUE)
                LEFT OUTER JOIN Product
                    ON product = Product.id
                    AND Product.official_malone IS TRUE
                LEFT OUTER JOIN ProductSeries
                    ON productseries = ProductSeries.id
                    AND ProductSeries.product IN (
                        SELECT id FROM Product WHERE official_malone IS TRUE)
                WHERE
                    (Distribution.id IS NOT NULL
                     OR DistroRelease.id IS NOT NULL
                     OR Product.id IS NOT NULL
                     OR ProductSeries.id IS NOT NULL)
                    AND BugTask.status = %s
                    AND BugTask.assignee IS NULL
                    AND BugTask.bugwatch IS NULL
                    AND BugTask.date_incomplete < CURRENT_TIMESTAMP
                        AT TIME ZONE 'UTC' - interval '%s days'
            )""" % sqlvalues(BugTaskStatus.INCOMPLETE, min_days_old))
        bugtasks = []
        for bugtask in all_bugtasks:
            if bugtask.conjoined_master is None:
                bugtasks.append(bugtask)
        return bugtasks

    def maintainedBugTasks(self, person, minimportance=None,
                           showclosed=False, orderBy=None, user=None):
        """See `IBugTaskSet`."""
        filters = ['BugTask.bug = Bug.id',
                   'BugTask.product = Product.id',
                   'Product.owner = TeamParticipation.team',
                   'TeamParticipation.person = %s' % person.id]

        if not showclosed:
            committed = BugTaskStatus.FIXCOMMITTED
            filters.append('BugTask.status < %s' % sqlvalues(committed))

        if minimportance is not None:
            filters.append(
                'BugTask.importance >= %s' % sqlvalues(minimportance))

        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter:
            filters.append(privacy_filter)

        # We shouldn't show duplicate bug reports.
        filters.append('Bug.duplicateof IS NULL')

        return BugTask.select(" AND ".join(filters),
            clauseTables=['Product', 'TeamParticipation', 'BugTask', 'Bug'])

    def getOrderByColumnDBName(self, col_name):
        """See `IBugTaskSet`."""
        return self._ORDERBY_COLUMN[col_name]

    def _processOrderBy(self, params):
        """Process the orderby parameter supplied to search().

        This method ensures the sort order will be stable, and converting
        the string supplied to actual column names.
        """
        orderby = params.orderby
        if orderby is None:
            orderby = []
        elif not zope_isinstance(orderby, (list, tuple)):
            orderby = [orderby]

        orderby_arg = []
        # This set contains columns which are, in practical terms,
        # unique. When these columns are used as sort keys, they ensure
        # the sort will be consistent. These columns will be used to
        # decide whether we need to add the BugTask.bug and BugTask.id
        # columns to make the sort consistent over runs -- which is good
        # for the user and essential for the test suite.
        unambiguous_cols = set([
            "BugTask.dateassigned",
            "BugTask.datecreated",
            "Bug.datecreated",
            "Bug.date_last_updated"])
        # Bug ID is unique within bugs on a product or source package.
        if (params.product or
            (params.distribution and params.sourcepackagename) or
            (params.distroseries and params.sourcepackagename)):
            in_unique_context = True
        else:
            in_unique_context = False

        if in_unique_context:
            unambiguous_cols.add("BugTask.bug")

        # Translate orderby keys into corresponding Table.attribute
        # strings.
        ambiguous = True
        for orderby_col in orderby:
            if isinstance(orderby_col, SQLConstant):
                orderby_arg.append(orderby_col)
                continue
            if orderby_col.startswith("-"):
                col_name = self.getOrderByColumnDBName(orderby_col[1:])
                order_clause = "-" + col_name
            else:
                col_name = self.getOrderByColumnDBName(orderby_col)
                order_clause = col_name
            if col_name in unambiguous_cols:
                ambiguous = False
            orderby_arg.append(order_clause)

        if ambiguous:
            if in_unique_context:
                orderby_arg.append('BugTask.bug')
            else:
                orderby_arg.append('BugTask.id')

        return orderby_arg

    def dangerousGetAllTasks(self):
        """DO NOT USE THIS METHOD. For details, see `IBugTaskSet`"""
        return BugTask.select()


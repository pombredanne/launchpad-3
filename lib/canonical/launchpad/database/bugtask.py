# Copyright 2004-2006 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0611,W0212

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
from operator import attrgetter

from sqlobject import (
    ForeignKey, StringCol, SQLObjectNotFound)
from sqlobject.sqlbuilder import SQLConstant

import pytz

from zope.component import getUtility
from zope.interface import implements, alsoProvides
from zope.security.proxy import isinstance as zope_isinstance

from canonical.config import config

from canonical.database.sqlbase import (
    cursor, SQLBase, sqlvalues, quote, quote_like)
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.enumcol import EnumCol

from canonical.lazr.enum import DBItem

from canonical.launchpad.searchbuilder import all, any, NULL, not_equals
from canonical.launchpad.database.pillar import pillar_sort_key
from canonical.launchpad.validators.person import public_person_validator
from canonical.launchpad.interfaces import (
    BUG_SUPERVISOR_BUGTASK_STATUSES, BugNominationStatus, BugTaskImportance,
    BugTaskSearchParams, BugTaskStatus, BugTaskStatusSearch,
    ConjoinedBugTaskEditError, IBugTask, IBugTaskDelta, IBugTaskSet,
    IDistribution, IDistributionSourcePackage, IDistroBugTask, IDistroSeries,
    IDistroSeriesBugTask, ILaunchpadCelebrities, INullBugTask, IProduct,
    IProductSeries, IProductSeriesBugTask, IProject, IProjectMilestone,
    ISourcePackage, IUpstreamBugTask, NotFoundError, PackagePublishingStatus,
    RESOLVED_BUGTASK_STATUSES, UNRESOLVED_BUGTASK_STATUSES)
from canonical.launchpad.interfaces.distribution import (
    IDistributionSet)
from canonical.launchpad.interfaces.sourcepackagename import (
    ISourcePackageNameSet)
from canonical.launchpad.helpers import shortlist
# XXX: kiko 2006-06-14 bug=49029


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
    def __init__(self, bugtask, product=None,
                 sourcepackagename=None, status=None, importance=None,
                 assignee=None, milestone=None, statusexplanation=None,
                 bugwatch=None):
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
                     'distroseries', 'milestone', 'sourcepackagename']
    _CONJOINED_ATTRIBUTES = (
        "status", "importance", "assignee", "milestone",
        "date_assigned", "date_confirmed", "date_inprogress",
        "date_closed", "date_incomplete", "date_left_new",
        "date_triaged", "date_fix_committed", "date_fix_released")
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
        dbName='distroseries', foreignKey='DistroSeries',
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
        validator=public_person_validator,
        notNull=False, default=None)
    bugwatch = ForeignKey(dbName='bugwatch', foreignKey='BugWatch',
        notNull=False, default=None)
    date_assigned = UtcDateTimeCol(notNull=False, default=None)
    datecreated  = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    date_confirmed = UtcDateTimeCol(notNull=False, default=None)
    date_inprogress = UtcDateTimeCol(notNull=False, default=None)
    date_closed = UtcDateTimeCol(notNull=False, default=None)
    date_incomplete = UtcDateTimeCol(notNull=False, default=None)
    date_left_new = UtcDateTimeCol(notNull=False, default=None)
    date_triaged = UtcDateTimeCol(notNull=False, default=None)
    date_fix_committed = UtcDateTimeCol(notNull=False, default=None)
    date_fix_released = UtcDateTimeCol(notNull=False, default=None)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        validator=public_person_validator, notNull=True)
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

    def subscribe(self, person, subscribed_by):
        """See `IBugTask`."""
        return self.bug.subscribe(person, subscribed_by)

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

    def getConjoinedMaster(self, bugtasks, bugtasks_by_package=None):
        """See `IBugTask`."""
        conjoined_master = None
        if IDistroBugTask.providedBy(self):
            if bugtasks_by_package is None:
                bugtasks_by_package = self.getBugTasksByPackageName(bugtasks)
            bugtasks = bugtasks_by_package[self.sourcepackagename]
            possible_masters = [
                bugtask for bugtask in bugtasks
                if (bugtask.distroseries is not None and
                    bugtask.sourcepackagename == self.sourcepackagename)]
            # Return early, so that we don't have to get currentseries,
            # which is expensive.
            if len(possible_masters) == 0:
                return None
            current_series = self.distribution.currentseries
            for bugtask in possible_masters:
                if bugtask.distroseries == current_series:
                    conjoined_master = bugtask
                    break
        elif IUpstreamBugTask.providedBy(self):
            assert self.product.development_focus is not None, (
                'A product should always have a development series.')
            devel_focus = self.product.development_focus
            for bugtask in bugtasks:
                if bugtask.productseries == devel_focus:
                    conjoined_master = bugtask
                    break

        if (conjoined_master is not None and
            conjoined_master.status in self._NON_CONJOINED_STATUSES):
            conjoined_master = None
        return conjoined_master

    def getBugTasksByPackageName(self, bugtasks):
        """See IBugTask."""
        bugtasks_by_package = {}
        for bugtask in bugtasks:
            bugtasks_by_package.setdefault(bugtask.sourcepackagename, [])
            bugtasks_by_package[bugtask.sourcepackagename].append(bugtask)
        return bugtasks_by_package

    @property
    def conjoined_master(self):
        """See `IBugTask`."""
        return self.getConjoinedMaster(shortlist(self.bug.bugtasks))

    @property
    def conjoined_slave(self):
        """See `IBugTask`."""
        conjoined_slave = None
        if IDistroSeriesBugTask.providedBy(self):
            distribution = self.distroseries.distribution
            if self.distroseries != distribution.currentseries:
                # Only current series tasks are conjoined.
                return None
            for bugtask in shortlist(self.bug.bugtasks):
                if (bugtask.distribution == distribution and
                    bugtask.sourcepackagename == self.sourcepackagename):
                    conjoined_slave = bugtask
                    break
        elif IProductSeriesBugTask.providedBy(self):
            product = self.productseries.product
            if self.productseries != product.development_focus:
                # Only development focus tasks are conjoined.
                return None
            for bugtask in shortlist(self.bug.bugtasks):
                if bugtask.product == product:
                    conjoined_slave = bugtask
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

    def _set_date_left_new(self, value):
        """Set date_left_new, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_left_new", value)

    def _set_date_triaged(self, value):
        """Set date_left_triaged, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_triaged", value)

    def _set_date_fix_committed(self, value):
        """Set date_left_fix_committed, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_fix_committed", value)

    def _set_date_fix_released(self, value):
        """Set date_left_fix_released, and update conjoined BugTask."""
        self._setValueAndUpdateConjoinedBugTask("date_fix_released", value)

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
        if (user.inTeam(self.pillar.bug_supervisor) or
            user.inTeam(self.pillar.owner) or
            user.id == celebrities.bug_watch_updater.id or
            user.id == celebrities.bug_importer.id):
            return True
        else:
            return new_status not in BUG_SUPERVISOR_BUGTASK_STATUSES

    def transitionToStatus(self, new_status, user):
        """See `IBugTask`."""
        if not new_status:
            # This is mainly to facilitate tests which, unlike the
            # normal status form, don't always submit a status when
            # testing the edit form.
            return

        if not self.canTransitionToStatus(new_status, user):
            raise AssertionError(
                "Only Bug Supervisors may change status to %s." % (
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
            self.date_triaged = None
            self.date_fix_committed = None
            self.date_fix_released = None

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

        if (old_status == BugTaskStatus.NEW and
            new_status > BugTaskStatus.NEW and
            self.date_left_new is None):
            # This task is leaving the NEW status for the first time
            self.date_left_new = now

        # If the new status is equal to or higher
        # than TRIAGED, we record a `date_triaged`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.TRIAGED and
            new_status >= BugTaskStatus.TRIAGED):
            # This task is now marked as TRIAGED
            self.date_triaged = now

        # If the new status is equal to or higher
        # than FIXCOMMITTED, we record a `date_fixcommitted`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.FIXCOMMITTED and
            new_status >= BugTaskStatus.FIXCOMMITTED):
            # This task is now marked as FIXCOMMITTED
            self.date_fix_committed = now

        # If the new status is equal to or higher
        # than FIXRELEASED, we record a `date_fixreleased`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.FIXRELEASED and
            new_status >= BugTaskStatus.FIXRELEASED):
            # This task is now marked as FIXRELEASED
            self.date_fix_released = now

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

        if new_status < BugTaskStatus.TRIAGED:
            self.date_triaged = None

        if new_status < BugTaskStatus.FIXCOMMITTED:
            self.date_fix_committed = None

        if new_status < BugTaskStatus.FIXRELEASED:
            self.date_fix_released = None

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

    def getPackageComponent(self):
        """See `IBugTask`."""
        sourcepackage = None
        if ISourcePackage.providedBy(self.target):
            return self.target.latest_published_component
        if IDistributionSourcePackage.providedBy(self.target):
            spph = self.target.latest_overall_publication
            if spph:
                return spph.component
        return None

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
        component = self.getPackageComponent()
        if component is None:
            component_name = 'None'
        else:
            component_name = component.name

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
                 'componentname': component_name})
        elif IDistroSeriesBugTask.providedBy(self):
            header_value = ((
                'distribution=%(distroname)s; '
                'distroseries=%(distroseriesname)s; '
                'sourcepackage=%(sourcepackagename)s; '
                'component=%(componentname)s;') %
                {'distroname': self.distroseries.distribution.name,
                 'distroseriesname': self.distroseries.name,
                 'sourcepackagename': sourcepackagename_value,
                 'componentname': component_name})
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
        "date_closed": "BugTask.date_closed",
        "number_of_duplicates": "Bug.number_of_duplicates",
        "message_count": "Bug.message_count"
        }

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
        # XXX: JSK: 2007-12-19: This method should probably return
        # None when task_id is not present. See:
        # https://bugs.edge.launchpad.net/launchpad/+bug/123592
        try:
            bugtask = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist." %
                                str(task_id))
        return bugtask

    def getBugTaskBadgeProperties(self, bugtasks):
        """See `IBugTaskSet`."""
        # Need to import Bug locally, to avoid circular imports.
        from canonical.launchpad.database.bug import Bug
        bugtask_ids = [bugtask.id for bugtask in bugtasks]
        bugs_with_mentoring_offers = list(Bug.select(
            """id IN (SELECT MentoringOffer.bug
                      FROM MentoringOffer, BugTask
                      WHERE MentoringOffer.bug = BugTask.bug
                        AND BugTask.id IN %s)""" % sqlvalues(bugtask_ids)))
        bugs_with_specifications = list(Bug.select(
            """id IN (SELECT SpecificationBug.bug
                      FROM SpecificationBug, BugTask
                      WHERE SpecificationBug.bug = BugTask.bug
                        AND BugTask.id IN %s)""" % sqlvalues(bugtask_ids)))
        bugs_with_branches = list(Bug.select(
            """id IN (SELECT BugBranch.bug
                      FROM BugBranch, BugTask
                      WHERE BugBranch.bug = BugTask.bug
                        AND BugTask.id IN %s)""" % sqlvalues(bugtask_ids)))
        badge_properties = {}
        for bugtask in bugtasks:
            badge_properties[bugtask] = {
                'has_mentoring_offer':
                    bugtask.bug in bugs_with_mentoring_offers,
                'has_specification': bugtask.bug in bugs_with_specifications,
                'has_branch': bugtask.bug in bugs_with_branches,
                }
        return badge_properties

    def getMultiple(self, task_ids):
        """See `IBugTaskSet`."""
        # Ensure we have a sequence of bug task IDs:
        task_ids = [int(task_id) for task_id in task_ids]
        # Query the database, returning the results in a dictionary:
        if len(task_ids) > 0:
            tasks = BugTask.select('id in %s' % sqlvalues(task_ids))
            return dict([(task.id, task) for task in tasks])
        else:
            return {}

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
            'distroseries': params.distroseries,
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
            extra_clauses.append("BugTask.distroseries is NULL AND "
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
            SourcePackagePublishingHistory.distroseries = %s AND
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
            if zope_isinstance(params.tag, all):
                # If the user chose to search for
                # the presence of all specified bugs,
                # we must handle the search differently.
                tags_clauses = []
                for tag in params.tag.query_values:
                    tags_clauses.append("""
                    EXISTS(
                      SELECT *
                      FROM BugTag
                      WHERE BugTag.bug = BugTask.bug
                      AND BugTag.tag = %s)
                      """ % sqlvalues(tag))
                extra_clauses.append(' AND '.join(tags_clauses))
            else:
                # Otherwise, we just pass the value (which is either
                # naked or wrapped in `any` for SQL construction).
                tags_clause = "BugTag.bug = BugTask.bug AND BugTag.tag %s" % (
                    search_value_to_where_condition(params.tag))
                extra_clauses.append(tags_clause)
                clauseTables.append('BugTag')

        # XXX Tom Berger 2008-02-14:
        # We use StructuralSubscription to determine
        # the bug supervisor relation for distribution source
        # packages, following a conversion to use this object.
        # We know that the behaviour remains the same, but we
        # should change the terminology, or re-instate
        # PackageBugSupervisor, since the use of this relation here
        # is not for subscription to notifications.
        # See bug #191809
        if params.bug_supervisor:
            bug_supervisor_clause = """BugTask.id IN (
                SELECT BugTask.id FROM BugTask, Product
                WHERE BugTask.product = Product.id
                    AND Product.bug_supervisor = %(bug_supervisor)s
                UNION ALL
                SELECT BugTask.id
                FROM BugTask, StructuralSubscription
                WHERE BugTask.distribution = StructuralSubscription.distribution
                    AND BugTask.sourcepackagename =
                        StructuralSubscription.sourcepackagename
                    AND StructuralSubscription.subscriber = %(bug_supervisor)s
                UNION ALL
                SELECT BugTask.id FROM BugTask, Distribution
                WHERE BugTask.distribution = Distribution.id
                    AND Distribution.bug_supervisor = %(bug_supervisor)s
                )""" % sqlvalues(bug_supervisor=params.bug_supervisor)
            extra_clauses.append(bug_supervisor_clause)

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
                mappings['target_column'] = 'distroseries'
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
        bugtasks = bugtasks.prejoin(['sourcepackagename', 'product'])
        bugtasks = bugtasks.prejoinClauseTables(['Bug'])
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
                bug.subscribe(product.security_contact, owner)
            elif distribution and distribution.security_contact:
                bug.subscribe(distribution.security_contact, owner)

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

    def findExpirableBugTasks(self, min_days_old, user,
                              bug=None, target=None):
        """See `IBugTaskSet`.

        The list of Incomplete bugtasks is selected from products and
        distributions that use Launchpad to track bugs. To qualify for
        expiration, the bug and its bugtasks meet the follow conditions:

        1. The bug is inactive; the last update of the is older than
            Launchpad expiration age.
        2. The bug is not a duplicate.
        3. The bug does not have any other valid bugtasks.
        4. The bugtask belongs to a project with enable_bug_expiration set
           to True.
        5. The bugtask has the status Incomplete.
        6. The bugtask is not assigned to anyone.
        7. The bugtask does not have a milestone.

        Bugtasks cannot transition to Invalid automatically unless they meet
        all the rules stated above.

        This implementation returns the master of the master-slave conjoined
        pairs of bugtasks. Slave conjoined bugtasks are not included in the
        list because they can only be expired by calling the master bugtask's
        transitionToStatus() method. See 'Conjoined Bug Tasks' in
        c.l.doc/bugtasks.txt.

        Only bugtask the specified user has permission to view are
        returned. The Janitor celebrity has permission to view all bugs.
        """
        if bug is None:
            bug_clause = ''
        else:
            bug_clause = 'AND Bug.id = %s' % sqlvalues(bug)

        if user == getUtility(ILaunchpadCelebrities).janitor:
            # The janitor needs access to all bugs.
            bug_privacy_filter = ''
        else:
            bug_privacy_filter = get_bug_privacy_filter(user)
            if bug_privacy_filter != '':
                bug_privacy_filter = "AND " + bug_privacy_filter
        unconfirmed_bug_join = self._getUnconfirmedBugJoin()
        (target_join, target_clause) = self._getTargetJoinAndClause(target)
        expirable_bugtasks = BugTask.select("""
            BugTask.bug = Bug.id
            AND BugTask.id IN (
                SELECT BugTask.id
                FROM BugTask
                    JOIN Bug ON BugTask.bug = Bug.id
                    LEFT JOIN BugWatch on Bug.id = BugWatch.bug
                """ + unconfirmed_bug_join + """
                """ + target_join + """
                WHERE
                """ + target_clause + """
                """ + bug_clause + """
                """ + bug_privacy_filter + """
                    AND BugTask.status = %s
                    AND BugTask.assignee IS NULL
                    AND BugTask.milestone IS NULL
                    AND Bug.duplicateof IS NULL
                    AND Bug.date_last_updated < CURRENT_TIMESTAMP
                        AT TIME ZONE 'UTC' - interval '%s days'
                    AND BugWatch.id IS NULL
            )""" % sqlvalues(BugTaskStatus.INCOMPLETE, min_days_old),
            clauseTables=['Bug'],
            orderBy='Bug.date_last_updated')

        return expirable_bugtasks

    def _getUnconfirmedBugJoin(self):
        """Return the SQL to join BugTask to unconfirmed bugs.

        This method returns a derived table with the alias UnconfirmedBugs
        that contains the id of all bugs that that permit expiration.
        A bugtasks cannot expire if the bug is, has been, or
        will be, confirmed to be legitimate. Once the bug is considered
        valid for one target, it is valid for all targets.
        """
        statuses_not_preventing_expiration = [
            BugTaskStatus.INVALID, BugTaskStatus.INCOMPLETE,
            BugTaskStatus.WONTFIX]

        unexpirable_status_list = [
            status for status in BugTaskStatus.items
            if status not in statuses_not_preventing_expiration]

        return """
            JOIN (
                -- ALL bugs with incomplete bugtasks.
                SELECT BugTask.bug AS bug
                  FROM BugTask
                 WHERE BugTask.status = %s
            EXCEPT
                -- All valid bugs
            SELECT DISTINCT Bug.id as bug
                FROM Bug
                    JOIN BugTask ON Bug.id = BugTask.bug
                WHERE BugTask.status IN %s
            ) UnconfirmedBugs ON BugTask.bug = UnconfirmedBugs.bug
            """ % sqlvalues(BugTaskStatus.INCOMPLETE, unexpirable_status_list)

    def _getTargetJoinAndClause(self, target):
        """Return a SQL join clause to a `BugTarget`.

        :param target: A supported BugTarget or None. The target param must
            be either a Distribution, DistroSeries, Product, or ProductSeries.
            If target is None, the clause joins BugTask to all the supported
            BugTarget tables.
        :raises NotImplementedError: If the target is an IProject,
            ISourcePackage, or an IDistributionSourcePackage.
        :raises AssertionError: If the target is not a known implementer of
            `IBugTarget`
        """
        target_join = """
            JOIN (
                -- We create this rather bizarre looking structure
                -- because we must replicate the behaviour of BugTask since
                -- we are joining to it. So when distroseries is set,
                -- distribution should be NULL. The two pillar columns will
                -- be used in the WHERE clause.
                SELECT 0 AS distribution, 0 AS distroseries,
                       0 AS product , 0 AS productseries,
                       0 AS distribution_pillar, 0 AS product_pillar
                UNION
                    SELECT Distribution.id, NULL, NULL, NULL,
                        Distribution.id, NULL
                    FROM Distribution
                    WHERE Distribution.enable_bug_expiration IS TRUE
                UNION
                    SELECT NULL, DistroSeries.id, NULL, NULL,
                        Distribution.id, NULL
                    FROM DistroSeries
                        JOIN Distribution
                            ON DistroSeries.distribution = Distribution.id
                    WHERE Distribution.enable_bug_expiration IS TRUE
                UNION
                    SELECT NULL, NULL, Product.id, NULL,
                        NULL, Product.id
                    FROM Product
                    WHERE Product.enable_bug_expiration IS TRUE
                UNION
                    SELECT NULL, NULL, NULL, ProductSeries.id,
                        NULL, Product.id
                    FROM ProductSeries
                        JOIN Product
                            ON ProductSeries.Product = Product.id
                    WHERE Product.enable_bug_expiration IS TRUE) target
                ON (BugTask.distribution = target.distribution
                    OR BugTask.distroseries = target.distroseries
                    OR BugTask.product = target.product
                    OR BugTask.productseries = target.productseries)"""
        if target is None:
            target_clause = "TRUE IS TRUE"
        elif IDistribution.providedBy(target):
            target_clause = "target.distribution_pillar = %s" % sqlvalues(
                target)
        elif IDistroSeries.providedBy(target):
            target_clause = "BugTask.distroseries = %s" % sqlvalues(target)
        elif IProduct.providedBy(target):
            target_clause = "target.product_pillar = %s" % sqlvalues(target)
        elif IProductSeries.providedBy(target):
            target_clause = "BugTask.productseries = %s" % sqlvalues(target)
        elif (IProject.providedBy(target)
              or ISourcePackage.providedBy(target)
              or IDistributionSourcePackage.providedBy(target)):
            raise NotImplementedError(
                "BugTarget %s is not supported by ." % target)
        else:
            raise AssertionError("Unknown BugTarget type.")

        return (target_join, target_clause)

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
        return BugTask.select(orderBy='id')

    def getBugCountsForPackages(self, user, packages):
        """See `IBugTaskSet`."""
        distributions = sorted(
            set(package.distribution for package in packages),
            key=attrgetter('name'))
        counts = []
        for distribution in distributions:
            counts.extend(self._getBugCountsForDistribution(
                user, distribution, packages))
        return counts

    def _getBugCountsForDistribution(self, user, distribution, packages):
        """Get bug counts by package, belonging to the given distribution.

        See `IBugTask.getBugCountsForPackages` for more information.
        """
        packages = [
            package for package in packages
            if package.distribution == distribution]
        package_name_ids = [
            package.sourcepackagename.id for package in packages]

        open_bugs_cond = (
            'BugTask.status %s' % search_value_to_where_condition(
                any(*UNRESOLVED_BUGTASK_STATUSES)))

        sum_template = "SUM(CASE WHEN %s THEN 1 ELSE 0 END) AS %s"
        sums = [
            sum_template % (open_bugs_cond, 'open_bugs'),
            sum_template % (
                'BugTask.importance %s' % search_value_to_where_condition(
                    BugTaskImportance.CRITICAL), 'open_critical_bugs'),
            sum_template % (
                'BugTask.assignee IS NULL', 'open_unassigned_bugs'),
            sum_template % (
                'BugTask.status %s' % search_value_to_where_condition(
                    BugTaskStatus.INPROGRESS), 'open_inprogress_bugs'),
            ]

        conditions = [
            'Bug.id = BugTask.bug',
            open_bugs_cond,
            'BugTask.sourcepackagename IN %s' % sqlvalues(package_name_ids),
            'BugTask.distribution = %s' % sqlvalues(distribution),
            'Bug.duplicateof is NULL',
            ]
        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter:
            conditions.append(privacy_filter)

        query = """SELECT BugTask.distribution,
                          BugTask.sourcepackagename,
                          %(sums)s
                   FROM BugTask, Bug
                   WHERE %(conditions)s
                   GROUP BY BugTask.distribution, BugTask.sourcepackagename"""
        cur = cursor()
        cur.execute(query % dict(
            sums=', '.join(sums), conditions=' AND '.join(conditions)))
        distribution_set = getUtility(IDistributionSet)
        sourcepackagename_set = getUtility(ISourcePackageNameSet)
        packages_with_bugs = set()
        counts = []
        for (distro_id, spn_id, open_bugs,
             open_critical_bugs, open_unassigned_bugs,
             open_inprogress_bugs) in shortlist(cur.fetchall()):
            distribution = distribution_set.get(distro_id)
            sourcepackagename = sourcepackagename_set.get(spn_id)
            source_package = distribution.getSourcePackage(sourcepackagename)
            # XXX: Bjorn Tillenius 2006-12-15:
            # Add a tuple instead of the distribution package
            # directly, since DistributionSourcePackage doesn't define a
            # __hash__ method.
            packages_with_bugs.add((distribution, sourcepackagename))
            package_counts = dict(
                package=source_package,
                open=open_bugs,
                open_critical=open_critical_bugs,
                open_unassigned=open_unassigned_bugs,
                open_inprogress=open_inprogress_bugs,
                )
            counts.append(package_counts)

        # Only packages with open bugs were included in the query. Let's
        # add the rest of the packages as well.
        all_packages = set(
            (distro_package.distribution, distro_package.sourcepackagename)
            for distro_package in packages)
        for distribution, sourcepackagename in all_packages.difference(
                packages_with_bugs):
            package_counts = dict(
                package=distribution.getSourcePackage(sourcepackagename),
                open=0, open_critical=0, open_unassigned=0,
                open_inprogress=0)
            counts.append(package_counts)

        return counts

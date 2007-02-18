# Copyright 2004-2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'BugTask',
    'BugTaskSet',
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

from canonical.lp import dbschema

from canonical.database.sqlbase import SQLBase, sqlvalues, quote_like
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.enumcol import EnumCol

from canonical.launchpad.searchbuilder import any, NULL, not_equals
from canonical.launchpad.components.bugtask import BugTaskMixin
from canonical.launchpad.interfaces import (
    BugTaskSearchParams, IBugTask, IBugTaskSet, IUpstreamBugTask,
    IDistroBugTask, IDistroReleaseBugTask, IProductSeriesBugTask, NotFoundError,
    ILaunchpadCelebrities, ISourcePackage, IDistributionSourcePackage,
    UNRESOLVED_BUGTASK_STATUSES, RESOLVED_BUGTASK_STATUSES,
    ConjoinedBugTaskEditError)
from canonical.launchpad.helpers import shortlist


debbugsseveritymap = {None:        dbschema.BugTaskImportance.UNDECIDED,
                      'wishlist':  dbschema.BugTaskImportance.WISHLIST,
                      'minor':     dbschema.BugTaskImportance.LOW,
                      'normal':    dbschema.BugTaskImportance.MEDIUM,
                      'important': dbschema.BugTaskImportance.HIGH,
                      'serious':   dbschema.BugTaskImportance.HIGH,
                      'grave':     dbschema.BugTaskImportance.HIGH,
                      'critical':  dbschema.BugTaskImportance.CRITICAL}

def bugtask_sort_key(bugtask):
    """A sort key for a set of bugtasks. We want:

          - products first, followed by their productseries tasks
          - distro tasks, followed by their distrorelease tasks
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

    if bugtask.distrorelease:
        distrorelease_name = bugtask.distrorelease.version
        distribution_name = bugtask.distrorelease.distribution.name
    else:
        distrorelease_name = None

    if bugtask.sourcepackagename:
        sourcepackage_name = bugtask.sourcepackagename.name
    else:
        sourcepackage_name = None

    # Move ubuntu to the top.
    if distribution_name == 'ubuntu':
        distribution_name = '-'

    return (
        bugtask.bug.id, distribution_name, product_name, productseries_name,
        distrorelease_name, sourcepackage_name)


class BugTask(SQLBase, BugTaskMixin):
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = ['distribution', 'product', 'productseries',
                     'distrorelease', 'milestone', 'sourcepackagename']
    _CONJOINED_ATTRIBUTES = (
        "status", "importance", "assignee", "milestone",
        "date_assigned", "date_confirmed", "date_inprogress",
        "date_closed")
    _NON_CONJOINED_STATUSES = (dbschema.BugTaskStatus.REJECTED,)

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
    distrorelease = ForeignKey(
        dbName='distrorelease', foreignKey='DistroRelease',
        notNull=False, default=None)
    milestone = ForeignKey(
        dbName='milestone', foreignKey='Milestone',
        notNull=False, default=None)
    status = EnumCol(
        dbName='status', notNull=True,
        schema=dbschema.BugTaskStatus,
        default=dbschema.BugTaskStatus.UNCONFIRMED)
    statusexplanation = StringCol(dbName='statusexplanation', default=None)
    importance = EnumCol(
        dbName='importance', notNull=True,
        schema=dbschema.BugTaskImportance,
        default=dbschema.BugTaskImportance.UNDECIDED)
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
    owner = ForeignKey(foreignKey='Person', dbName='owner', notNull=True)
    # The targetnamecache is a value that is only supposed to be set when a
    # bugtask is created/modified or by the update-bugtask-targetnamecaches
    # cronscript. For this reason it's not exposed in the interface, and
    # client code should always use the targetname read-only property.
    targetnamecache = StringCol(
        dbName='targetnamecache', notNull=False, default=None)

    @property
    def bug_subscribers(self):
        return self.bug.getDirectSubscribers() + self.bug.getIndirectSubscribers()

    @property
    def age(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)

        return now - self.datecreated

    # Several other classes need to generate lists of bug tasks, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc
    #
    # Note that this definition and SQL should be kept in sync with the
    # BugTask.is_complete property below.
    completeness_clause =  """
                BugTask.status IN ( %d, %d )
                """ % (
                    dbschema.BugTaskStatus.REJECTED.value,
                    dbschema.BugTaskStatus.FIXRELEASED.value,
                    )

    @property
    def is_complete(self):
        """See IBugTask. Note that this should be kept in sync with the
        completeness_clause above."""
        return self.status in (
            dbschema.BugTaskStatus.REJECTED,
            dbschema.BugTaskStatus.FIXRELEASED,
            )

    @property
    def conjoined_master(self):
        """See IBugTask."""
        conjoined_master = None
        if (IDistroBugTask.providedBy(self) and
            self.distribution.currentrelease is not None):
            current_release = self.distribution.currentrelease
            for bt in shortlist(self.bug.bugtasks):
                if (bt.distrorelease == current_release and
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
        """See IBugTask."""
        conjoined_slave = None
        if IDistroReleaseBugTask.providedBy(self):
            distribution = self.distrorelease.distribution
            if self.distrorelease != distribution.currentrelease:
                # Only current release tasks are conjoined.
                return None
            sourcepackagename = self.sourcepackagename
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
    # XXX: Conjoined bugtask synching methods. We override these methods
    # individually, to avoid cycle problems if we were to override
    # _SO_setValue instead. This indicates either a bug or design issue
    # in SQLObject. -- Bjorn Tillenius, 2006-10-31
    # Each attribute listed in _CONJOINED_ATTRIBUTES should have a
    # _set_foo method below.
    def _set_status(self, value):
        if value not in self._NON_CONJOINED_STATUSES:
            self._setValueAndUpdateConjoinedBugTask("status", value)
        else:
            self._SO_set_status(value)

    def _set_assignee(self, value):
        self._setValueAndUpdateConjoinedBugTask("assignee", value)

    def _set_importance(self, value):
        self._setValueAndUpdateConjoinedBugTask("importance", value)

    def _set_milestone(self, value):
        self._setValueAndUpdateConjoinedBugTask("milestone", value)

    def _set_sourcepackagename(self, value):
        old_sourcepackagename = self.sourcepackagename
        self._setValueAndUpdateConjoinedBugTask("sourcepackagename", value)
        self._syncSourcePackages(old_sourcepackagename)

    def _syncSourcePackages(self, prev_sourcepackagename):
        """Synchronize changes to source packages with other distrotasks.

        If one distroreleasetask's source package is changed, all the
        other distroreleasetasks with the same distribution and source
        package has to be changed, as well as the corresponding
        distrotask.
        """
        if self.distrorelease is not None:
            distribution = self.distrorelease.distribution
        else:
            distribution = self.distribution
        if distribution is not None:
            for bugtask in self.related_tasks:
                if bugtask.distrorelease:
                    related_distribution = bugtask.distrorelease.distribution
                else:
                    related_distribution = bugtask.distribution
                if (related_distribution == distribution and
                    bugtask.sourcepackagename == prev_sourcepackagename):
                    bugtask.sourcepackagename = self.sourcepackagename

    def _set_date_assigned(self, value):
        self._setValueAndUpdateConjoinedBugTask("date_assigned", value)

    def _set_date_confirmed(self, value):
        self._setValueAndUpdateConjoinedBugTask("date_confirmed", value)

    def _set_date_inprogress(self, value):
        self._setValueAndUpdateConjoinedBugTask("date_inprogress", value)

    def _set_date_closed(self, value):
        self._setValueAndUpdateConjoinedBugTask("date_closed", value)

    def _setValueAndUpdateConjoinedBugTask(self, colname, value):
        if self._isConjoinedBugTask():
            raise ConjoinedBugTaskEditError(
                "This task cannot be edited directly.")
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
        # XXX: we should use a specific SQLObject API here to avoid the
        # privacy violation.
        #   -- kiko, 2006-03-21
        if self.productID is not None:
            alsoProvides(self, IUpstreamBugTask)
        elif self.productseriesID is not None:
            alsoProvides(self, IProductSeriesBugTask)
        elif self.distroreleaseID is not None:
            alsoProvides(self, IDistroReleaseBugTask)
        elif self.distributionID is not None:
            # If nothing else, this is a distro task.
            alsoProvides(self, IDistroBugTask)
        else:
            raise AssertionError, "Task %d is floating" % self.id

    @property
    def target_uses_malone(self):
        """See IBugTask"""
        if IUpstreamBugTask.providedBy(self):
            root_target = self.product
        elif IProductSeriesBugTask.providedBy(self):
            root_target = self.productseries.product
        elif IDistroReleaseBugTask.providedBy(self):
            root_target = self.distrorelease.distribution
        elif IDistroBugTask.providedBy(self):
            root_target = self.distribution
        else:
            raise AssertionError, "Task %d is floating" % self.id
        return bool(root_target.official_malone)

    def _SO_setValue(self, name, value, fromPython, toPython):
        SQLBase._SO_setValue(self, name, value, fromPython, toPython)

        # The bug target may have just changed, so update the
        # targetnamecache.
        if name != 'targetnamecache':
            self.updateTargetNameCache()

    def set(self, **kw):
        # We need to overwrite this method to make sure the targetnamecache
        # column is updated when multiple attributes of a bugtask are
        # modified. We can't rely on event subscribers for doing this because
        # they can run in a unpredictable order.
        SQLBase.set(self, **kw)
        # We also can't simply update kw with the value we want for
        # targetnamecache because we need to access bugtask attributes
        # that may be available only after SQLBase.set() is called.
        SQLBase.set(self, **{'targetnamecache': self.target.bugtargetname})

    def setImportanceFromDebbugs(self, severity):
        """See canonical.launchpad.interfaces.IBugTask."""
        try:
            self.importance = debbugsseveritymap[severity]
        except KeyError:
            raise ValueError('Unknown debbugs severity "%s"' % severity)
        return self.importance

    def transitionToStatus(self, new_status):
        """See canonical.launchpad.interfaces.IBugTask."""
        if not new_status:
            # This is mainly to facilitate tests which, unlike the
            # normal status form, don't always submit a status when
            # testing the edit form.
            return

        if self.status == new_status:
            # No change in the status, so nothing to do.
            return

        old_status = self.status
        self.status = new_status

        if new_status == dbschema.BugTaskStatus.UNKNOWN:
            # Ensure that all status-related dates are cleared,
            # because it doesn't make sense to have any values set for
            # date_confirmed, date_closed, etc. when the status
            # becomes UNKNOWN.
            self.date_confirmed = None
            self.date_inprogress = None
            self.date_closed = None

            return

        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)

        # Record the date of the particular kinds of transitions into
        # certain states.
        if ((old_status.value < dbschema.BugTaskStatus.CONFIRMED.value) and
            (new_status.value >= dbschema.BugTaskStatus.CONFIRMED.value)):
            # Even if the bug task skips the Confirmed status
            # (e.g. goes directly to Fix Committed), we'll record a
            # confirmed date at the same time anyway, otherwise we get
            # a strange gap in our data, and potentially misleading
            # reports.
            self.date_confirmed = now

        if ((old_status.value < dbschema.BugTaskStatus.INPROGRESS.value) and
            (new_status.value >= dbschema.BugTaskStatus.INPROGRESS.value)):
            # Same idea with In Progress as the comment above about
            # Confirmed.
            self.date_inprogress = now

        if ((old_status in UNRESOLVED_BUGTASK_STATUSES) and
            (new_status in RESOLVED_BUGTASK_STATUSES)):
            self.date_closed = now

        # Ensure that we don't have dates recorded for state
        # transitions, if the bugtask has regressed to an earlier
        # workflow state. We want to ensure that, for example, a
        # bugtask that went Unconfirmed => Confirmed => Unconfirmed
        # has a dateconfirmed value of None.
        if new_status in UNRESOLVED_BUGTASK_STATUSES:
            self.date_closed = None

        if new_status < dbschema.BugTaskStatus.CONFIRMED:
            self.date_confirmed = None

        if new_status < dbschema.BugTaskStatus.INPROGRESS:
            self.date_inprogress = None

    def transitionToAssignee(self, assignee):
        """See canonical.launchpad.interfaces.IBugTask."""
        if assignee == self.assignee:
            # No change to the assignee, so nothing to do.
            return

        UTC = pytz.timezone('UTC')
        now = datetime.datetime.now(UTC)
        if self.assignee and not assignee:
            # The assignee is being cleared, so clear the dateassigned
            # value.
            self.date_assigned = None
        if not self.assignee and assignee:
            # The task is going from not having an assignee to having
            # one, so record when this happened
            self.date_assigned = now

        self.assignee = assignee

    def updateTargetNameCache(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        targetname = self.target.bugtargetname
        if self.targetnamecache != targetname:
            self.targetnamecache = targetname

    def asEmailHeaderValue(self):
        """See canonical.launchpad.interfaces.IBugTask."""
        # Calculate an appropriate display value for the assignee.
        if self.assignee:
            if self.assignee.preferredemail:
                assignee_value = self.assignee.preferredemail.email
            else:
                # There is an assignee with no preferredemail, so we'll
                # "degrade" to the assignee.name. This might happen for teams
                # that don't have associated emails or when a bugtask was
                # imported from an external source and had its assignee set
                # automatically, even though the assignee may not even know they
                # have an account in Launchpad. :)
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
                currentrelease = self.target.currentrelease.sourcepackagerelease

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
        elif IDistroReleaseBugTask.providedBy(self):
            header_value = ((
                'distribution=%(distroname)s; '
                'distrorelease=%(distroreleasename)s; '
                'sourcepackage=%(sourcepackagename)s; '
                'component=%(componentname)s;') %
                {'distroname': self.distrorelease.distribution.name,
                 'distroreleasename': self.distrorelease.name,
                 'sourcepackagename': sourcepackagename_value,
                 'componentname': component})
        else:
            raise AssertionError('Unknown BugTask context: %r' % self)

        header_value += ((
            ' status=%(status)s; importance=%(importance)s; '
            'assignee=%(assignee)s;') %
            {'status': self.status.title,
             'importance': self.importance.title,
             'assignee': assignee_value})

        return header_value


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

    title = "A set of bug tasks"

    def get(self, task_id):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        try:
            bugtask = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist" %
                                str(task_id))
        return bugtask

    def findSimilar(self, user, summary, product=None, distribution=None,
                    sourcepackagename=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
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

        search_params.searchtext = nl_phrase_search(
            summary, Bug, ' AND '.join(constraint_clauses), ['BugTask'])
        return self.search(search_params)

    def search(self, params):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        assert isinstance(params, BugTaskSearchParams)

        extra_clauses = ['Bug.id = BugTask.bug']
        clauseTables = ['BugTask', 'Bug']

        # These arguments can be processed in a loop without any other
        # special handling.
        standard_args = {
            'bug': params.bug,
            'status': params.status,
            'importance': params.importance,
            'product': params.product,
            'distribution': params.distribution,
            'distrorelease': params.distrorelease,
            'productseries': params.productseries,
            'milestone': params.milestone,
            'assignee': params.assignee,
            'sourcepackagename': params.sourcepackagename,
            'owner': params.owner,
        }
        # Loop through the standard, "normal" arguments and build the
        # appropriate SQL WHERE clause. Note that arg_value will be one
        # of:
        #
        # * a searchbuilder.any object, representing a set of acceptable filter
        #   values
        # * a searchbuilder.NULL object
        # * an sqlobject
        # * a dbschema item
        # * None (meaning no filter criteria specified for that arg_name)
        #
        # XXX: is this a good candidate for becoming infrastructure in
        # canonical.database.sqlbase?
        #   -- kiko, 2006-03-16
        for arg_name, arg_value in standard_args.items():
            if arg_value is None:
                continue
            where_cond = search_value_to_where_condition(arg_value)
            if where_cond is not None:
                extra_clauses.append("BugTask.%s %s" % (arg_name, where_cond))

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
            searchtext_quoted = sqlvalues(params.searchtext)[0]
            searchtext_like_quoted = quote_like(params.searchtext)
            extra_clauses.append(
                "((Bug.fti @@ ftq(%s) OR BugTask.fti @@ ftq(%s)) OR"
                " (BugTask.targetnamecache ILIKE '%%' || %s || '%%'))" % (
                searchtext_quoted, searchtext_quoted, searchtext_like_quoted))
            if params.orderby is None:
                # Unordered search results aren't useful, so sort by relevance
                # instead.
                params.orderby = [
                    SQLConstant("-rank(Bug.fti, ftq(%s))" % searchtext_quoted),
                    SQLConstant(
                        "-rank(BugTask.fti, ftq(%s))" % searchtext_quoted)]

        if params.subscriber is not None:
            clauseTables.append('BugSubscription')
            extra_clauses.append("""Bug.id = BugSubscription.bug AND
                    BugSubscription.person = %(personid)s""" %
                    sqlvalues(personid=params.subscriber.id))

        if params.component:
            clauseTables += ["SourcePackagePublishingHistory",
                             "SourcePackageRelease"]
            distrorelease = None
            if params.distribution:
                distrorelease = params.distribution.currentrelease
            elif params.distrorelease:
                distrorelease = params.distrorelease
            assert distrorelease, (
                "Search by component requires a context with a distribution "
                "or distrorelease")

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
            SourcePackagePublishingHistory.component IN %s AND
            SourcePackagePublishingHistory.status = %s
            """ % sqlvalues(distrorelease, component_ids,
                            dbschema.PackagePublishingStatus.PUBLISHED)])

        if params.pending_bugwatch_elsewhere:
            # Include only bugtasks that have other bugtasks on targets
            # not using Malone, which are not Rejected, and have no bug
            # watch.
            pending_bugwatch_elsewhere_clause = """
                EXISTS (
                    SELECT TRUE FROM BugTask AS RelatedBugTask
                    LEFT OUTER JOIN Distribution AS OtherDistribution
                        ON RelatedBugTask.distribution = OtherDistribution.id
                    LEFT OUTER JOIN Product AS OtherProduct
                        ON RelatedBugTask.product = OtherProduct.id
                    WHERE RelatedBugTask.bug = BugTask.bug
                        AND RelatedBugTask.id != BugTask.id
                        AND RelatedBugTask.bugwatch IS NULL
                        AND (
                            OtherDistribution.official_malone IS FALSE
                            OR OtherProduct.official_malone IS FALSE
                            )
                        AND RelatedBugTask.status != %s
                    )
                """ % sqlvalues(dbschema.BugTaskStatus.REJECTED)

            extra_clauses.append(pending_bugwatch_elsewhere_clause)

        if params.has_no_upstream_bugtask:
            has_no_upstream_bugtask_clause = """
                BugTask.bug NOT IN (
                    SELECT DISTINCT bug FROM BugTask
                    WHERE product IS NOT NULL)
            """
            extra_clauses.append(has_no_upstream_bugtask_clause)

        # Our definition of "resolved upstream" means:
        #
        # * bugs with bugtasks linked to watches that are rejected,
        #   fixed committed or fix released
        #
        # * bugs with upstream bugtasks that are fix committed or fix released
        #
        # This definition of "resolved upstream" should address the use
        # cases we gathered at UDS Paris (and followup discussions with
        # seb128, sfllaw, et al.)
        if params.only_resolved_upstream:
            statuses_for_watch_tasks = [
                dbschema.BugTaskStatus.REJECTED,
                dbschema.BugTaskStatus.FIXCOMMITTED,
                dbschema.BugTaskStatus.FIXRELEASED]
            statuses_for_upstream_tasks = [
                dbschema.BugTaskStatus.FIXCOMMITTED,
                dbschema.BugTaskStatus.FIXRELEASED]

            only_resolved_upstream_clause = """
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
                """ % (
                    search_value_to_where_condition(
                        any(*statuses_for_watch_tasks)),
                    search_value_to_where_condition(
                        any(*statuses_for_upstream_tasks)))
            extra_clauses.append(only_resolved_upstream_clause)

        if params.tag:
            tags_clause = "BugTag.bug = BugTask.bug AND BugTag.tag %s" % (
                    search_value_to_where_condition(params.tag))
            extra_clauses.append(tags_clause)
            clauseTables.append('BugTag')

        clause = get_bug_privacy_filter(params.user)
        if clause:
            extra_clauses.append(clause)

        orderby_arg = self._processOrderBy(params)

        query = " AND ".join(extra_clauses)
        bugtasks = BugTask.select(
            query, prejoinClauseTables=["Bug"], clauseTables=clauseTables,
            prejoins=['sourcepackagename', 'product'],
            orderBy=orderby_arg)

        return bugtasks

    def createTask(self, bug, owner, product=None, productseries=None,
                   distribution=None, distrorelease=None,
                   sourcepackagename=None,
                   status=IBugTask['status'].default,
                   importance=IBugTask['importance'].default,
                   assignee=None, milestone=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
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

        assert (product or productseries or distribution or distrorelease), (
            'Got no bugtask target')

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
            distrorelease=distrorelease,
            sourcepackagename=sourcepackagename,
            **non_target_create_params)

        if distribution:
            # Create tasks for accepted nominations if this is a source
            # package addition.
            accepted_nominations = [
                nomination for nomination in bug.getNominations(distribution)
                if nomination.isApproved()]
            for nomination in accepted_nominations:
                accepted_release_task = BugTask(
                    distrorelease=nomination.distrorelease,
                    sourcepackagename=sourcepackagename,
                    **non_target_create_params)

        if bugtask.conjoined_slave:
            bugtask._syncFromConjoinedSlave()

        return bugtask

    def maintainedBugTasks(self, person, minimportance=None,
                           showclosed=False, orderBy=None, user=None):
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        filters = ['BugTask.bug = Bug.id',
                   'BugTask.product = Product.id',
                   'Product.owner = TeamParticipation.team',
                   'TeamParticipation.person = %s' % person.id]

        if not showclosed:
            committed = dbschema.BugTaskStatus.FIXCOMMITTED
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
        """See canonical.launchpad.interfaces.IBugTaskSet."""
        return self._ORDERBY_COLUMN[col_name]

    def _processOrderBy(self, params):
        # Process the orderby parameter supplied to search(), ensuring
        # the sort order will be stable, and converting the string
        # supplied to actual column names.
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
            (params.distrorelease and params.sourcepackagename)):
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
        """DO NOT USE THIS METHOD. For details, see IBugTaskSet"""
        return BugTask.select()



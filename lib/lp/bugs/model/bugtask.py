# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0611,W0212

"""Classes that implement IBugTask and its related interfaces."""

__metaclass__ = type

__all__ = [
    'BugTaskDelta',
    'BugTaskToBugAdapter',
    'BugTask',
    'BugTaskSet',
    'bugtask_sort_key',
    'bug_target_from_key',
    'bug_target_to_key',
    'get_bug_privacy_filter',
    'get_related_bugtasks_search_params',
    'search_value_to_where_condition',
    'validate_new_target',
    'validate_target',
    ]


import datetime
from itertools import chain
from operator import attrgetter
import re

from lazr.enum import BaseItem
from lazr.lifecycle.event import (
    ObjectDeletedEvent,
    ObjectModifiedEvent,
    )
from lazr.lifecycle.snapshot import Snapshot
import pytz
from sqlobject import (
    ForeignKey,
    IntCol,
    SQLObjectNotFound,
    StringCol,
    )
from sqlobject.sqlbuilder import SQLConstant
from storm.expr import (
    Alias,
    And,
    Desc,
    In,
    Join,
    LeftJoin,
    Not,
    Or,
    Select,
    SQL,
    Sum,
    )
from storm.info import ClassAlias
from storm.store import (
    EmptyResultSet,
    Store,
    )
from zope.component import getUtility
from zope.event import notify
from zope.interface import (
    implements,
    providedBy,
    )
from zope.security.proxy import (
    isinstance as zope_isinstance,
    removeSecurityProxy,
    )

from canonical.config import config
from canonical.database.constants import UTC_NOW
from canonical.database.datetimecol import UtcDateTimeCol
from canonical.database.enumcol import EnumCol
from canonical.database.nl_search import nl_phrase_search
from canonical.database.sqlbase import (
    block_implicit_flushes,
    convert_storm_clause_to_string,
    cursor,
    quote,
    quote_like,
    SQLBase,
    sqlvalues,
    )
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.helpers import shortlist
from canonical.launchpad.interfaces.lpstorm import IStore
from canonical.launchpad.searchbuilder import (
    all,
    any,
    greater_than,
    not_equals,
    NULL,
    )
from canonical.launchpad.webapp.interfaces import (
    DEFAULT_FLAVOR,
    ILaunchBag,
    IStoreSelector,
    MAIN_STORE,
    )
from lp.app.enums import ServiceUsage
from lp.app.errors import NotFoundError
from lp.app.interfaces.launchpad import ILaunchpadCelebrities
from lp.bugs.interfaces.bug import IBugSet
from lp.bugs.interfaces.bugattachment import BugAttachmentType
from lp.bugs.interfaces.bugnomination import BugNominationStatus
from lp.bugs.interfaces.bugtask import (
    BUG_SUPERVISOR_BUGTASK_STATUSES,
    BugBlueprintSearch,
    BugBranchSearch,
    BugTaskImportance,
    BugTaskSearchParams,
    BugTaskStatus,
    BugTaskStatusSearch,
    CannotDeleteBugtask,
    DB_INCOMPLETE_BUGTASK_STATUSES,
    DB_UNRESOLVED_BUGTASK_STATUSES,
    get_bugtask_status,
    IBugTask,
    IBugTaskDelta,
    IBugTaskSet,
    IllegalRelatedBugTasksParams,
    IllegalTarget,
    normalize_bugtask_status,
    RESOLVED_BUGTASK_STATUSES,
    UserCannotEditBugTaskAssignee,
    UserCannotEditBugTaskImportance,
    UserCannotEditBugTaskMilestone,
    UserCannotEditBugTaskStatus,
    )
from lp.bugs.model.bugnomination import BugNomination
from lp.bugs.model.bugsubscription import BugSubscription
from lp.registry.interfaces.distribution import (
    IDistribution,
    IDistributionSet,
    )
from lp.registry.interfaces.distributionsourcepackage import (
    IDistributionSourcePackage,
    )
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.milestone import (
    IMilestoneSet,
    IProjectGroupMilestone,
    )
from lp.registry.interfaces.person import (
    IPerson,
    validate_person,
    validate_public_person,
    )
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.productseries import IProductSeries
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.role import IPersonRoles
from lp.registry.interfaces.sourcepackage import ISourcePackage
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from lp.registry.model.pillar import pillar_sort_key
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services import features
from lp.services.propertycache import get_property_cache
from lp.soyuz.enums import PackagePublishingStatus
from lp.blueprints.model.specification import Specification


debbugsseveritymap = {
    None: BugTaskImportance.UNDECIDED,
    'wishlist': BugTaskImportance.WISHLIST,
    'minor': BugTaskImportance.LOW,
    'normal': BugTaskImportance.MEDIUM,
    'important': BugTaskImportance.HIGH,
    'serious': BugTaskImportance.HIGH,
    'grave': BugTaskImportance.HIGH,
    'critical': BugTaskImportance.CRITICAL,
    }


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


def get_related_bugtasks_search_params(user, context, **kwargs):
    """Returns a list of `BugTaskSearchParams` which can be used to
    search for all tasks related to a user given by `context`.

    Which tasks are related to a user?
      * the user has to be either assignee or owner of this task
        OR
      * the user has to be subscriber or commenter to the underlying bug
        OR
      * the user is reporter of the underlying bug, but this condition
        is automatically fulfilled by the first one as each new bug
        always get one task owned by the bug reporter
    """
    assert IPerson.providedBy(context), "Context argument needs to be IPerson"
    relevant_fields = ('assignee', 'bug_subscriber', 'owner', 'bug_commenter',
                       'structural_subscriber')
    search_params = []
    for key in relevant_fields:
        # all these parameter default to None
        user_param = kwargs.get(key)
        if user_param is None or user_param == context:
            # we are only creating a `BugTaskSearchParams` object if
            # the field is None or equal to the context
            arguments = kwargs.copy()
            arguments[key] = context
            if key == 'owner':
                # Specify both owner and bug_reporter to try to
                # prevent the same bug (but different tasks)
                # being displayed.
                # see `PersonRelatedBugTaskSearchListingView.searchUnbatched`
                arguments['bug_reporter'] = context
            search_params.append(
                BugTaskSearchParams.fromSearchForm(user, **arguments))
    if len(search_params) == 0:
        # unable to search for related tasks to user_context because user
        # modified the query in an invalid way by overwriting all user
        # related parameters
        raise IllegalRelatedBugTasksParams(
            ('Cannot search for related tasks to \'%s\', at least one '
             'of these parameter has to be empty: %s'
                % (context.name, ", ".join(relevant_fields))))
    return search_params


def bug_target_from_key(product, productseries, distribution, distroseries,
                        sourcepackagename):
    """Returns the IBugTarget defined by the given DB column values."""
    if product:
        return product
    elif productseries:
        return productseries
    elif distribution:
        if sourcepackagename:
            return distribution.getSourcePackage(
                sourcepackagename)
        else:
            return distribution
    elif distroseries:
        if sourcepackagename:
            return distroseries.getSourcePackage(
                sourcepackagename)
        else:
            return distroseries
    else:
        raise AssertionError("Unable to determine bugtask target.")


def bug_target_to_key(target):
    """Returns the DB column values for an IBugTarget."""
    values = dict(
                product=None,
                productseries=None,
                distribution=None,
                distroseries=None,
                sourcepackagename=None,
                )
    if IProduct.providedBy(target):
        values['product'] = target
    elif IProductSeries.providedBy(target):
        values['productseries'] = target
    elif IDistribution.providedBy(target):
        values['distribution'] = target
    elif IDistroSeries.providedBy(target):
        values['distroseries'] = target
    elif IDistributionSourcePackage.providedBy(target):
        values['distribution'] = target.distribution
        values['sourcepackagename'] = target.sourcepackagename
    elif ISourcePackage.providedBy(target):
        values['distroseries'] = target.distroseries
        values['sourcepackagename'] = target.sourcepackagename
    else:
        raise AssertionError("Not an IBugTarget.")
    return values


class BugTaskDelta:
    """See `IBugTaskDelta`."""

    implements(IBugTaskDelta)

    def __init__(self, bugtask, status=None, importance=None,
                 assignee=None, milestone=None, bugwatch=None, target=None):
        self.bugtask = bugtask

        self.assignee = assignee
        self.bugwatch = bugwatch
        self.importance = importance
        self.milestone = milestone
        self.status = status
        self.target = target


def BugTaskToBugAdapter(bugtask):
    """Adapt an IBugTask to an IBug."""
    return bugtask.bug


class PassthroughValue:
    """A wrapper to allow setting values on conjoined bug tasks."""

    def __init__(self, value):
        self.value = value


@block_implicit_flushes
def validate_conjoined_attribute(self, attr, value):
    # If the value has been wrapped in a _PassthroughValue instance,
    # then we are being updated by our conjoined master: pass the
    # value through without any checking.
    if isinstance(value, PassthroughValue):
        return value.value

    # Check to see if the object is being instantiated.  This test is specific
    # to SQLBase.  Checking for specific attributes (like self.bug) is
    # insufficient and fragile.
    if self._SO_creating:
        return value

    # If this is a conjoined slave then call setattr on the master.
    # Effectively this means that making a change to the slave will
    # actually make the change to the master (which will then be passed
    # down to the slave, of course). This helps to prevent OOPSes when
    # people try to update the conjoined slave via the API.
    conjoined_master = self.conjoined_master
    if conjoined_master is not None:
        setattr(conjoined_master, attr, value)
        return value

    # If there is a conjoined slave, update that.
    conjoined_bugtask = self.conjoined_slave
    if conjoined_bugtask:
        setattr(conjoined_bugtask, attr, PassthroughValue(value))

    return value


def validate_status(self, attr, value):
    if value not in self._NON_CONJOINED_STATUSES:
        return validate_conjoined_attribute(self, attr, value)
    else:
        return value


def validate_assignee(self, attr, value):
    value = validate_conjoined_attribute(self, attr, value)
    # Check if this person is valid and not None.
    return validate_person(self, attr, value)


def validate_target(bug, target, retarget_existing=True):
    """Validate a bugtask target against a bug's existing tasks.

    Checks that no conflicting tasks already exist, and that the new
    target's pillar matches the bug access policy if one is set.
    """
    if bug.getBugTask(target):
        raise IllegalTarget(
            "A fix for this bug has already been requested for %s"
            % target.displayname)

    # Because we don't have a sensible way to determine a new access
    # policy, it is presently forbidden to transition a task to another
    # pillar.
    if (bug.access_policy is not None and
        target.pillar != bug.access_policy.pillar):
        raise IllegalTarget(
            "%s is not allowed by this bug's access policy."
            % target.pillar.displayname)

    if (IDistributionSourcePackage.providedBy(target) or
        ISourcePackage.providedBy(target)):
        # If the distribution has at least one series, check that the
        # source package has been published in the distribution.
        if (target.sourcepackagename is not None and
            len(target.distribution.series) > 0):
            try:
                target.distribution.guessPublishedSourcePackageName(
                    target.sourcepackagename.name)
            except NotFoundError, e:
                raise IllegalTarget(e[0])

    if bug.private and not bool(features.getFeatureFlag(
            'disclosure.allow_multipillar_private_bugs.enabled')):
        # Perhaps we are replacing the one and only existing bugtask, in
        # which case that's ok.
        if retarget_existing and len(bug.bugtasks) <= 1:
            return
        # We can add a target so long as the pillar exists already.
        if (len(bug.affected_pillars) > 0
                and target.pillar not in bug.affected_pillars):
            raise IllegalTarget(
                "This private bug already affects %s. "
                "Private bugs cannot affect multiple projects."
                    % bug.default_bugtask.target.bugtargetdisplayname)


def validate_new_target(bug, target):
    """Validate a bugtask target to be added.

    Make sure that the isn't already a distribution task without a
    source package, or that such task is added only when the bug doesn't
    already have any tasks for the distribution.

    The same checks as `validate_target` does are also done.
    """
    if IDistribution.providedBy(target):
        # Prevent having a task on only the distribution if there's at
        # least one task already on the distribution, whether or not
        # that task also has a source package.
        distribution_tasks_for_bug = [
            bugtask for bugtask
            in shortlist(bug.bugtasks, longest_expected=50)
            if bugtask.distribution == target]

        if len(distribution_tasks_for_bug) > 0:
            raise IllegalTarget(
                "This bug is already on %s. Please specify an "
                "affected package in which the bug has not yet "
                "been reported." % target.displayname)
    elif IDistributionSourcePackage.providedBy(target):
        # Ensure that there isn't already a generic task open on the
        # distribution for this bug, because if there were, that task
        # should be reassigned to the sourcepackage, rather than a new
        # task opened.
        if bug.getBugTask(target.distribution) is not None:
            raise IllegalTarget(
                "This bug is already open on %s with no package "
                "specified. You should fill in a package name for "
                "the existing bug." % target.distribution.displayname)

    validate_target(bug, target, retarget_existing=False)


class BugTask(SQLBase):
    """See `IBugTask`."""
    implements(IBugTask)
    _table = "BugTask"
    _defaultOrder = ['distribution', 'product', 'productseries',
                     'distroseries', 'milestone', 'sourcepackagename']
    _CONJOINED_ATTRIBUTES = (
        "_status", "importance", "assigneeID", "milestoneID",
        "date_assigned", "date_confirmed", "date_inprogress",
        "date_closed", "date_incomplete", "date_left_new",
        "date_triaged", "date_fix_committed", "date_fix_released",
        "date_left_closed")
    _NON_CONJOINED_STATUSES = (BugTaskStatus.WONTFIX, )

    _inhibit_target_check = False

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
        notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    _status = EnumCol(
        dbName='status', notNull=True,
        schema=(BugTaskStatus, BugTaskStatusSearch),
        default=BugTaskStatus.NEW,
        storm_validator=validate_status)
    importance = EnumCol(
        dbName='importance', notNull=True,
        schema=BugTaskImportance,
        default=BugTaskImportance.UNDECIDED,
        storm_validator=validate_conjoined_attribute)
    assignee = ForeignKey(
        dbName='assignee', foreignKey='Person',
        storm_validator=validate_assignee,
        notNull=False, default=None)
    bugwatch = ForeignKey(dbName='bugwatch', foreignKey='BugWatch',
        notNull=False, default=None)
    date_assigned = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    datecreated = UtcDateTimeCol(notNull=False, default=UTC_NOW)
    date_confirmed = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_inprogress = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_closed = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_incomplete = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_left_new = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_triaged = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_fix_committed = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_fix_released = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    date_left_closed = UtcDateTimeCol(notNull=False, default=None,
        storm_validator=validate_conjoined_attribute)
    heat = IntCol(notNull=True, default=0)
    owner = ForeignKey(
        dbName='owner', foreignKey='Person',
        storm_validator=validate_public_person, notNull=True)
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
    def status(self):
        if self._status in DB_INCOMPLETE_BUGTASK_STATUSES:
            return BugTaskStatus.INCOMPLETE
        return self._status

    @property
    def title(self):
        """See `IBugTask`."""
        return 'Bug #%s in %s: "%s"' % (
            self.bug.id, self.bugtargetdisplayname, self.bug.title)

    @property
    def bug_subscribers(self):
        """See `IBugTask`."""
        return tuple(
            chain(self.bug.getDirectSubscribers(),
                  self.bug.getIndirectSubscribers()))

    @property
    def bugtargetname(self):
        """See `IBugTask`."""
        return self.target.bugtargetname

    @property
    def target(self):
        """See `IBugTask`."""
        return bug_target_from_key(
            self.product, self.productseries, self.distribution,
            self.distroseries, self.sourcepackagename)

    @property
    def related_tasks(self):
        """See `IBugTask`."""
        other_tasks = [
            task for task in self.bug.bugtasks if task != self]

        return other_tasks

    @property
    def pillar(self):
        """See `IBugTask`."""
        return self.target.pillar

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
    def bugtargetdisplayname(self):
        """See `IBugTask`."""
        return self.targetnamecache

    @property
    def age(self):
        """See `IBugTask`."""
        now = datetime.datetime.now(pytz.UTC)

        return now - self.datecreated

    @property
    def task_age(self):
        """See `IBugTask`."""
        return self.age.seconds

    # Several other classes need to generate lists of bug tasks, and
    # one thing they often have to filter for is completeness. We maintain
    # this single canonical query string here so that it does not have to be
    # cargo culted into Product, Distribution, ProductSeries etc
    completeness_clause = """
        BugTask.status IN ( %s )
        """ % ','.join([str(a.value) for a in RESOLVED_BUGTASK_STATUSES])

    @property
    def is_complete(self):
        """See `IBugTask`.

        Note that this should be kept in sync with the completeness_clause
        above.
        """
        return self._status in RESOLVED_BUGTASK_STATUSES

    def canBeDeleted(self):
        try:
            self.checkCanBeDeleted()
        except Exception:
            return False
        return True

    def checkCanBeDeleted(self):
        num_bugtasks = Store.of(self).find(
            BugTask, bug=self.bug).count()

        if num_bugtasks < 2:
            raise CannotDeleteBugtask(
                "Cannot delete only bugtask affecting: %s."
                % self.target.bugtargetdisplayname)

    def delete(self, who=None):
        """See `IBugTask`."""
        if who is None:
            who = getUtility(ILaunchBag).user

        # Raise an error if the bugtask cannot be deleted.
        self.checkCanBeDeleted()

        bug = self.bug
        target = self.target
        notify(ObjectDeletedEvent(self, who))
        self.destroySelf()
        del get_property_cache(bug).bugtasks

        # When a task is deleted the bug's heat needs to be recalculated.
        target.recalculateBugHeatCache()

    def findSimilarBugs(self, user, limit=10):
        """See `IBugTask`."""
        if self.product is not None:
            context_params = {'product': self.product}
        elif (self.sourcepackagename is not None and
            self.distribution is not None):
            context_params = {
                'distribution': self.distribution,
                'sourcepackagename': self.sourcepackagename,
                }
        elif self.distribution is not None:
            context_params = {'distribution': self.distribution}
        else:
            raise AssertionError("BugTask doesn't have a searchable target.")

        matching_bugtasks = getUtility(IBugTaskSet).findSimilar(
            user, self.bug.title, **context_params)

        matching_bugs = getUtility(IBugSet).getDistinctBugsForBugTasks(
            matching_bugtasks, user, limit)

        # Make sure to exclude the bug of the current bugtask.
        return [bug for bug in matching_bugs if bug.id != self.bugID]

    def subscribe(self, person, subscribed_by):
        """See `IBugTask`."""
        return self.bug.subscribe(person, subscribed_by)

    def isSubscribed(self, person):
        """See `IBugTask`."""
        return self.bug.isSubscribed(person)

    def _syncSourcePackages(self, new_spn):
        """Synchronize changes to source packages with other distrotasks.

        If one distroseriestask's source package is changed, all the
        other distroseriestasks with the same distribution and source
        package has to be changed, as well as the corresponding
        distrotask.
        """
        if self.bug is None or not (self.distribution or self.distroseries):
            # The validator is being called on a new or non-distro task.
            return
        distribution = self.distribution or self.distroseries.distribution
        for bugtask in self.related_tasks:
            relevant = (
                bugtask.sourcepackagename == self.sourcepackagename and
                distribution in (
                    bugtask.distribution,
                    getattr(bugtask.distroseries, 'distribution', None)))
            if relevant:
                key = bug_target_to_key(bugtask.target)
                key['sourcepackagename'] = new_spn
                bugtask.transitionToTarget(
                    bug_target_from_key(**key),
                    _sync_sourcepackages=False)

    def getContributorInfo(self, user, person):
        """See `IBugTask`."""
        result = {}
        result['is_contributor'] = person.isBugContributorInTarget(
            user, self.pillar)
        result['person_name'] = person.displayname
        result['pillar_name'] = self.pillar.displayname
        return result

    def getConjoinedMaster(self, bugtasks, bugtasks_by_package=None):
        """See `IBugTask`."""
        conjoined_master = None
        if self.distribution:
            if bugtasks_by_package is None:
                bugtasks_by_package = (
                    self.bug.getBugTasksByPackageName(bugtasks))
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
        elif self.product:
            assert self.product.development_focusID is not None, (
                'A product should always have a development series.')
            devel_focusID = self.product.development_focusID
            for bugtask in bugtasks:
                if bugtask.productseriesID == devel_focusID:
                    conjoined_master = bugtask
                    break

        if (conjoined_master is not None and
            conjoined_master.status in self._NON_CONJOINED_STATUSES):
            conjoined_master = None
        return conjoined_master

    def _get_shortlisted_bugtasks(self):
        return shortlist(self.bug.bugtasks, longest_expected=200)

    @property
    def conjoined_master(self):
        """See `IBugTask`."""
        return self.getConjoinedMaster(self._get_shortlisted_bugtasks())

    @property
    def conjoined_slave(self):
        """See `IBugTask`."""
        conjoined_slave = None
        if self.distroseries:
            distribution = self.distroseries.distribution
            if self.distroseries != distribution.currentseries:
                # Only current series tasks are conjoined.
                return None
            for bugtask in self._get_shortlisted_bugtasks():
                if (bugtask.distribution == distribution and
                    bugtask.sourcepackagename == self.sourcepackagename):
                    conjoined_slave = bugtask
                    break
        elif self.productseries:
            product = self.productseries.product
            if self.productseries != product.development_focus:
                # Only development focus tasks are conjoined.
                return None
            for bugtask in self._get_shortlisted_bugtasks():
                if bugtask.product == product:
                    conjoined_slave = bugtask
                    break

        if (conjoined_slave is not None and
            self.status in self._NON_CONJOINED_STATUSES):
            conjoined_slave = None
        return conjoined_slave

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
            setattr(self, synched_attr, PassthroughValue(slave_attr_value))

    @property
    def target_uses_malone(self):
        """See `IBugTask`"""
        # XXX sinzui 2007-10-04 bug=149009:
        # This property is not needed. Code should inline this implementation.
        return (self.pillar.bug_tracking_usage == ServiceUsage.LAUNCHPAD)

    def transitionToMilestone(self, new_milestone, user):
        """See `IBugTask`."""
        if not self.userHasPrivileges(user):
            raise UserCannotEditBugTaskMilestone(
                "User does not have sufficient permissions "
                "to edit the bug task milestone.")
        else:
            self.milestone = new_milestone

    def transitionToImportance(self, new_importance, user):
        """See `IBugTask`."""
        if not self.userHasPrivileges(user):
            raise UserCannotEditBugTaskImportance(
                "User does not have sufficient permissions "
                "to edit the bug task importance.")
        else:
            self.importance = new_importance

    def setImportanceFromDebbugs(self, severity):
        """See `IBugTask`."""
        try:
            self.importance = debbugsseveritymap[severity]
        except KeyError:
            raise ValueError('Unknown debbugs severity "%s".' % severity)
        return self.importance

    # START TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.
    _parse_launchpad_names = re.compile(r"[a-z0-9][a-z0-9\+\.\-]+").findall

    def _checkAutoconfirmFeatureFlag(self):
        """Does a feature flag enable automatic switching of our bugtasks?"""
        # This method should be ripped out if we determine that we like
        # this behavior for all projects.
        # This is a bit of a feature flag hack, but has been discussed as
        # a reasonable way to deploy this quickly.
        pillar = self.pillar
        if IDistribution.providedBy(pillar):
            flag_name = 'bugs.autoconfirm.enabled_distribution_names'
        else:
            assert IProduct.providedBy(pillar), 'unexpected pillar'
            flag_name = 'bugs.autoconfirm.enabled_product_names'
        enabled = features.getFeatureFlag(flag_name)
        if enabled is None:
            return False
        if (enabled.strip() != '*' and
            pillar.name not in self._parse_launchpad_names(enabled)):
            # We are not generically enabled ('*') and our pillar's name
            # is not explicitly enabled.
            return False
        return True
    # END TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.

    def maybeConfirm(self):
        """Maybe confirm this bugtask.
        Only call this if the bug._shouldConfirmBugtasks().
        This adds the further constraint that the bugtask needs to be NEW,
        and not imported from an external bug tracker.
        """
        if (self.status == BugTaskStatus.NEW
            and self.bugwatch is None
            # START TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.
            and self._checkAutoconfirmFeatureFlag()
            # END TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.
            ):
            janitor = getUtility(ILaunchpadCelebrities).janitor
            bugtask_before_modification = Snapshot(
                self, providing=providedBy(self))
            # Create a bug message explaining why the janitor auto-confirmed
            # the bugtask.
            msg = ("Status changed to 'Confirmed' because the bug "
                   "affects multiple users.")
            self.bug.newMessage(owner=janitor, content=msg)
            self.transitionToStatus(BugTaskStatus.CONFIRMED, janitor)
            notify(ObjectModifiedEvent(
                self, bugtask_before_modification, ['status'], user=janitor))

    def canTransitionToStatus(self, new_status, user):
        """See `IBugTask`."""
        new_status = normalize_bugtask_status(new_status)
        if (self.status == BugTaskStatus.FIXRELEASED and
           (user.id == self.bug.ownerID or user.inTeam(self.bug.owner))):
            return True
        elif self.userHasPrivileges(user):
            return True
        else:
            return (self.status not in (
                        BugTaskStatus.WONTFIX, BugTaskStatus.FIXRELEASED)
                    and new_status not in BUG_SUPERVISOR_BUGTASK_STATUSES)

    def transitionToStatus(self, new_status, user, when=None):
        """See `IBugTask`."""
        if not new_status or user is None:
            # This is mainly to facilitate tests which, unlike the
            # normal status form, don't always submit a status when
            # testing the edit form.
            return

        new_status = normalize_bugtask_status(new_status)

        if not self.canTransitionToStatus(new_status, user):
            raise UserCannotEditBugTaskStatus(
                "Only Bug Supervisors may change status to %s." % (
                    new_status.title,))

        if new_status == BugTaskStatus.INCOMPLETE:
            # We store INCOMPLETE as INCOMPLETE_WITHOUT_RESPONSE so that it
            # can be queried on efficiently.
            if (when is None or self.bug.date_last_message is None or
                when > self.bug.date_last_message):
                new_status = BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE
            else:
                new_status = BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE

        if self._status == new_status:
            # No change in the status, so nothing to do.
            return

        old_status = self.status
        self._status = new_status

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

        if when is None:
            when = datetime.datetime.now(pytz.UTC)

        # Record the date of the particular kinds of transitions into
        # certain states.
        if ((old_status < BugTaskStatus.CONFIRMED) and
            (new_status >= BugTaskStatus.CONFIRMED)):
            # Even if the bug task skips the Confirmed status
            # (e.g. goes directly to Fix Committed), we'll record a
            # confirmed date at the same time anyway, otherwise we get
            # a strange gap in our data, and potentially misleading
            # reports.
            self.date_confirmed = when

        if ((old_status < BugTaskStatus.INPROGRESS) and
            (new_status >= BugTaskStatus.INPROGRESS)):
            # Same idea with In Progress as the comment above about
            # Confirmed.
            self.date_inprogress = when

        if (old_status == BugTaskStatus.NEW and
            new_status > BugTaskStatus.NEW and
            self.date_left_new is None):
            # This task is leaving the NEW status for the first time
            self.date_left_new = when

        # If the new status is equal to or higher
        # than TRIAGED, we record a `date_triaged`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.TRIAGED and
            new_status >= BugTaskStatus.TRIAGED):
            # This task is now marked as TRIAGED
            self.date_triaged = when

        # If the new status is equal to or higher
        # than FIXCOMMITTED, we record a `date_fixcommitted`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.FIXCOMMITTED and
            new_status >= BugTaskStatus.FIXCOMMITTED):
            # This task is now marked as FIXCOMMITTED
            self.date_fix_committed = when

        # If the new status is equal to or higher
        # than FIXRELEASED, we record a `date_fixreleased`
        # to mark the fact that the task has passed
        # through this status.
        if (old_status < BugTaskStatus.FIXRELEASED and
            new_status >= BugTaskStatus.FIXRELEASED):
            # This task is now marked as FIXRELEASED
            self.date_fix_released = when

        # Bugs can jump in and out of 'incomplete' status
        # and for just as long as they're marked incomplete
        # we keep a date_incomplete recorded for them.
        if new_status in DB_INCOMPLETE_BUGTASK_STATUSES:
            self.date_incomplete = when
        else:
            self.date_incomplete = None

        if ((old_status in DB_UNRESOLVED_BUGTASK_STATUSES) and
            (new_status in RESOLVED_BUGTASK_STATUSES)):
            self.date_closed = when

        if ((old_status in RESOLVED_BUGTASK_STATUSES) and
            (new_status in DB_UNRESOLVED_BUGTASK_STATUSES)):
            self.date_left_closed = when

        # Ensure that we don't have dates recorded for state
        # transitions, if the bugtask has regressed to an earlier
        # workflow state. We want to ensure that, for example, a
        # bugtask that went New => Confirmed => New
        # has a dateconfirmed value of None.
        if new_status in DB_UNRESOLVED_BUGTASK_STATUSES:
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

    def userCanSetAnyAssignee(self, user):
        """See `IBugTask`."""
        if user is None:
            return False
        elif self.pillar.bug_supervisor is None:
            return True
        else:
            return self.userHasPrivileges(user)

    def userCanUnassign(self, user):
        """True if user can set the assignee to None.

        This option not shown for regular users unless they or their teams
        are the assignees. Project owners, drivers, bug supervisors and
        Launchpad admins can always unassign.
        """
        return user is not None and (
            user.inTeam(self.assignee) or self.userHasPrivileges(user))

    def canTransitionToAssignee(self, assignee):
        """See `IBugTask`."""
        # All users can assign and unassign themselves and their teams,
        # but only project owners, bug supervisors, project/distribution
        # drivers and Launchpad admins can assign others.
        user = getUtility(ILaunchBag).user
        return (
            user is not None and (
                user.inTeam(assignee) or
                (assignee is None and self.userCanUnassign(user)) or
                self.userCanSetAnyAssignee(user)))

    def transitionToAssignee(self, assignee):
        """See `IBugTask`."""
        if assignee == self.assignee:
            # No change to the assignee, so nothing to do.
            return

        if not self.canTransitionToAssignee(assignee):
            raise UserCannotEditBugTaskAssignee(
                'Regular users can assign and unassign only themselves and '
                'their teams. Only project owners, bug supervisors, drivers '
                'and release managers can assign others.')

        now = datetime.datetime.now(pytz.UTC)
        if self.assignee and not assignee:
            # The assignee is being cleared, so clear the date_assigned
            # value.
            self.date_assigned = None
            # The bugtask is unassigned, so clear the _known_viewer cached
            # property for the bug. Retain the current assignee as a viewer so
            # that they are able to unassign themselves and get confirmation
            # that that worked.
            get_property_cache(self.bug)._known_viewers = set(
                [self.assignee.id])
        if not self.assignee and assignee:
            # The task is going from not having an assignee to having
            # one, so record when this happened
            self.date_assigned = now

        self.assignee = assignee
        # Invalidate the old visibility cache for this bug and replace it with
        # the new assignee.
        if self.assignee is not None:
            get_property_cache(self.bug)._known_viewers = set(
                [self.assignee.id])

    def validateTransitionToTarget(self, target):
        """See `IBugTask`."""
        from lp.registry.model.distroseries import DistroSeries

        # Check if any series are involved. You can't retarget series
        # tasks. Except for DistroSeries/SourcePackage tasks, which can
        # only be retargetted to another SourcePackage in the same
        # DistroSeries, or the DistroSeries.
        interfaces = set(providedBy(target))
        interfaces.update(providedBy(self.target))
        if IProductSeries in interfaces:
            raise IllegalTarget(
                "Series tasks may only be created by approving nominations.")
        elif interfaces.intersection((IDistroSeries, ISourcePackage)):
            series = set()
            for potential_target in (target, self.target):
                if IDistroSeries.providedBy(potential_target):
                    series.add(potential_target)
                elif ISourcePackage.providedBy(potential_target):
                    series.add(potential_target.distroseries)
                else:
                    series = set()
                    break
            if len(series) != 1:
                raise IllegalTarget(
                    "Distribution series tasks may only be retargeted "
                    "to a package within the same series.")
        # Because of the mildly insane way that DistroSeries nominations
        # work (they affect all Distributions and
        # DistributionSourcePackages), we can't sensibly allow
        # pillar changes to/from distributions with series tasks on this
        # bug. That would require us to create or delete tasks.
        # Changing just the sourcepackagename is OK, though, as a
        # validator on sourcepackagename will change all related tasks.
        elif interfaces.intersection(
            (IDistribution, IDistributionSourcePackage)):
            # Work out the involved distros (will include None if there
            # are product tasks).
            distros = set()
            for potential_target in (target, self.target):
                if IDistribution.providedBy(potential_target.pillar):
                    distros.add(potential_target.pillar)
                else:
                    distros.add(None)
            if len(distros) > 1:
                # Multiple distros involved. Check that none of their
                # series have tasks on this bug.
                if not Store.of(self).find(
                    BugTask,
                    BugTask.bugID == self.bugID,
                    BugTask.distroseriesID == DistroSeries.id,
                    DistroSeries.distributionID.is_in(
                        distro.id for distro in distros if distro),
                    ).is_empty():
                    raise IllegalTarget(
                        "Distribution tasks with corresponding series "
                        "tasks may only be retargeted to a different "
                        "package.")

        validate_target(self.bug, target)

    def transitionToTarget(self, target, _sync_sourcepackages=True):
        """See `IBugTask`.

        If _sync_sourcepackages is True (the default) and the
        sourcepackagename is being changed, any other tasks for the same
        name in this distribution will have their names updated to
        match. This should only be used by _syncSourcePackages.
        """
        if self.target == target:
            return

        self.validateTransitionToTarget(target)

        target_before_change = self.target

        if (self.milestone is not None and
            self.milestone.target != target.pillar):
            # If the milestone for this bugtask is set, we
            # have to make sure that it's a milestone of the
            # current target, or reset it to None
            self.milestone = None

        new_key = bug_target_to_key(target)

        # As a special case, if the sourcepackagename has changed then
        # we update any other tasks for the same distribution and
        # sourcepackagename. This keeps series tasks consistent.
        if (_sync_sourcepackages and
            new_key['sourcepackagename'] != self.sourcepackagename):
            self._syncSourcePackages(new_key['sourcepackagename'])

        for name, value in new_key.iteritems():
            setattr(self, name, value)
        self.updateTargetNameCache()

        # After the target has changed, we need to recalculate the maximum bug
        # heat for the new and old targets.
        if self.target != target_before_change:
            target_before_change.recalculateBugHeatCache()
            self.target.recalculateBugHeatCache()
            # START TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.
            # We also should see if we ought to auto-transition to the
            # CONFIRMED status.
            if self.bug.shouldConfirmBugtasks():
                self.maybeConfirm()
            # END TEMPORARY BIT FOR BUGTASK AUTOCONFIRM FEATURE FLAG.

    def updateTargetNameCache(self, newtarget=None):
        """See `IBugTask`."""
        if newtarget is None:
            newtarget = self.target
        targetname = newtarget.bugtargetdisplayname
        if self.targetnamecache != targetname:
            self.targetnamecache = targetname

    def getPackageComponent(self):
        """See `IBugTask`."""
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

        if self.product:
            header_value = 'product=%s;' % self.target.name
        elif self.productseries:
            header_value = 'product=%s; productseries=%s;' % (
                self.productseries.product.name, self.productseries.name)
        elif self.distribution:
            header_value = ((
                'distribution=%(distroname)s; '
                'sourcepackage=%(sourcepackagename)s; '
                'component=%(componentname)s;') %
                {'distroname': self.distribution.name,
                 'sourcepackagename': sourcepackagename_value,
                 'componentname': component_name})
        elif self.distroseries:
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
        # calculate the differences in the fields that both types of tasks
        # have in common
        changes = {}
        for field_name in ("target", "status", "importance",
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

    def userHasPrivileges(self, user):
        """See `IBugTask`."""
        if not user:
            return False
        role = IPersonRoles(user)
        # Admins can always change bug details.
        if role.in_admin:
            return True

        # Similar to admins, the Bug Watch Updater, Bug Importer and 
        # Janitor can always change bug details.
        if (
            role.in_bug_watch_updater or role.in_bug_importer or
            role.in_janitor):
            return True

        # Otherwise, if you're a member of the pillar owner, drivers, or the
        # bug supervisor, you can change bug details.
        return (
            role.isOwner(self.pillar) or role.isOneOfDrivers(self.pillar) or
            role.isBugSupervisor(self.pillar) or
            (self.distroseries is not None and
                role.isDriver(self.distroseries)) or
            (self.productseries is not None and
                role.isDriver(self.productseries)))

    def __repr__(self):
        return "<BugTask for bug %s on %r>" % (self.bugID, self.target)


def search_value_to_where_condition(search_value):
    """Convert a search value to a WHERE condition.

        >>> search_value_to_where_condition(any(1, 2, 3))
        'IN (1,2,3)'
        >>> search_value_to_where_condition(any()) is None
        True
        >>> search_value_to_where_condition(not_equals('foo'))
        "!= 'foo'"
        >>> search_value_to_where_condition(greater_than('foo'))
        "> 'foo'"
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
    elif zope_isinstance(search_value, greater_than):
        return "> %s" % sqlvalues(search_value.value)
    elif search_value is not NULL:
        return "= %s" % sqlvalues(search_value)
    else:
        # The argument value indicates we should match
        # only NULL values for the column named by
        # arg_name.
        return "IS NULL"


def get_bug_privacy_filter(user):
    """An SQL filter for search results that adds privacy-awareness."""
    return get_bug_privacy_filter_with_decorator(user)[0]


def _nocache_bug_decorator(obj):
    """A pass through decorator for consistency.

    :seealso: get_bug_privacy_filter_with_decorator
    """
    return obj


def _make_cache_user_can_view_bug(user):
    """Curry a decorator for bugtask queries to cache permissions.

    :seealso: get_bug_privacy_filter_with_decorator
    """
    userid = user.id

    def cache_user_can_view_bug(bugtask):
        get_property_cache(bugtask.bug)._known_viewers = set([userid])
        return bugtask
    return cache_user_can_view_bug


def get_bug_privacy_filter_with_decorator(user):
    """Return a SQL filter to limit returned bug tasks.

    :return: A SQL filter, a decorator to cache visibility in a resultset that
        returns BugTask objects.
    """
    if user is None:
        return "Bug.private = FALSE", _nocache_bug_decorator
    admin_team = getUtility(ILaunchpadCelebrities).admin
    if user.inTeam(admin_team):
        return "", _nocache_bug_decorator
    # A subselect is used here because joining through
    # TeamParticipation is only relevant to the "user-aware"
    # part of the WHERE condition (i.e. the bit below.) The
    # other half of this condition (see code above) does not
    # use TeamParticipation at all.
    pillar_privacy_filters = ''
    if features.getFeatureFlag(
        'disclosure.private_bug_visibility_cte.enabled'):
        if features.getFeatureFlag(
            'disclosure.private_bug_visibility_rules.enabled'):
            pillar_privacy_filters = """
                UNION
                SELECT BugTask.bug
                FROM BugTask, Product
                WHERE Product.owner IN (SELECT team FROM teams) AND
                    BugTask.product = Product.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, ProductSeries
                WHERE ProductSeries.owner IN (SELECT team FROM teams) AND
                    BugTask.productseries = ProductSeries.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, Distribution
                WHERE Distribution.owner IN (SELECT team FROM teams) AND
                    BugTask.distribution = Distribution.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, DistroSeries, Distribution
                WHERE Distribution.owner IN (SELECT team FROM teams) AND
                    DistroSeries.distribution = Distribution.id AND
                    BugTask.distroseries = DistroSeries.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
            """
        query = """
            (Bug.private = FALSE OR EXISTS (
                WITH teams AS (
                    SELECT team from TeamParticipation
                    WHERE person = %(personid)s
                )
                SELECT BugSubscription.bug
                FROM BugSubscription
                WHERE BugSubscription.person IN (SELECT team FROM teams) AND
                    BugSubscription.bug = Bug.id
                UNION
                SELECT BugTask.bug
                FROM BugTask
                WHERE BugTask.assignee IN (SELECT team FROM teams) AND
                    BugTask.bug = Bug.id
                %(extra_filters)s
                    ))
            """ % dict(
                    personid=quote(user.id),
                    extra_filters=pillar_privacy_filters)
    else:
        if features.getFeatureFlag(
            'disclosure.private_bug_visibility_rules.enabled'):
            pillar_privacy_filters = """
                UNION
                SELECT BugTask.bug
                FROM BugTask, TeamParticipation, Product
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = Product.owner AND
                    BugTask.product = Product.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, TeamParticipation, ProductSeries
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = ProductSeries.owner AND
                    BugTask.productseries = ProductSeries.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, TeamParticipation, Distribution
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = Distribution.owner AND
                    BugTask.distribution = Distribution.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
                UNION
                SELECT BugTask.bug
                FROM BugTask, TeamParticipation, DistroSeries, Distribution
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = Distribution.owner AND
                    DistroSeries.distribution = Distribution.id AND
                    BugTask.distroseries = DistroSeries.id AND
                    BugTask.bug = Bug.id AND
                    Bug.security_related IS False
            """ % sqlvalues(personid=user.id)
        query = """
            (Bug.private = FALSE OR EXISTS (
                SELECT BugSubscription.bug
                FROM BugSubscription, TeamParticipation
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = BugSubscription.person AND
                    BugSubscription.bug = Bug.id
                UNION
                SELECT BugTask.bug
                FROM BugTask, TeamParticipation
                WHERE TeamParticipation.person = %(personid)s AND
                    TeamParticipation.team = BugTask.assignee AND
                    BugTask.bug = Bug.id
                %(extra_filters)s
                    ))
            """ % dict(
                    personid=quote(user.id),
                    extra_filters=pillar_privacy_filters)
    return query, _make_cache_user_can_view_bug(user)


def build_tag_set_query(joiner, tags):
    """Return an SQL snippet to find whether a bug matches the given tags.

    The tags are sorted so that testing the generated queries is
    easier and more reliable.

    This SQL is designed to be a sub-query where the parent SQL defines
    Bug.id. It evaluates to TRUE or FALSE, indicating whether the bug
    with Bug.id matches against the tags passed.

    Returns None if no tags are passed.

    :param joiner: The SQL set term used to join the individual tag
        clauses, typically "INTERSECT" or "UNION".
    :param tags: An iterable of valid tag names (not prefixed minus
        signs, not wildcards).
    """
    tags = list(tags)
    if tags == []:
        return None

    joiner = " %s " % joiner
    return "EXISTS (%s)" % joiner.join(
        "SELECT TRUE FROM BugTag WHERE " +
            "BugTag.bug = Bug.id AND BugTag.tag = %s" % quote(tag)
        for tag in sorted(tags))


def _build_tag_set_query_any(tags):
    """Return a query fragment for bugs matching any tag.

    :param tags: An iterable of valid tags without - or + and not wildcards.
    :return: A string SQL query fragment or None if no tags were provided.
    """
    tags = sorted(tags)
    if tags == []:
        return None
    return "EXISTS (%s)" % (
        "SELECT TRUE FROM BugTag"
        " WHERE BugTag.bug = Bug.id"
        " AND BugTag.tag IN %s") % sqlvalues(tags)


def build_tag_search_clause(tags_spec):
    """Return a tag search clause.

    :param tags_spec: An instance of `any` or `all` containing tag
        "specifications". A tag specification is a valid tag name
        optionally prefixed by a minus sign (denoting "not"), or an
        asterisk (denoting "any tag"), again optionally prefixed by a
        minus sign (and thus denoting "not any tag").
    """
    tags = set(tags_spec.query_values)
    wildcards = [tag for tag in tags if tag in ('*', '-*')]
    tags.difference_update(wildcards)
    include = [tag for tag in tags if not tag.startswith('-')]
    exclude = [tag[1:] for tag in tags if tag.startswith('-')]

    # Should we search for all specified tags or any of them?
    find_all = zope_isinstance(tags_spec, all)

    if find_all:
        # How to combine an include clause and an exclude clause when
        # both are generated.
        combine_with = 'AND'
        # The set of bugs that have *all* of the tags requested for
        # *inclusion*.
        include_clause = build_tag_set_query("INTERSECT", include)
        # The set of bugs that have *any* of the tags requested for
        # *exclusion*.
        exclude_clause = _build_tag_set_query_any(exclude)
    else:
        # How to combine an include clause and an exclude clause when
        # both are generated.
        combine_with = 'OR'
        # The set of bugs that have *any* of the tags requested for
        # inclusion.
        include_clause = _build_tag_set_query_any(include)
        # The set of bugs that have *all* of the tags requested for
        # exclusion.
        exclude_clause = build_tag_set_query("INTERSECT", exclude)

    # Search for the *presence* of any tag.
    if '*' in wildcards:
        # Only clobber the clause if not searching for all tags.
        if include_clause == None or not find_all:
            include_clause = (
                "EXISTS (SELECT TRUE FROM BugTag WHERE BugTag.bug = Bug.id)")

    # Search for the *absence* of any tag.
    if '-*' in wildcards:
        # Only clobber the clause if searching for all tags.
        if exclude_clause == None or find_all:
            exclude_clause = (
                "EXISTS (SELECT TRUE FROM BugTag WHERE BugTag.bug = Bug.id)")

    # Combine the include and exclude sets.
    if include_clause != None and exclude_clause != None:
        return "(%s %s NOT %s)" % (
            include_clause, combine_with, exclude_clause)
    elif include_clause != None:
        return "%s" % include_clause
    elif exclude_clause != None:
        return "NOT %s" % exclude_clause
    else:
        # This means that there were no tags (wildcard or specific) to
        # search for (which is allowed, even if it's a bit weird).
        return None


class BugTaskSet:
    """See `IBugTaskSet`."""
    implements(IBugTaskSet)

    _ORDERBY_COLUMN = None

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

    @property
    def open_bugtask_search(self):
        """See `IBugTaskSet`."""
        return BugTaskSearchParams(
            user=getUtility(ILaunchBag).user,
            status=any(*DB_UNRESOLVED_BUGTASK_STATUSES),
            omit_dupes=True)

    def get(self, task_id):
        """See `IBugTaskSet`."""
        # XXX: JSK: 2007-12-19: This method should probably return
        # None when task_id is not present. See:
        # https://bugs.launchpad.net/launchpad/+bug/123592
        try:
            bugtask = BugTask.get(task_id)
        except SQLObjectNotFound:
            raise NotFoundError("BugTask with ID %s does not exist." %
                                str(task_id))
        return bugtask

    def getBugTasks(self, bug_ids):
        """See `IBugTaskSet`."""
        from lp.bugs.model.bug import Bug
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = [BugTask, Join(Bug, BugTask.bug == Bug.id)]
        columns = (Bug, BugTask)
        result = store.using(*origin).find(columns, Bug.id.is_in(bug_ids))
        bugs_and_tasks = {}
        for bug, task in result:
            if bug not in bugs_and_tasks:
                bugs_and_tasks[bug] = []
            bugs_and_tasks[bug].append(task)
        return bugs_and_tasks

    def getBugTaskBadgeProperties(self, bugtasks):
        """See `IBugTaskSet`."""
        # Import locally to avoid circular imports.
        from lp.blueprints.model.specificationbug import SpecificationBug
        from lp.bugs.model.bug import Bug
        from lp.bugs.model.bugbranch import BugBranch

        bug_ids = set(bugtask.bugID for bugtask in bugtasks)
        bug_ids_with_specifications = set(IStore(SpecificationBug).find(
            SpecificationBug.bugID,
            SpecificationBug.bugID.is_in(bug_ids)))
        bug_ids_with_branches = set(IStore(BugBranch).find(
                BugBranch.bugID, BugBranch.bugID.is_in(bug_ids)))
        # Badging looks up milestones too : eager load into the storm cache.
        milestoneset = getUtility(IMilestoneSet)
        # And trigger a load:
        milestone_ids = set(map(attrgetter('milestoneID'), bugtasks))
        milestone_ids.discard(None)
        if milestone_ids:
            list(milestoneset.getByIds(milestone_ids))

        # Check if the bugs are cached. If not, cache all uncached bugs
        # at once to avoid one query per bugtask. We could rely on the
        # Storm cache, but this is explicit.
        bugs = dict(
            (bug.id, bug)
            for bug in IStore(Bug).find(Bug, Bug.id.is_in(bug_ids)).cached())
        uncached_ids = bug_ids.difference(bug_id for bug_id in bugs)
        if len(uncached_ids) > 0:
            bugs.update(dict(IStore(Bug).find((Bug.id, Bug),
                                              Bug.id.is_in(uncached_ids))))

        badge_properties = {}
        for bugtask in bugtasks:
            bug = bugs[bugtask.bugID]
            badge_properties[bugtask] = {
                'has_specification':
                    bug.id in bug_ids_with_specifications,
                'has_branch':
                    bug.id in bug_ids_with_branches,
                'has_patch':
                    bug.latest_patch_uploaded is not None,
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
        if not summary:
            return EmptyResultSet()
        # Avoid circular imports.
        from lp.bugs.model.bug import Bug
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

        search_params.fast_searchtext = nl_phrase_search(
            summary, Bug, ' AND '.join(constraint_clauses), ['BugTask'])
        return self.search(search_params, _noprejoins=True)

    @classmethod
    def _buildStatusClause(cls, status):
        """Return the SQL query fragment for search by status.

        Called from `buildQuery` or recursively."""
        if zope_isinstance(status, any):
            values = list(status.query_values)
            # Since INCOMPLETE isn't stored as a single value we need to
            # expand it before generating the SQL.
            if BugTaskStatus.INCOMPLETE in values:
                values.remove(BugTaskStatus.INCOMPLETE)
                values.extend(DB_INCOMPLETE_BUGTASK_STATUSES)
            return '(BugTask.status {0})'.format(
                search_value_to_where_condition(any(*values)))
        elif zope_isinstance(status, not_equals):
            return '(NOT {0})'.format(cls._buildStatusClause(status.value))
        elif zope_isinstance(status, BaseItem):
            # INCOMPLETE is not stored in the DB, instead one of
            # DB_INCOMPLETE_BUGTASK_STATUSES is stored, so any request to
            # search for INCOMPLETE should instead search for those values.
            if status == BugTaskStatus.INCOMPLETE:
                return '(BugTask.status {0})'.format(
                    search_value_to_where_condition(
                        any(*DB_INCOMPLETE_BUGTASK_STATUSES)))
            else:
                return '(BugTask.status = %s)' % sqlvalues(status)
        else:
            raise ValueError('Unrecognized status value: %r' % (status,))

    def _buildExcludeConjoinedClause(self, milestone):
        """Exclude bugtasks with a conjoined master.

        This search option only makes sense when searching for bugtasks
        for a milestone.  Only bugtasks for a project or a distribution
        can have a conjoined master bugtask, which is a bugtask on the
        project's development focus series or the distribution's
        currentseries. The project bugtask or the distribution bugtask
        will always have the same milestone set as its conjoined master
        bugtask, if it exists on the bug. Therefore, this prevents a lot
        of bugs having two bugtasks listed in the results. However, it
        is ok if a bug has multiple bugtasks in the results as long as
        those other bugtasks are on other series.
        """
        # XXX: EdwinGrubbs 2010-12-15 bug=682989
        # (ConjoinedMaster.bug == X) produces the wrong sql, but
        # (ConjoinedMaster.bugID == X) works right. This bug applies to
        # all foreign keys on the ClassAlias.

        # Perform a LEFT JOIN to the conjoined master bugtask.  If the
        # conjoined master is not null, it gets filtered out.
        ConjoinedMaster = ClassAlias(BugTask, 'ConjoinedMaster')
        extra_clauses = ["ConjoinedMaster.id IS NULL"]
        if milestone.distribution is not None:
            current_series = milestone.distribution.currentseries
            join = LeftJoin(
                ConjoinedMaster,
                And(ConjoinedMaster.bugID == BugTask.bugID,
                    BugTask.distributionID == milestone.distribution.id,
                    ConjoinedMaster.distroseriesID == current_series.id,
                    Not(ConjoinedMaster._status.is_in(
                            BugTask._NON_CONJOINED_STATUSES))))
            join_tables = [(ConjoinedMaster, join)]
        else:
            # Prevent import loop.
            from lp.registry.model.milestone import Milestone
            from lp.registry.model.product import Product
            if IProjectGroupMilestone.providedBy(milestone):
                # Since an IProjectGroupMilestone could have bugs with
                # bugtasks on two different projects, the project
                # bugtask is only excluded by a development focus series
                # bugtask on the same project.
                joins = [
                    Join(Milestone, BugTask.milestone == Milestone.id),
                    LeftJoin(Product, BugTask.product == Product.id),
                    LeftJoin(
                        ConjoinedMaster,
                        And(ConjoinedMaster.bugID == BugTask.bugID,
                            ConjoinedMaster.productseriesID
                                == Product.development_focusID,
                            Not(ConjoinedMaster._status.is_in(
                                    BugTask._NON_CONJOINED_STATUSES)))),
                    ]
                # join.right is the table name.
                join_tables = [(join.right, join) for join in joins]
            elif milestone.product is not None:
                dev_focus_id = (
                    milestone.product.development_focusID)
                join = LeftJoin(
                    ConjoinedMaster,
                    And(ConjoinedMaster.bugID == BugTask.bugID,
                        BugTask.productID == milestone.product.id,
                        ConjoinedMaster.productseriesID == dev_focus_id,
                        Not(ConjoinedMaster._status.is_in(
                                BugTask._NON_CONJOINED_STATUSES))))
                join_tables = [(ConjoinedMaster, join)]
            else:
                raise AssertionError(
                    "A milestone must always have either a project, "
                    "project group, or distribution")
        return (join_tables, extra_clauses)

    def _require_params(self, params):
        assert zope_isinstance(params, BugTaskSearchParams)
        if not isinstance(params, BugTaskSearchParams):
            # Browser code let this get wrapped, unwrap it here as its just a
            # dumb data store that has no security implications.
            params = removeSecurityProxy(params)
        return params

    def buildQuery(self, params):
        """Build and return an SQL query with the given parameters.

        Also return the clauseTables and orderBy for the generated query.

        :return: A query, the tables to query, ordering expression and a
            decorator to call on each returned row.
        """
        params = self._require_params(params)
        from lp.bugs.model.bug import (
            Bug,
            BugAffectsPerson,
            )
        extra_clauses = ['Bug.id = BugTask.bug']
        clauseTables = [BugTask, Bug]
        join_tables = []
        decorators = []
        has_duplicate_results = False
        with_clauses = []

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
            'date_closed': params.date_closed,
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
            if IProjectGroupMilestone.providedBy(params.milestone):
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

            if params.exclude_conjoined_tasks:
                tables, clauses = self._buildExcludeConjoinedClause(
                    params.milestone)
                join_tables += tables
                extra_clauses += clauses
        elif params.exclude_conjoined_tasks:
            raise ValueError(
                "BugTaskSearchParam.exclude_conjoined cannot be True if "
                "BugTaskSearchParam.milestone is not set")

        if params.project:
            # Prevent circular import problems.
            from lp.registry.model.product import Product
            clauseTables.append(Product)
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
            if params.attachmenttype == BugAttachmentType.PATCH:
                extra_clauses.append("Bug.latest_patch_uploaded IS NOT NULL")
            else:
                attachment_clause = (
                    "Bug.id IN (SELECT bug from BugAttachment WHERE %s)")
                if isinstance(params.attachmenttype, any):
                    where_cond = "BugAttachment.type IN (%s)" % ", ".join(
                        sqlvalues(*params.attachmenttype.query_values))
                else:
                    where_cond = "BugAttachment.type = %s" % sqlvalues(
                        params.attachmenttype)
                extra_clauses.append(attachment_clause % where_cond)

        if params.searchtext:
            extra_clauses.append(self._buildSearchTextClause(params))

        if params.fast_searchtext:
            extra_clauses.append(self._buildFastSearchTextClause(params))

        if params.subscriber is not None:
            clauseTables.append(BugSubscription)
            extra_clauses.append("""Bug.id = BugSubscription.bug AND
                    BugSubscription.person = %(personid)s""" %
                    sqlvalues(personid=params.subscriber.id))

        if params.structural_subscriber is not None:
            # See bug 787294 for the story that led to the query elements
            # below.  Please change with care.
            with_clauses.append(
                '''ss as (SELECT * from StructuralSubscription
                WHERE StructuralSubscription.subscriber = %s)'''
                % sqlvalues(params.structural_subscriber))
            # Prevent circular import problems.
            from lp.registry.model.product import Product
            join_tables.append(
                (Product, LeftJoin(Product, And(
                                BugTask.productID == Product.id,
                                Product.active))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss1'),
                    BugTask.product == SQL('ss1.product'))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss2'),
                    BugTask.productseries == SQL('ss2.productseries'))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss3'),
                    Product.project == SQL('ss3.project'))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss4'),
                    And(BugTask.distribution == SQL('ss4.distribution'),
                        Or(BugTask.sourcepackagename ==
                            SQL('ss4.sourcepackagename'),
                           SQL('ss4.sourcepackagename IS NULL'))))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss5'),
                    BugTask.distroseries == SQL('ss5.distroseries'))))
            join_tables.append(
                (None,
                 LeftJoin(
                    SQL('ss ss6'),
                    BugTask.milestone == SQL('ss6.milestone'))))
            extra_clauses.append(
                "NULL_COUNT("
                "ARRAY[ss1.id, ss2.id, ss3.id, ss4.id, ss5.id, ss6.id]"
                ") < 6")
            has_duplicate_results = True

        # Remove bugtasks from deactivated products, if necessary.
        # We don't have to do this if
        # 1) We're searching on bugtasks for a specific product
        # 2) We're searching on bugtasks for a specific productseries
        # 3) We're searching on bugtasks for a distribution
        # 4) We're searching for bugtasks for a distroseries
        # because in those instances we don't have arbitrary products which
        # may be deactivated showing up in our search.
        if (params.product is None and
            params.distribution is None and
            params.productseries is None and
            params.distroseries is None):
            # Prevent circular import problems.
            from lp.registry.model.product import Product
            extra_clauses.append(
                "(Bugtask.product IS NULL OR Product.active = TRUE)")
            join_tables.append(
                (Product, LeftJoin(Product, And(
                                BugTask.productID == Product.id,
                                Product.active))))

        if params.component:
            distroseries = None
            if params.distribution:
                distroseries = params.distribution.currentseries
            elif params.distroseries:
                distroseries = params.distroseries
            if distroseries is None:
                raise ValueError(
                    "Search by component requires a context with a "
                    "distribution or distroseries.")

            if zope_isinstance(params.component, any):
                component_ids = sqlvalues(*params.component.query_values)
            else:
                component_ids = sqlvalues(params.component)

            distro_archive_ids = [
                archive.id
                for archive in distroseries.distribution.all_distro_archives]
            with_clauses.append("""spns as (
                SELECT spr.sourcepackagename
                FROM SourcePackagePublishingHistory
                JOIN SourcePackageRelease AS spr ON spr.id =
                    SourcePackagePublishingHistory.sourcepackagerelease AND
                SourcePackagePublishingHistory.distroseries = %s AND
                SourcePackagePublishingHistory.archive IN %s AND
                SourcePackagePublishingHistory.component IN %s AND
                SourcePackagePublishingHistory.status = %s
                )""" % sqlvalues(distroseries,
                                distro_archive_ids,
                                component_ids,
                                PackagePublishingStatus.PUBLISHED))
            extra_clauses.append(
                """BugTask.sourcepackagename in (
                    select sourcepackagename from spns)""")

        upstream_clause = self.buildUpstreamClause(params)
        if upstream_clause:
            extra_clauses.append(upstream_clause)

        if params.tag:
            tag_clause = build_tag_search_clause(params.tag)
            if tag_clause is not None:
                extra_clauses.append(tag_clause)

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
                WHERE
                  BugTask.distribution = StructuralSubscription.distribution
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
            Bug.id IN (SELECT DISTINCT bug FROM Bugmessage WHERE
            BugMessage.index > 0 AND BugMessage.owner = %(bug_commenter)s)
            """ % sqlvalues(bug_commenter=params.bug_commenter)
            extra_clauses.append(bug_commenter_clause)

        if params.affects_me:
            params.affected_user = params.user
        if params.affected_user:
            join_tables.append(
                (BugAffectsPerson, Join(
                    BugAffectsPerson, And(
                        BugTask.bugID == BugAffectsPerson.bugID,
                        BugAffectsPerson.affected,
                        BugAffectsPerson.person == params.affected_user))))

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
            clauseTables.append(BugNomination)

        clause, decorator = get_bug_privacy_filter_with_decorator(params.user)
        if clause:
            extra_clauses.append(clause)
            decorators.append(decorator)

        hw_clause = self._buildHardwareRelatedClause(params)
        if hw_clause is not None:
            extra_clauses.append(hw_clause)

        if zope_isinstance(params.linked_branches, BaseItem):
            if params.linked_branches == BugBranchSearch.BUGS_WITH_BRANCHES:
                extra_clauses.append(
                    """EXISTS (
                        SELECT id FROM BugBranch WHERE BugBranch.bug=Bug.id)
                    """)
            elif (params.linked_branches ==
                  BugBranchSearch.BUGS_WITHOUT_BRANCHES):
                extra_clauses.append(
                    """NOT EXISTS (
                        SELECT id FROM BugBranch WHERE BugBranch.bug=Bug.id)
                    """)
        elif zope_isinstance(params.linked_branches, (any, all, int)):
            # A specific search term has been supplied.
            extra_clauses.append(
                """EXISTS (
                    SELECT TRUE FROM BugBranch WHERE BugBranch.bug=Bug.id AND
                    BugBranch.branch %s)
                """ % search_value_to_where_condition(params.linked_branches))

        linked_blueprints_clause = self._buildBlueprintRelatedClause(params)
        if linked_blueprints_clause is not None:
            extra_clauses.append(linked_blueprints_clause)

        if params.modified_since:
            extra_clauses.append(
                "Bug.date_last_updated > %s" % (
                    sqlvalues(params.modified_since,)))

        if params.created_since:
            extra_clauses.append(
                "BugTask.datecreated > %s" % (
                    sqlvalues(params.created_since,)))

        orderby_arg, extra_joins = self._processOrderBy(params)
        join_tables.extend(extra_joins)

        query = " AND ".join(extra_clauses)

        if not decorators:
            decorator = lambda x: x
        else:

            def decorator(obj):
                for decor in decorators:
                    obj = decor(obj)
                return obj
        if with_clauses:
            with_clause = SQL(', '.join(with_clauses))
        else:
            with_clause = None
        return (
            query, clauseTables, orderby_arg, decorator, join_tables,
            has_duplicate_results, with_clause)

    def buildUpstreamClause(self, params):
        """Return an clause for returning upstream data if the data exists.

        This method will handles BugTasks that do not have upstream BugTasks
        as well as thoses that do.
        """
        params = self._require_params(params)
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
            # Find all bugs that has no product bugtask. We limit the
            # SELECT by matching against BugTask.bug to make the query
            # faster.
            has_no_upstream_bugtask_clause = """
                NOT EXISTS (SELECT TRUE
                            FROM BugTask AS OtherBugTask
                            WHERE OtherBugTask.bug = BugTask.bug
                                AND OtherBugTask.product IS NOT NULL)
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
                BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE,
                BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
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
                ]

        comment_clause = """BugTask.id IN (
            SELECT BugTask.id
            FROM BugTask, BugMessage,Message, MessageChunk
            WHERE BugMessage.bug = BugTask.bug
                AND BugMessage.message = Message.id
                AND Message.id = MessageChunk.message
                AND MessageChunk.fti @@ ftq(%s))""" % searchtext_quoted
        text_search_clauses = [
            "Bug.fti @@ ftq(%s)" % searchtext_quoted,
            ]
        no_targetnamesearch = bool(features.getFeatureFlag(
            'malone.disable_targetnamesearch'))
        if not no_targetnamesearch:
            text_search_clauses.append(
                "BugTask.targetnamecache ILIKE '%%' || %s || '%%'" % (
                searchtext_like_quoted))
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

    def _buildHardwareRelatedClause(self, params):
        """Hardware related SQL expressions and tables for bugtask searches.

        :return: (tables, clauses) where clauses is a list of SQL expressions
            which limit a bugtask search to bugs related to a device or
            driver specified in search_params. If search_params contains no
            hardware related data, empty lists are returned.
        :param params: A `BugTaskSearchParams` instance.

        Device related WHERE clauses are returned if
        params.hardware_bus, params.hardware_vendor_id,
        params.hardware_product_id are all not None.
        """
        # Avoid cyclic imports.
        from lp.hardwaredb.model.hwdb import (
            HWSubmission, HWSubmissionBug, HWSubmissionDevice,
            _userCanAccessSubmissionStormClause,
            make_submission_device_statistics_clause)
        from lp.bugs.model.bug import Bug, BugAffectsPerson

        bus = params.hardware_bus
        vendor_id = params.hardware_vendor_id
        product_id = params.hardware_product_id
        driver_name = params.hardware_driver_name
        package_name = params.hardware_driver_package_name

        if (bus is not None and vendor_id is not None and
            product_id is not None):
            tables, clauses = make_submission_device_statistics_clause(
                bus, vendor_id, product_id, driver_name, package_name, False)
        elif driver_name is not None or package_name is not None:
            tables, clauses = make_submission_device_statistics_clause(
                None, None, None, driver_name, package_name, False)
        else:
            return None

        tables.append(HWSubmission)
        tables.append(Bug)
        clauses.append(HWSubmissionDevice.submission == HWSubmission.id)
        bug_link_clauses = []
        if params.hardware_owner_is_bug_reporter:
            bug_link_clauses.append(
                HWSubmission.ownerID == Bug.ownerID)
        if params.hardware_owner_is_affected_by_bug:
            bug_link_clauses.append(
                And(BugAffectsPerson.personID == HWSubmission.ownerID,
                    BugAffectsPerson.bug == Bug.id,
                    BugAffectsPerson.affected))
            tables.append(BugAffectsPerson)
        if params.hardware_owner_is_subscribed_to_bug:
            bug_link_clauses.append(
                And(BugSubscription.person_id == HWSubmission.ownerID,
                    BugSubscription.bug_id == Bug.id))
            tables.append(BugSubscription)
        if params.hardware_is_linked_to_bug:
            bug_link_clauses.append(
                And(HWSubmissionBug.bugID == Bug.id,
                    HWSubmissionBug.submissionID == HWSubmission.id))
            tables.append(HWSubmissionBug)

        if len(bug_link_clauses) == 0:
            return None

        clauses.append(Or(*bug_link_clauses))
        clauses.append(_userCanAccessSubmissionStormClause(params.user))

        tables = [convert_storm_clause_to_string(table) for table in tables]
        clauses = ['(%s)' % convert_storm_clause_to_string(clause)
                   for clause in clauses]
        clause = 'Bug.id IN (SELECT DISTINCT Bug.id from %s WHERE %s)' % (
            ', '.join(tables), ' AND '.join(clauses))
        return clause

    def _buildBlueprintRelatedClause(self, params):
        """Find bugs related to Blueprints, or not."""
        linked_blueprints = params.linked_blueprints
        if linked_blueprints is None:
            return None
        elif zope_isinstance(linked_blueprints, BaseItem):
            if linked_blueprints == BugBlueprintSearch.BUGS_WITH_BLUEPRINTS:
                return "EXISTS (%s)" % (
                    "SELECT 1 FROM SpecificationBug"
                    " WHERE SpecificationBug.bug = Bug.id")
            elif (linked_blueprints ==
                  BugBlueprintSearch.BUGS_WITHOUT_BLUEPRINTS):
                return "NOT EXISTS (%s)" % (
                    "SELECT 1 FROM SpecificationBug"
                    " WHERE SpecificationBug.bug = Bug.id")
        else:
            # A specific search term has been supplied.
            return """EXISTS (
                    SELECT TRUE FROM SpecificationBug
                    WHERE SpecificationBug.bug=Bug.id AND
                    SpecificationBug.specification %s)
                """ % search_value_to_where_condition(linked_blueprints)

    def buildOrigin(self, join_tables, prejoin_tables, clauseTables):
        """Build the parameter list for Store.using().

        :param join_tables: A sequence of tables that should be joined
            as returned by buildQuery(). Each element has the form
            (table, join), where table is the table to join and join
            is a Storm Join or LeftJoin instance.
        :param prejoin_tables: A sequence of tables that should additionally
            be joined. Each element has the form (table, join),
            where table is the table to join and join is a Storm Join
            or LeftJoin instance.
        :param clauseTables: A sequence of tables that should appear in
            the FROM clause of a query. The join condition is defined in
            the WHERE clause.

        Tables may appear simultaneously in join_tables, prejoin_tables
        and in clauseTables. This method ensures that each table
        appears exactly once in the returned sequence.
        """
        origin = [BugTask]
        already_joined = set(origin)
        for table, join in join_tables:
            if table is None or table not in already_joined:
                origin.append(join)
                if table is not None:
                    already_joined.add(table)
        for table, join in prejoin_tables:
            if table not in already_joined:
                origin.append(join)
                already_joined.add(table)
        for table in clauseTables:
            if table not in already_joined:
                origin.append(table)
        return origin

    def _search(self, resultrow, prejoins, pre_iter_hook, params, *args):
        """Return a Storm result set for the given search parameters.

        :param resultrow: The type of data returned by the query.
        :param prejoins: A sequence of Storm SQL row instances which are
            pre-joined.
        :param pre_iter_hook: An optional pre-iteration hook used for eager
            loading bug targets for list views.
        :param params: A BugTaskSearchParams instance.
        :param args: optional additional BugTaskSearchParams instances,
        """
        orig_store = store = IStore(BugTask)
        [query, clauseTables, orderby, bugtask_decorator, join_tables,
        has_duplicate_results, with_clause] = self.buildQuery(params)
        if with_clause:
            store = store.with_(with_clause)
        if len(args) == 0:
            if has_duplicate_results:
                origin = self.buildOrigin(join_tables, [], clauseTables)
                outer_origin = self.buildOrigin([], prejoins, [])
                subquery = Select(BugTask.id, where=SQL(query), tables=origin)
                resultset = store.using(*outer_origin).find(
                    resultrow, In(BugTask.id, subquery))
            else:
                origin = self.buildOrigin(join_tables, prejoins, clauseTables)
                resultset = store.using(*origin).find(resultrow, query)
            if prejoins:
                decorator = lambda row: bugtask_decorator(row[0])
            else:
                decorator = bugtask_decorator

            resultset.order_by(orderby)
            return DecoratedResultSet(resultset, result_decorator=decorator,
                pre_iter_hook=pre_iter_hook)

        inner_resultrow = (BugTask,)
        origin = self.buildOrigin(join_tables, [], clauseTables)
        resultset = store.using(*origin).find(inner_resultrow, query)

        decorators = [bugtask_decorator]
        for arg in args:
            [query, clauseTables, ignore, decorator, join_tables,
             has_duplicate_results, with_clause] = self.buildQuery(arg)
            origin = self.buildOrigin(join_tables, [], clauseTables)
            localstore = store
            if with_clause:
                localstore = orig_store.with_(with_clause)
            next_result = localstore.using(*origin).find(
                inner_resultrow, query)
            resultset = resultset.union(next_result)
            # NB: assumes the decorators are all compatible.
            # This may need revisiting if e.g. searches on behalf of different
            # users are combined.
            decorators.append(decorator)

        def prejoin_decorator(row):
            bugtask = row[0]
            for decorator in decorators:
                bugtask = decorator(bugtask)
            return bugtask

        def simple_decorator(bugtask):
            for decorator in decorators:
                bugtask = decorator(bugtask)
            return bugtask

        origin = [Alias(resultset._get_select(), "BugTask")]
        if prejoins:
            origin += [join for table, join in prejoins]
            decorator = prejoin_decorator
        else:
            decorator = simple_decorator

        result = store.using(*origin).find(resultrow)
        result.order_by(orderby)
        return DecoratedResultSet(result, result_decorator=decorator,
            pre_iter_hook=pre_iter_hook)

    def search(self, params, *args, **kwargs):
        """See `IBugTaskSet`.

        :param _noprejoins: Private internal parameter to BugTaskSet which
            disables all use of prejoins : consolidated from code paths that
            claim they were inefficient and unwanted.
        :param prejoins: A sequence of tuples (table, table_join) which
            which should be pre-joined in addition to the default prejoins.
            This parameter has no effect if _noprejoins is True.
        """
        # Prevent circular import problems.
        from lp.registry.model.product import Product
        from lp.bugs.model.bug import Bug
        _noprejoins = kwargs.get('_noprejoins', False)
        if _noprejoins:
            prejoins = []
            resultrow = BugTask
            eager_load = None
        else:
            requested_joins = kwargs.get('prejoins', [])
            # NB: We could save later work by predicting what sort of
            # targets we might be interested in here, but as at any
            # point we're dealing with relatively few results, this is
            # likely to be a small win.
            prejoins = [
                (Bug, Join(Bug, BugTask.bug == Bug.id))] + requested_joins

            def eager_load(results):
                product_ids = set([row[0].productID for row in results])
                product_ids.discard(None)
                pkgname_ids = set(
                    [row[0].sourcepackagenameID for row in results])
                pkgname_ids.discard(None)
                store = IStore(BugTask)
                if product_ids:
                    list(store.find(Product, Product.id.is_in(product_ids)))
                if pkgname_ids:
                    list(store.find(SourcePackageName,
                        SourcePackageName.id.is_in(pkgname_ids)))
            resultrow = (BugTask, Bug)
            additional_result_objects = [
                table for table, join in requested_joins
                if table not in resultrow]
            resultrow = resultrow + tuple(additional_result_objects)
        return self._search(resultrow, prejoins, eager_load, params, *args)

    def searchBugIds(self, params):
        """See `IBugTaskSet`."""
        return self._search(BugTask.bugID, [], None, params).result_set

    def countBugs(self, user, contexts, group_on):
        """See `IBugTaskSet`."""
        # Circular fail.
        from lp.bugs.model.bugsummary import BugSummary
        conditions = []
        # Open bug statuses
        conditions.append(
            BugSummary.status.is_in(DB_UNRESOLVED_BUGTASK_STATUSES))
        # BugSummary does not include duplicates so no need to exclude.
        context_conditions = []
        for context in contexts:
            condition = removeSecurityProxy(
                context.getBugSummaryContextWhereClause())
            if condition is not False:
                context_conditions.append(condition)
        if not context_conditions:
            return {}
        conditions.append(Or(*context_conditions))
        # bugsummary by design requires either grouping by tag or excluding
        # non-null tags.
        # This is an awkward way of saying
        # if BugSummary.tag not in group_on:
        # - see bug 799602
        group_on_tag = False
        for column in group_on:
            if column is BugSummary.tag:
                group_on_tag = True
        if not group_on_tag:
            conditions.append(BugSummary.tag == None)
        else:
            conditions.append(BugSummary.tag != None)
        store = IStore(BugSummary)
        admin_team = getUtility(ILaunchpadCelebrities).admin
        if user is not None and not user.inTeam(admin_team):
            # admins get to see every bug, everyone else only sees bugs
            # viewable by them-or-their-teams.
            store = store.with_(SQL(
                "teams AS ("
                "SELECT team from TeamParticipation WHERE person=?)",
                (user.id,)))
        # Note that because admins can see every bug regardless of
        # subscription they will see rather inflated counts. Admins get to
        # deal.
        if user is None:
            conditions.append(BugSummary.viewed_by_id == None)
        elif not user.inTeam(admin_team):
            conditions.append(
                Or(
                    BugSummary.viewed_by_id == None,
                    BugSummary.viewed_by_id.is_in(
                        SQL("SELECT team FROM teams"))
                    ))
        sum_count = Sum(BugSummary.count)
        resultset = store.find(group_on + (sum_count,), *conditions)
        resultset.group_by(*group_on)
        resultset.having(sum_count != 0)
        # Ensure we have no order clauses.
        resultset.order_by()
        result = {}
        for row in resultset:
            result[row[:-1]] = row[-1]
        return result

    def getPrecachedNonConjoinedBugTasks(self, user, milestone):
        """See `IBugTaskSet`."""
        params = BugTaskSearchParams(
            user, milestone=milestone,
            orderby=['status', '-importance', 'id'],
            omit_dupes=True, exclude_conjoined_tasks=True)
        return self.search(params)

    def createTask(self, bug, owner, target,
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

        # Make sure there's no task for this bug already filed
        # against the target.
        validate_new_target(bug, target)

        target_key = bug_target_to_key(target)
        if not bug.private and bug.security_related:
            product = target_key['product']
            distribution = target_key['distribution']
            if product and product.security_contact:
                bug.subscribe(product.security_contact, owner)
            elif distribution and distribution.security_contact:
                bug.subscribe(distribution.security_contact, owner)

        non_target_create_params = dict(
            bug=bug,
            _status=status,
            importance=importance,
            assignee=assignee,
            owner=owner,
            milestone=milestone)
        create_params = non_target_create_params.copy()
        create_params.update(target_key)
        bugtask = BugTask(**create_params)
        if target_key['distribution']:
            # Create tasks for accepted nominations if this is a source
            # package addition.
            accepted_nominations = [
                nomination for nomination in
                bug.getNominations(target_key['distribution'])
                if nomination.isApproved()]
            for nomination in accepted_nominations:
                accepted_series_task = BugTask(
                    distroseries=nomination.distroseries,
                    sourcepackagename=target_key['sourcepackagename'],
                    **non_target_create_params)
                accepted_series_task.updateTargetNameCache()

        if bugtask.conjoined_slave:
            bugtask._syncFromConjoinedSlave()

        bugtask.updateTargetNameCache()
        del get_property_cache(bug).bugtasks
        # Because of block_implicit_flushes, it is possible for a new bugtask
        # to be queued in appropriately, which leads to Bug.bugtasks not
        # finding the bugtask.
        Store.of(bugtask).flush()
        return bugtask

    def getStatusCountsForProductSeries(self, user, product_series):
        """See `IBugTaskSet`."""
        if user is None:
            bug_privacy_filter = 'AND Bug.private = FALSE'
        else:
            # Since the count won't reveal sensitive information, and
            # since the get_bug_privacy_filter() check for non-admins is
            # costly, don't filter those bugs at all.
            bug_privacy_filter = ''
        # The union is actually much faster than a LEFT JOIN with the
        # Milestone table, since postgres optimizes it to perform index
        # scans instead of sequential scans on the BugTask table.
        query = """
            SELECT
                status, COUNT(*)
            FROM (
                SELECT BugTask.status
                FROM BugTask
                    JOIN Bug ON BugTask.bug = Bug.id
                WHERE
                    BugTask.productseries = %(series)s
                    %(privacy)s
                UNION ALL
                SELECT BugTask.status
                FROM BugTask
                    JOIN Bug ON BugTask.bug = Bug.id
                    JOIN Milestone ON BugTask.milestone = Milestone.id
                WHERE
                    BugTask.productseries IS NULL
                    AND Milestone.productseries = %(series)s
                    %(privacy)s
                ) AS subquery
            GROUP BY status
            """
        query %= dict(
            series=quote(product_series),
            privacy=bug_privacy_filter)
        cur = cursor()
        cur.execute(query)
        return dict(
            (get_bugtask_status(status_id), count)
            for (status_id, count) in cur.fetchall())

    def findExpirableBugTasks(self, min_days_old, user,
                              bug=None, target=None, limit=None):
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

        Only bugtasks the specified user has permission to view are
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
        unconfirmed_bug_condition = self._getUnconfirmedBugCondition()
        (target_join, target_clause) = self._getTargetJoinAndClause(target)
        query = """
            BugTask.bug = Bug.id
            AND BugTask.id IN (
                SELECT BugTask.id
                FROM BugTask
                    JOIN Bug ON BugTask.bug = Bug.id
                    LEFT JOIN BugWatch on Bug.id = BugWatch.bug
                """ + target_join + """
                WHERE
                """ + target_clause + """
                """ + bug_clause + """
                """ + bug_privacy_filter + """
                    AND BugTask.status in (%s, %s, %s)
                    AND BugTask.assignee IS NULL
                    AND BugTask.milestone IS NULL
                    AND Bug.duplicateof IS NULL
                    AND Bug.date_last_updated < CURRENT_TIMESTAMP
                        AT TIME ZONE 'UTC' - interval '%s days'
                    AND BugWatch.id IS NULL
            )""" % sqlvalues(BugTaskStatus.INCOMPLETE,
                BugTaskStatusSearch.INCOMPLETE_WITH_RESPONSE,
                BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE, min_days_old)
        expirable_bugtasks = BugTask.select(
            query + unconfirmed_bug_condition,
            clauseTables=['Bug'],
            orderBy='Bug.date_last_updated')
        if limit is not None:
            expirable_bugtasks = expirable_bugtasks.limit(limit)
        return expirable_bugtasks

    def _getUnconfirmedBugCondition(self):
        """Return the SQL to filter out BugTasks that has been confirmed

        A bugtasks cannot expire if the bug is, has been, or
        will be, confirmed to be legitimate. Once the bug is considered
        valid for one target, it is valid for all targets.
        """
        statuses_not_preventing_expiration = [
            BugTaskStatus.INVALID, BugTaskStatus.INCOMPLETE,
            BugTaskStatusSearch.INCOMPLETE_WITHOUT_RESPONSE,
            BugTaskStatus.WONTFIX]

        unexpirable_status_list = [
            status for status in BugTaskStatus.items
            if status not in statuses_not_preventing_expiration]

        return """
             AND NOT EXISTS (
                SELECT TRUE
                FROM BugTask AS RelatedBugTask
                WHERE RelatedBugTask.bug = BugTask.bug
                    AND RelatedBugTask.status IN %s)
            """ % sqlvalues(unexpirable_status_list)

    TARGET_SELECT = {
        IDistribution: """
            SELECT Distribution.id, NULL, NULL, NULL,
                Distribution.id, NULL
            FROM Distribution
            WHERE Distribution.enable_bug_expiration IS TRUE""",
        IDistroSeries: """
            SELECT NULL, DistroSeries.id, NULL, NULL,
                Distribution.id, NULL
            FROM DistroSeries
                JOIN Distribution
                    ON DistroSeries.distribution = Distribution.id
            WHERE Distribution.enable_bug_expiration IS TRUE""",
        IProduct: """
            SELECT NULL, NULL, Product.id, NULL,
                NULL, Product.id
            FROM Product
            WHERE Product.enable_bug_expiration IS TRUE""",
        IProductSeries: """
            SELECT NULL, NULL, NULL, ProductSeries.id,
                NULL, Product.id
            FROM ProductSeries
                JOIN Product
                    ON ProductSeries.Product = Product.id
            WHERE Product.enable_bug_expiration IS TRUE""",
        }

    TARGET_JOIN_CLAUSE = {
        IDistribution: "BugTask.distribution = target.distribution",
        IDistroSeries: "BugTask.distroseries = target.distroseries",
        IProduct: "BugTask.product = target.product",
        IProductSeries: "BugTask.productseries = target.productseries",
        }

    def _getJoinForTargets(self, *targets):
        """Build the UNION of the sub-query for the given set of targets."""
        selects = ' UNION '.join(
            self.TARGET_SELECT[target] for target in targets)
        join_clause = ' OR '.join(
            self.TARGET_JOIN_CLAUSE[target] for target in targets)
        # We create this rather bizarre looking structure
        # because we must replicate the behaviour of BugTask since
        # we are joining to it. So when distroseries is set,
        # distribution should be NULL. The two pillar columns will
        # be used in the WHERE clause.
        return """
        JOIN (
            SELECT 0 AS distribution, 0 AS distroseries,
                   0 AS product , 0 AS productseries,
                   0 AS distribution_pillar, 0 AS product_pillar
            UNION %s
            ) target
            ON (%s)""" % (selects, join_clause)

    def _getTargetJoinAndClause(self, target):
        """Return a SQL join clause to a `BugTarget`.

        :param target: A supported BugTarget or None. The target param must
            be either a Distribution, DistroSeries, Product, or ProductSeries.
            If target is None, the clause joins BugTask to all the supported
            BugTarget tables.
        :raises NotImplementedError: If the target is an IProjectGroup,
            ISourcePackage, or an IDistributionSourcePackage.
        :raises AssertionError: If the target is not a known implementer of
            `IBugTarget`
        """
        if target is None:
            target_join = self._getJoinForTargets(
                IDistribution, IDistroSeries, IProduct, IProductSeries)
            target_clause = "TRUE IS TRUE"
        elif IDistribution.providedBy(target):
            target_join = self._getJoinForTargets(
                IDistribution, IDistroSeries)
            target_clause = "target.distribution_pillar = %s" % sqlvalues(
                target)
        elif IDistroSeries.providedBy(target):
            target_join = self._getJoinForTargets(IDistroSeries)
            target_clause = "BugTask.distroseries = %s" % sqlvalues(target)
        elif IProduct.providedBy(target):
            target_join = self._getJoinForTargets(IProduct, IProductSeries)
            target_clause = "target.product_pillar = %s" % sqlvalues(target)
        elif IProductSeries.providedBy(target):
            target_join = self._getJoinForTargets(IProductSeries)
            target_clause = "BugTask.productseries = %s" % sqlvalues(target)
        elif (IProjectGroup.providedBy(target)
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

    def getOpenBugTasksPerProduct(self, user, products):
        """See `IBugTaskSet`."""
        # Local import of Bug to avoid import loop.
        from lp.bugs.model.bug import Bug
        store = getUtility(IStoreSelector).get(MAIN_STORE, DEFAULT_FLAVOR)
        origin = [
            Bug,
            Join(BugTask, BugTask.bug == Bug.id),
            ]

        product_ids = [product.id for product in products]
        conditions = And(
            BugTask._status.is_in(DB_UNRESOLVED_BUGTASK_STATUSES),
            Bug.duplicateof == None,
            BugTask.productID.is_in(product_ids))

        privacy_filter = get_bug_privacy_filter(user)
        if privacy_filter != '':
            conditions = And(conditions, privacy_filter)
        result = store.using(*origin).find(
            (BugTask.productID, SQL('COUNT(*)')),
            conditions)

        result = result.group_by(BugTask.productID)
        # The result will return a list of product ids and counts,
        # which will be converted into key-value pairs in the dictionary.
        return dict(result)

    def getOrderByColumnDBName(self, col_name):
        """See `IBugTaskSet`."""
        if BugTaskSet._ORDERBY_COLUMN is None:
            # Avoid circular imports.
            from lp.bugs.model.bug import (
                Bug,
                BugTag,
                )
            from lp.registry.model.milestone import Milestone
            from lp.registry.model.person import Person
            Assignee = ClassAlias(Person)
            Reporter = ClassAlias(Person)
            BugTaskSet._ORDERBY_COLUMN = {
                "task": (BugTask.id, []),
                "id": (BugTask.bugID, []),
                "importance": (BugTask.importance, []),
                # TODO: sort by their name?
                "assignee": (
                    Assignee.name,
                    [
                        (Assignee,
                         LeftJoin(Assignee, BugTask.assignee == Assignee.id))
                        ]),
                "targetname": (BugTask.targetnamecache, []),
                "status": (BugTask._status, []),
                "title": (Bug.title, []),
                "milestone": (BugTask.milestoneID, []),
                "dateassigned": (BugTask.date_assigned, []),
                "datecreated": (BugTask.datecreated, []),
                "date_last_updated": (Bug.date_last_updated, []),
                "date_closed": (BugTask.date_closed, []),
                "number_of_duplicates": (Bug.number_of_duplicates, []),
                "message_count": (Bug.message_count, []),
                "users_affected_count": (Bug.users_affected_count, []),
                "heat": (BugTask.heat, []),
                "latest_patch_uploaded": (Bug.latest_patch_uploaded, []),
                "milestone_name": (
                    Milestone.name,
                    [
                        (Milestone,
                         LeftJoin(Milestone,
                                  BugTask.milestone == Milestone.id))
                        ]),
                "reporter": (
                    Reporter.name,
                    [
                        (Bug, Join(Bug, BugTask.bug == Bug.id)),
                        (Reporter, Join(Reporter, Bug.owner == Reporter.id))
                        ]),
                "tag": (
                    BugTag.tag,
                    [
                        (Bug, Join(Bug, BugTask.bug == Bug.id)),
                        (BugTag,
                         LeftJoin(
                             BugTag,
                             BugTag.bug == Bug.id and
                             # We want at most one tag per bug. Select the
                             # tag that comes first in alphabetic order.
                             BugTag.id == SQL("""
                                 SELECT id FROM BugTag AS bt
                                 WHERE bt.bug=bug.id ORDER BY bt.name LIMIT 1
                                 """))),
                        ]
                    ),
                "specification": (
                    Specification.name,
                    [
                        (Bug, Join(Bug, BugTask.bug == Bug.id)),
                        (Specification,
                         LeftJoin(
                             Specification,
                             # We want at most one specification per bug.
                             # Select the specification that comes first
                             # in alphabetic order.
                             Specification.id == SQL("""
                                 SELECT Specification.id
                                 FROM SpecificationBug
                                 JOIN Specification
                                     ON SpecificationBug.specification=
                                         Specification.id
                                 WHERE SpecificationBug.bug=Bug.id
                                 ORDER BY Specification.name
                                 LIMIT 1
                                 """))),
                        ]
                    ),
                }
        return BugTaskSet._ORDERBY_COLUMN[col_name]

    def _processOrderBy(self, params):
        """Process the orderby parameter supplied to search().

        This method ensures the sort order will be stable, and converting
        the string supplied to actual column names.

        :return: A Storm order_by tuple.
        """
        # Local import of Bug to avoid import loop.
        from lp.bugs.model.bug import Bug
        orderby = params.orderby
        if orderby is None:
            orderby = []
        elif not zope_isinstance(orderby, (list, tuple)):
            orderby = [orderby]

        orderby_arg = []
        # This set contains columns which are, in practical terms,
        # unique. When these columns are used as sort keys, they ensure
        # the sort will be consistent. These columns will be used to
        # decide whether we need to add the BugTask.bug or BugTask.id
        # columns to make the sort consistent over runs -- which is good
        # for the user and essential for the test suite.
        unambiguous_cols = set([
            Bug.date_last_updated,
            Bug.datecreated,
            Bug.id,
            BugTask.bugID,
            BugTask.date_assigned,
            BugTask.datecreated,
            BugTask.id,
            ])
        # Bug ID is unique within bugs on a product or source package.
        if (params.product or
            (params.distribution and params.sourcepackagename) or
            (params.distroseries and params.sourcepackagename)):
            in_unique_context = True
        else:
            in_unique_context = False

        if in_unique_context:
            unambiguous_cols.add(BugTask.bug)

        # Translate orderby keys into corresponding Table.attribute
        # strings.
        extra_joins = []
        ambiguous = True
        # Sorting by milestone only is a very "coarse" sort order.
        # If no additional sort order is specified, add the bug task
        # importance as a secondary sort order.
        if len(orderby) == 1:
            if orderby[0] == 'milestone_name':
                # We want the most important bugtasks first; these have
                # larger integer values.
                orderby.append('-importance')
            elif orderby[0] == '-milestone_name':
                orderby.append('importance')
            else:
                # Other sort orders don't need tweaking.
                pass

        for orderby_col in orderby:
            if isinstance(orderby_col, SQLConstant):
                orderby_arg.append(orderby_col)
                continue
            if orderby_col.startswith("-"):
                col, sort_joins = self.getOrderByColumnDBName(orderby_col[1:])
                extra_joins.extend(sort_joins)
                order_clause = Desc(col)
            else:
                col, sort_joins = self.getOrderByColumnDBName(orderby_col)
                extra_joins.extend(sort_joins)
                order_clause = col
            if col in unambiguous_cols:
                ambiguous = False
            orderby_arg.append(order_clause)

        if ambiguous:
            if in_unique_context:
                orderby_arg.append(BugTask.bugID)
            else:
                orderby_arg.append(BugTask.id)

        return tuple(orderby_arg), extra_joins

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
                any(*DB_UNRESOLVED_BUGTASK_STATUSES)))

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
            sum_template % (
                'BugTask.importance %s' % search_value_to_where_condition(
                    BugTaskImportance.HIGH), 'open_high_bugs'),
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
             open_inprogress_bugs,
             open_high_bugs) in shortlist(cur.fetchall()):
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
                open_high=open_high_bugs,
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
                open_inprogress=0, open_high=0)
            counts.append(package_counts)

        return counts

    def getBugTaskTargetMilestones(self, bugtasks):
        from lp.registry.model.distribution import Distribution
        from lp.registry.model.distroseries import DistroSeries
        from lp.registry.model.milestone import Milestone
        from lp.registry.model.product import Product
        from lp.registry.model.productseries import ProductSeries
        store = Store.of(bugtasks[0])
        distro_ids = set()
        distro_series_ids = set()
        product_ids = set()
        product_series_ids = set()

        # Gather all the ids that might have milestones to preload for the
        # for the milestone vocabulary
        for task in bugtasks:
            task = removeSecurityProxy(task)
            distro_ids.add(task.distributionID)
            distro_series_ids.add(task.distroseriesID)
            product_ids.add(task.productID)
            product_series_ids.add(task.productseriesID)

        distro_ids.discard(None)
        distro_series_ids.discard(None)
        product_ids.discard(None)
        product_series_ids.discard(None)

        milestones = store.find(
            Milestone,
            Or(
                Milestone.distributionID.is_in(distro_ids),
                Milestone.distroseriesID.is_in(distro_series_ids),
                Milestone.productID.is_in(product_ids),
                Milestone.productseriesID.is_in(product_series_ids)))

        # Pull in all the related pillars
        list(store.find(
            Distribution, Distribution.id.is_in(distro_ids)))
        list(store.find(
            DistroSeries, DistroSeries.id.is_in(distro_series_ids)))
        list(store.find(
            Product, Product.id.is_in(product_ids)))
        list(store.find(
            ProductSeries, ProductSeries.id.is_in(product_series_ids)))

        return milestones

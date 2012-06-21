# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.expr import (
    Alias,
    And,
    Cast,
    Count,
    Join,
    Select,
    Union,
    With,
    )
from storm.properties import (
    Bool,
    Int,
    Unicode,
    )

from lp.bugs.model.bug import BugTag
from lp.bugs.model.bugsubscription import BugSubscription
from lp.bugs.model.bugsummary import RawBugSummary
from lp.bugs.model.bugtask import (
    bug_target_to_key,
    bug_target_from_key,
    BugTask,
    )
from lp.bugs.model.bugtaskflat import BugTaskFlat
from lp.registry.enums import (
    PRIVATE_INFORMATION_TYPES,
    PUBLIC_INFORMATION_TYPES,
    )
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.series import ISeriesMixin
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.registry.model.distribution import Distribution
from lp.registry.model.distroseries import DistroSeries
from lp.registry.model.sourcepackagename import SourcePackageName
from lp.services.database.lpstorm import IStore
from lp.services.looptuner import TunableLoop


def get_bugsummary_targets():
    """Get the current set of targets represented in BugSummary."""
    return set(IStore(RawBugSummary).find(
        (RawBugSummary.product_id, RawBugSummary.productseries_id,
         RawBugSummary.distribution_id, RawBugSummary.distroseries_id,
         RawBugSummary.sourcepackagename_id)).config(distinct=True))


def get_bugtask_targets():
    """Get the current set of targets represented in BugTask."""
    new_targets = set(IStore(BugTask).find(
        (BugTask.productID, BugTask.productseriesID,
         BugTask.distributionID, BugTask.distroseriesID,
         BugTask.sourcepackagenameID)).config(distinct=True))
    # BugSummary counts package tasks in the packageless totals, so
    # ensure that there's also a packageless total for each distro(series).
    new_targets.update(set(
        (p, ps, d, ds, None) for (p, ps, d, ds, spn) in new_targets))
    return new_targets


def load_target(pid, psid, did, dsid, spnid):
    store = IStore(Product)
    p = store.get(Product, pid)
    ps = store.get(ProductSeries, psid)
    d = store.get(Distribution, did)
    ds = store.get(DistroSeries, dsid)
    spn = store.get(SourcePackageName, spnid)
    return bug_target_from_key(p, ps, d, ds, spn)


def format_target(target):
    id = target.pillar.name
    series = (
        (ISeriesMixin.providedBy(target) and target)
        or getattr(target, 'distroseries', None)
        or getattr(target, 'productseries', None))
    if series:
        id += '/%s' % series.name
    spn = getattr(target, 'sourcepackagename', None)
    if spn:
        id += '/+source/%s' % spn.name
    return id


def get_bugsummary_constraint(target):
    raw_key = bug_target_to_key(target)
    return [
        getattr(RawBugSummary, '%s_id' % k) == (v.id if v else None)
        for (k, v) in raw_key.items()]


def get_bugtaskflat_constraint(target):
    raw_key = bug_target_to_key(target)
    # For the purposes of BugSummary, DSP/SP tasks count for their
    # distro(series).
    if IDistribution.providedBy(target) or IDistroSeries.providedBy(target):
        del raw_key['sourcepackagename']
    return [
        getattr(BugTaskFlat, '%s_id' % k) == (v.id if v else None)
        for (k, v) in raw_key.items()]


def get_bugsummary_rows(target):
    return IStore(RawBugSummary).find(
        (RawBugSummary.product_id, RawBugSummary.productseries_id,
         RawBugSummary.distribution_id, RawBugSummary.distroseries_id,
         RawBugSummary.sourcepackagename_id, RawBugSummary.milestone_id,
         RawBugSummary.status, RawBugSummary.importance, RawBugSummary.tag,
         RawBugSummary.viewed_by_id, RawBugSummary.has_patch,
         RawBugSummary.count),
        *get_bugsummary_constraint(target))


def rebuild_bugsummary_for_target(target, log):
    log.debug("Rebuilding %s" % format_target(target))
    log.debug(
        '%d existing BugSummary rows'
        % len(get_bugsummary_rows(target)))


def calculate_bugsummary_rows(target):
    bugtaskflat_constraints = get_bugtaskflat_constraint(target)

    relevant_tasks = With(
        'relevant_task',
        Select(
            (BugTaskFlat.bug_id, BugTaskFlat.information_type,
             BugTaskFlat.status, BugTaskFlat.milestone_id,
             BugTaskFlat.importance,
             Alias(BugTaskFlat.latest_patch_uploaded != None, 'has_patch')),
            tables=[BugTaskFlat],
            where=And(
                BugTaskFlat.duplicateof_id == None,
                *bugtaskflat_constraints)))

    class RelevantTask(BugTaskFlat):
        __storm_table__ = 'relevant_task'

        has_patch = Bool()

    class BugSummaryPrototype(BugTaskFlat):
        __storm_table__ = 'bugsummary_prototype'

        has_patch = Bool()
        tag = Unicode()
        viewed_by_id = Int(name='viewed_by')

    common_cols = (
        RelevantTask.status, RelevantTask.milestone_id,
        RelevantTask.importance, RelevantTask.has_patch)
    null_tag = Alias(Cast(None, 'text'), 'tag')
    null_viewed_by = Alias(Cast(None, 'integer'), 'viewed_by')

    tag_join = Join(BugTag, BugTag.bugID == RelevantTask.bug_id)
    sub_join = Join(
        BugSubscription,
        BugSubscription.bug_id == RelevantTask.bug_id)

    public_constraint = RelevantTask.information_type.is_in(
        PUBLIC_INFORMATION_TYPES)
    private_constraint = RelevantTask.information_type.is_in(
        PRIVATE_INFORMATION_TYPES)

    unions = Union(
        Select(
            common_cols + (null_tag, null_viewed_by),
            tables=[RelevantTask], where=public_constraint),
        Select(
            common_cols + (BugTag.tag, null_viewed_by),
            tables=[RelevantTask, tag_join], where=public_constraint),
        Select(
            common_cols + (null_tag, BugSubscription.person_id),
            tables=[RelevantTask, sub_join], where=private_constraint),
        Select(
            common_cols + (BugTag.tag, BugSubscription.person_id),
            tables=[RelevantTask, sub_join, tag_join],
            where=private_constraint),
        all=True)

    proto_key_cols = (
        BugSummaryPrototype.status, BugSummaryPrototype.milestone_id,
        BugSummaryPrototype.importance, BugSummaryPrototype.has_patch,
        BugSummaryPrototype.tag, BugSummaryPrototype.viewed_by_id)

    origin = IStore(BugTaskFlat).with_(relevant_tasks).using(
        Alias(unions, 'bugsummary_prototype'))
    results = origin.find(proto_key_cols + (Count(),))
    results = results.group_by(*proto_key_cols).order_by(*proto_key_cols)
    return results


class BugSummaryRebuildTunableLoop(TunableLoop):

    maximum_chunk_size = 100

    def __init__(self, log, abort_time=None):
        super(BugSummaryRebuildTunableLoop, self).__init__(log, abort_time)
        self.targets = list(
            get_bugsummary_targets().union(get_bugtask_targets()))
        self.offset = 0

    def isDone(self):
        return self.offset >= len(self.targets)

    def __call__(self, chunk_size):
        chunk_size = int(chunk_size)
        chunk = self.targets[self.offset:self.offset + chunk_size]

        for target_key in chunk:
            target = load_target(*target_key)
            rebuild_bugsummary_for_target(target, self.log)
        self.offset += len(chunk)

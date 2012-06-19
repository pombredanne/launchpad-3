# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.model.bugsummary import RawBugSummary
from lp.bugs.model.bugtask import BugTask
from lp.registry.interfaces.series import ISeriesMixin
from lp.services.database.lpstorm import IStore


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


def get_bugsummary_rows(*args):
    results = IStore(RawBugSummary).find(
        (RawBugSummary.product_id, RawBugSummary.productseries_id,
         RawBugSummary.distribution_id, RawBugSummary.distroseries_id,
         RawBugSummary.sourcepackagename_id, RawBugSummary.milestone_id,
         RawBugSummary.status, RawBugSummary.importance, RawBugSummary.tag,
         RawBugSummary.viewed_by_id, RawBugSummary.has_patch,
         RawBugSummary.count),
        *args)
    return set(results)

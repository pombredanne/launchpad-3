# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from lp.bugs.model.bugsummary import BugSummary
from lp.bugs.model.bugtask import BugTask
from lp.services.database.lpstorm import IStore


def get_bugsummary_targets():
    """Get the current set of targets represented in BugSummary."""
    return set(IStore(BugSummary).find(
        (BugSummary.product_id, BugSummary.productseries_id,
         BugSummary.distribution_id, BugSummary.distroseries_id,
         BugSummary.sourcepackagename_id)).config(distinct=True))


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

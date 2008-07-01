# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Publish a vcs import branch from the importd slave.

XXX MichaelHudson 2008-06-06, bug=232076 we only need the code that
remains in this module to test the conversion from old-style to
new-style import.  When that code is deleted, this module can go too.
"""

__metaclass__ = type

__all__ = ['ensure_series_branch']


from zope.component import getUtility

from canonical.launchpad.interfaces import (
    BranchType, ILaunchpadCelebrities, IBranchSet)


def ensure_series_branch(series):
    """Ensure a ProductSeries has as associated vcs-imports branch.

    :param series: ProductSeries database object specifying a VCS import.
    """
    if series.import_branch is None:
        series.import_branch = create_branch_for_series(series)


def create_branch_for_series(series):
    """Create the Branch registration for the VCS import.

    :param series: ProductSeries database object specifying a VCS import.
    :return: Branch database object used to publish that VCS import.
    """
    name = series.name
    vcs_imports = getUtility(ILaunchpadCelebrities).vcs_imports
    product = series.product
    branch = getUtility(IBranchSet).new(
        BranchType.IMPORTED, name, vcs_imports, vcs_imports, product,
        url=None)
    return branch

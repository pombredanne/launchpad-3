# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX write me."""

from zope.component import getUtility

from lp.code.interfaces.branchnamespace import IBranchNamespaceSet
from lp.code.enums import BranchType
from lp.registry.interfaces.sourcepackage import ISourcePackageFactory

__metaclass__ = type
__all__ = []


def make_db_branch_in_new_distro_series(db_branch, new_distro_series):
    new_namespace = getUtility(IBranchNamespaceSet).get(
        person=db_branch.owner, product=None, distroseries=new_distro_series,
        sourcepackagename=db_branch.sourcepackagename)
    # Specify title?
    new_branch = new_namespace.new(
        BranchType.HOSTED, db_branch.name, db_branch.registrant)
    return new_branch

def clone_branch(db_branch, new_distro_series):
    assert db_branch.product is None
    assert db_branch.distroseries is not None
    new_branch = make_db_branch_in_new_distro_series(
        db_branch, new_distro_series)
    getUtility(ISourcePackageFactory).new(
        sourcepackagename=new_branch.sourcepackagename,
        distroseries=new_distro_series)

    # make new db branch
    # make it official

    # for both hosted and mirrored area:
    #  move .bzr directory from old to new (some abstraction violations here!)
    #  init branch at old location
    #  set stacked on url for old location
    #  pull from new location to new


def branch_ubuntu():
    pass

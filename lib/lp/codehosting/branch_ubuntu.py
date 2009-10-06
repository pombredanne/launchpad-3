# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XXX write me."""

import os

from bzrlib.bzrdir import BzrDir

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchpadCelebrities
from canonical.config import config

from lp.code.interfaces.branchnamespace import IBranchNamespaceSet
from lp.code.enums import BranchType
from lp.codehosting.vfs import branch_id_to_path
from lp.registry.interfaces.pocket import PackagePublishingPocket

__metaclass__ = type
__all__ = []


def make_db_branch_in_new_distro_series(db_branch, new_distro_series):
    new_namespace = getUtility(IBranchNamespaceSet).get(
        person=db_branch.owner, product=None, distroseries=new_distro_series,
        sourcepackagename=db_branch.sourcepackagename)
    new_branch = new_namespace.createBranch(
        BranchType.HOSTED, db_branch.name, db_branch.registrant)
    return new_branch


def make_branch_official(new_branch):
    new_branch.sourcepackage.setBranch(
        PackagePublishingPocket.RELEASE, new_branch,
        getUtility(ILaunchpadCelebrities).ubuntu_branches.teamowner)


def switch_branches(prefix, scheme, old_branch, new_branch):
    # What happens if this function gets interrupted?
    #  move .bzr directory from old to new
    os.makedirs(os.path.join(prefix, branch_id_to_path(new_branch.id)))
    os.rename(
        os.path.join(prefix, branch_id_to_path(old_branch.id), '.bzr'),
        os.path.join(prefix, branch_id_to_path(new_branch.id), '.bzr'))

    #  init branch at old location
    new_location_bzrdir = BzrDir.open(scheme + new_branch.unique_name)
    old_location_bzrdir = new_location_bzrdir.clone(
        scheme + old_branch.unique_name, revision_id='null:')

    #  set stacked on url for old location
    old_location_branch = old_location_bzrdir.open_branch()
    old_location_branch.set_stacked_on_url('/' + new_branch.unique_name)

    #  pull from new location to new
    old_location_branch.pull(new_location_bzrdir.open_branch())


def clone_branch(db_branch, new_distro_series):
    assert db_branch.product is None
    assert db_branch.distroseries is not None
    # make new db branch
    new_branch = make_db_branch_in_new_distro_series(
        db_branch, new_distro_series)
    # make it official
    make_branch_official(new_branch)

    # for both hosted and mirrored area:
    #  move .bzr directory from old to new (some abstraction violations here!)
    #  init branch at old location
    #  set stacked on url for old location
    #  pull from new location to new
    switch_branches(
        config.codehosting.mirrored_branches_root, 'lp-mirrored://', db_branch,
        new_branch)
    switch_branches(
        config.codehosting.hosted_branches_root, 'lp-hosted://', db_branch,
        new_branch)


def branch_ubuntu():
    pass

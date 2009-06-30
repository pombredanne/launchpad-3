# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for different objects to branch collections."""

__metaclass__ = type
__all__ = [
    'branch_collection_for_person',
    'branch_collection_for_product',
    'branch_collection_for_project',
    ]


from zope.component import getUtility

from lp.code.interfaces.branchcollection import IAllBranches


def branch_collection_for_product(product):
    """Adapt a product to a branch collection."""
    return getUtility(IAllBranches).inProduct(product)


def branch_collection_for_project(project):
    """Adapt a project to a branch collection."""
    return getUtility(IAllBranches).inProject(project)


def branch_collection_for_person(person):
    """Adapt a person to a branch collection."""
    return getUtility(IAllBranches).ownedBy(person)

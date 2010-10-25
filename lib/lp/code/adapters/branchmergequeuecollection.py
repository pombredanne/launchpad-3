# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Adapters for different objects to branch merge queue collections."""

__metaclass__ = type
__all__ = [
    'branch_collection_for_person',
    ]


from zope.component import getUtility

from lp.code.interfaces.branchmergequeuecollection import (
    IAllBranchMergeQueues,
    )


def merge_queue_collection_for_person(person):
    """Adapt a person to a branch collection."""
    return getUtility(IAllBranchMergeQueues).ownedBy(person)

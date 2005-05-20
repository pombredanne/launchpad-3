# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Validators for IBug fields."""

__metaclass__ = type

from zope.component import getUtility
from sqlobject import SQLObjectNotFound
from canonical.launchpad.interfaces import ILaunchBag

# XXX: Brad Bollenbach, 2005-04-19: Circular import.
# from canonical.launchpad.interfaces import IBugSet

def non_duplicate_bug(value):
    """Prevent dups of dups.

    Returns True if the dup target is not a duplicate /and/ if the
    current bug doesn't have any duplicates referencing it, otherwise
    return False.
    """
    # XXX: Brad Bollenbach, 2005-04-19: Need to resolve circular
    # import. (See imports near top of file for where I attempted to
    # import this interface.)
    from canonical.launchpad.interfaces import IBugSet

    bugset = getUtility(IBugSet)
    duplicate = getUtility(ILaunchBag).bug
    dup_target = bugset.get(value)
    current_bug_has_dup_refs = bugset.search(duplicateof = duplicate).count()
    target_is_dup = dup_target.duplicateof

    if (not target_is_dup) and (not current_bug_has_dup_refs):
        return True
    else:
        return False

# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type


from canonical.database.sqlbase import block_implicit_flushes
from canonical.launchpad.interfaces import SpecificationGoalStatus


@block_implicit_flushes
def specification_goalstatus(spec, event):
    """Update goalstatus if productseries or distroseries is changed."""
    delta = spec.getDelta(event.object_before_modification, event.user)
    if delta is None:
        return
    if delta.productseries is not None or delta.distroseries is not None:
        spec.goalstatus = SpecificationGoalStatus.PROPOSED

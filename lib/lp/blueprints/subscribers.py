# Copyright 2009-2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


from canonical.database.sqlbase import block_implicit_flushes
from lp.blueprints.enums import SpecificationGoalStatus
from lp.registry.interfaces.person import IPerson


@block_implicit_flushes
def specification_goalstatus(spec, event):
    """Update goalstatus if productseries or distroseries is changed."""
    delta = spec.getDelta(
        event.object_before_modification, IPerson(event.user))
    if delta is None:
        return
    if delta.productseries is not None or delta.distroseries is not None:
        spec.goalstatus = SpecificationGoalStatus.PROPOSED


def specification_update_lifecycle_status(spec, event):
    """Mark the specification as started and/or complete if appropriate.

    Does nothing if there is no user associated with the event.
    """
    if event.user is None:
        return
    spec.updateLifecycleStatus(IPerson(event.user))

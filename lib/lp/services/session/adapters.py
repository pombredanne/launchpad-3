# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Session adapters."""

__metaclass__ = type
__all__ = []


from zope.component import adapter
from zope.interface import implementer

from canonical.database.sqlbase import session_store
from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore, ISlaveStore, IStore)
from lp.services.session.interfaces import ISessionStormClass


@adapter(ISessionStormClass)
@implementer(IMasterStore)
def session_master_store(cls):
    """Adapt a Session database class to an `IMasterStore`."""
    return session_store()


@adapter(ISessionStormClass)
@implementer(ISlaveStore)
def session_slave_store(cls):
    """Adapt a Session database class to an `ISlaveStore`."""
    return session_store()


@adapter(ISessionStormClass)
@implementer(IStore)
def session_default_store(cls):
    """Adapt an Session database class to an `IStore`."""
    return session_store()

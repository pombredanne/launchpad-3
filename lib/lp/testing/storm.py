# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'reload_object',
    ]


from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.distribution import Distribution


def reload_object(obj):
    """Return a new instance of a storm objet from the store."""
    store = IStore(Distribution)
    return store.get(removeSecurityProxy(obj).__class__, obj.id)

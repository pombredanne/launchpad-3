# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'reload_object',
    'reload_dsp',
    ]


from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.model.distribution import Distribution


def reload_object(obj):
    """Return a new instance of a storm objet from the store."""
    store = IStore(Distribution)
    return store.get(removeSecurityProxy(obj).__class__, obj.id)


def reload_dsp(dsp):
    """Return a new instance of a DistributionSourcePackage from the store."""
    store = IStore(Distribution)
    distribution_class = removeSecurityProxy(dsp.distribution.__class__)
    distribution = store.get(distribution_class, dsp.distribution.id)
    spn_class = removeSecurityProxy(dsp.sourcepackagename.__class__)
    spn = store.get(spn_class, dsp.sourcepackagename.id)
    return distribution.getSourcePackage(name=spn.name)

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helper functions dealing with IServiceUsage."""
__metaclass__ = type

import transaction
from zope.component import getUtility

from lp.app.enums import ServiceUsage
from lp.registry.interfaces.pillar import IPillarNameSet
from lp.testing import (
    login,
    logout,
    )
from lp.testing.factory import LaunchpadObjectFactory
from lp.testing.sampledata import ADMIN_EMAIL


def set_service_usage(pillar_name, **kw):
    factory = LaunchpadObjectFactory()
    login(ADMIN_EMAIL)
    pillar = getUtility(IPillarNameSet)[pillar_name]
    for attr, service_usage_name in kw.items():
        service_usage = getattr(ServiceUsage, service_usage_name)
        if attr == 'bug_tracking_usage':
            pillar.official_malone = (service_usage == ServiceUsage.LAUNCHPAD)
            if service_usage == ServiceUsage.EXTERNAL:
                pillar.bugtracker = factory.makeBugTracker()
        else:
            setattr(pillar, attr, service_usage)
    #transaction.commit()
    logout()

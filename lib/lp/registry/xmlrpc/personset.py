# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""XMLRPC APIs for person set."""

__metaclass__ = type
__all__ = [
    'PersonSetAPIView',
    ]


from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.webapp import LaunchpadXMLRPCView
from lp.registry.interfaces.person import (
    IPersonSet, IPersonSetAPIView, IPersonSetApplication,
    PersonCreationRationale)


class PersonSetAPIView(LaunchpadXMLRPCView):
    """See `IPersonSetAPIView`."""

    implements(IPersonSetAPIView)

    def getOrCreateByOpenIDIdentifier(self, openid_identifier, email,
                                      full_name):
        person, db_updated = getUtility(IPersonSet).getOrCreateByOpenIDIdentifier(
            openid_identifier, email, full_name,
            PersonCreationRationale.SOFTWARE_CENTER_PURCHASE,
            "when purchasing an application via Software Center.")

        return person.name


class PersonSetApplication:
    """Personset end-point."""
    implements(IPersonSetApplication)

    title = "PersonSet API"


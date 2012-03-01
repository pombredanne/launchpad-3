# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for pillar and artifact access policy services."""

__metaclass__ = type
__all__ = [
    'AccessPolicyService',
    ]

from lazr.restful import EntryResource
from lazr.restful.utils import get_current_web_service_request

from zope.component import getUtility
from zope.interface import implements

from lp.registry.enums import AccessPolicyType
from lp.registry.interfaces.accesspolicyservice import IAccessPolicyService
from lp.registry.interfaces.person import IPersonSet


class AccessPolicyService:
    """Service providing operations for access policies.

    Service is accessed via a url of the form
    '/services/accesspolicy?ws.op=...
    """

    implements(IAccessPolicyService)

    @property
    def name(self):
        """See `IService`."""
        return 'accesspolicy'

    def getAccessPolicies(self):
        """See `IAccessPolicyService`."""
        policies = []
        for x, policy in enumerate(AccessPolicyType):
            item = dict(
                index=x,
                value=policy.token,
                title=policy.title,
                description=policy.value.description
            )
            policies.append(item)
        return policies

    def getSharingPermissions(self):
        """See `IAccessPolicyService`."""
        # TODO - use proper model class
        sharing_permissions = [
            {'value': 'all', 'name': 'All',
             'title': 'share bug and branch subscriptions'},
            {'value': 'some', 'name': 'Some',
             'title': 'share bug and branch subscriptions'},
            {'value': 'nothing', 'name': 'Nothing',
             'title': 'revoke all bug and branch subscriptions'}
        ]
        return sharing_permissions

    def getProductObservers(self, product):
        """See `IAccessPolicyService`."""
        # TODO - replace this sample data with something real
        result = []
        request = get_current_web_service_request()
        personset = getUtility(IPersonSet)
        for id in range(1, 4):
            person = personset.get(id)
            resource = EntryResource(person, request)
            person_data = resource.toDataForJSON()
            permissions = {
                'PROPRIETARY': 'some',
                'EMBARGOEDSECURITY': 'all'
            }
            if id > 2:
                permissions['USERDATA'] = 'some'
            person_data['permissions'] = permissions
            result.append(person_data)
        return result

    def deleteProductObserver(self, product, observer):
        """See `IAccessPolicyService`."""
        # TODO - implement this
        pass

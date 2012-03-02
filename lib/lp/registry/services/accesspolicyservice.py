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

from lp.registry.enums import (
    AccessPolicyType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessPolicySource,
    IAccessPolicyGrantSource,
    )
from lp.registry.interfaces.accesspolicyservice import IAccessPolicyService
from lp.services.webapp.authorization import available_with_permission


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
        sharing_permissions = []
        for permission in SharingPermission:
            item = dict(
                value=permission.token,
                title=permission.title,
                description=permission.value.description
            )
            sharing_permissions.append(item)
        return sharing_permissions

    @available_with_permission('launchpad.Driver', 'pillar')
    def getPillarObservers(self, pillar):
        """See `IAccessPolicyService`."""

        # Currently support querying for sharing_permission = ALL
        # TODO - support querying for sharing_permission = SOME

        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        policy_grants = policy_grant_source.findByPolicy(policies)

        result = []
        person_by_id = {}
        request = get_current_web_service_request()
        for policy_grant in policy_grants:
            if not policy_grant.grantee.id in person_by_id:
                resource = EntryResource(policy_grant.grantee, request)
                person_data = resource.toDataForJSON()
                person_data['permissions'] = {}
                person_by_id[policy_grant.grantee.id] = person_data
            person_data = person_by_id[policy_grant.grantee.id]
            person_data['permissions'][policy_grant.policy.type.name] = (
                SharingPermission.ALL.name)
            result.append(person_data)
        return result

    @available_with_permission('launchpad.Edit', 'pillar')
    def addPillarObserver(self, pillar, observer, access_policy_type, user):
        """See `IAccessPolicyService`."""

        # Create a pillar access policy if one doesn't exist.
        policy_source = getUtility(IAccessPolicySource)
        pillar_access_policy = [(pillar, access_policy_type)]
        policy = policy_source.find(pillar_access_policy).one()
        if policy is None:
            [policy] = policy_source.create(pillar_access_policy)
        # We have a policy, create the grant if it doesn't exist.
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        if policy_grant_source.find([(policy, observer)]).count() == 0:
            policy_grant_source.grant([(policy, observer, user)])

        # Return observer data to the caller.
        request = get_current_web_service_request()
        resource = EntryResource(observer, request)
        person_data = resource.toDataForJSON()
        permissions = {
            access_policy_type.name: SharingPermission.ALL.name,
        }
        person_data['permissions'] = permissions
        return person_data

    @available_with_permission('launchpad.Edit', 'pillar')
    def deletePillarObserver(self, pillar, observer, access_policy_type):
        """See `IAccessPolicyService`."""
        # TODO - implement this
        pass

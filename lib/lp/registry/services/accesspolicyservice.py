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
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
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

    def getAccessPolicies(self, pillar):
        """See `IAccessPolicyService`."""

        allowed_policy_types = [
            AccessPolicyType.EMBARGOEDSECURITY,
            AccessPolicyType.USERDATA]
        # Products with current commercial subscriptions are also allowed to
        # have a PROPRIETARY access policy.
        if (IProduct.providedBy(pillar) and
                pillar.has_current_commercial_subscription):
            allowed_policy_types.append(AccessPolicyType.PROPRIETARY)

        policies_data = []
        for x, policy in enumerate(allowed_policy_types):
            item = dict(
                index=x,
                value=policy.name,
                title=policy.title,
                description=policy.description
            )
            policies_data.append(item)
        return policies_data

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
    def updatePillarObserver(self, pillar, observer, access_policy_types,
                             user):
        """See `IAccessPolicyService`."""

        # We do not support adding observers to project groups.
        assert not IProjectGroup.providedBy(pillar)

        pillar_policy_types = [(pillar, access_policy_type)
                            for access_policy_type in access_policy_types]

        # Create any missing pillar access policies.
        policy_source = getUtility(IAccessPolicySource)
        pillar_policies = list(policy_source.find(pillar_policy_types))
        existing_policy_types = [(pillar, pillar_policy.type)
                                 for pillar_policy in pillar_policies]
        required_policies = (
            set(pillar_policy_types).difference(existing_policy_types))
        if len(required_policies) > 0:
            pillar_policies.extend(policy_source.create(required_policies))

        # We have the policies, we need to figure out which grants we need to
        # create. We also need to revoke any grants which are not required.
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        policy_grants = [(policy, observer) for policy in pillar_policies]
        existing_grants = [(grant.policy, grant.grantee)
                        for grant in policy_grant_source.find(policy_grants)]
        required_grants = set(policy_grants).difference(existing_grants)

        all_pillar_policies = policy_source.findByPillar([pillar])
        possible_policy_grants = [(policy, observer)
                for policy in all_pillar_policies]
        possible_grants = [(grant.policy, grant.grantee)
                for grant in policy_grant_source.find(possible_policy_grants)]

        grants_to_revoke = set(possible_grants).difference(policy_grants)
        # Create any newly required grants.
        if len(required_grants) > 0:
            policy_grant_source.grant([(policy, observer, user)
                                    for policy, observer in required_grants])
        # Now revoke any existing grants no longer required.
        if len(grants_to_revoke) > 0:
            policy_grant_source.revoke(grants_to_revoke)

        # Return observer data to the caller.
        request = get_current_web_service_request()
        resource = EntryResource(observer, request)
        person_data = resource.toDataForJSON()
        permissions = {}
        for access_policy_type in access_policy_types:
            permissions[access_policy_type.name] = SharingPermission.ALL.name
        person_data['permissions'] = permissions
        return person_data

    @available_with_permission('launchpad.Edit', 'pillar')
    def deletePillarObserver(self, pillar, observer, access_policy_type):
        """See `IAccessPolicyService`."""
        # TODO - implement this
        pass

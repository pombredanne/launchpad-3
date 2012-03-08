# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for pillar and artifact sharing service."""

__metaclass__ = type
__all__ = [
    'SharingService',
    ]

from lazr.restful import EntryResource
from lazr.restful.utils import get_current_web_service_request

from zope.component import getUtility
from zope.interface import implements

from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactGrantSource,
    IAccessPolicySource,
    IAccessPolicyGrantFlatSource,
    IAccessPolicyGrantSource,
    )
from lp.registry.interfaces.sharingservice import ISharingService
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.services.webapp.authorization import available_with_permission


class SharingService:
    """Service providing operations for adding and removing pillar sharees.

    Service is accessed via a url of the form
    '/services/sharing?ws.op=...
    """

    implements(ISharingService)

    @property
    def name(self):
        """See `IService`."""
        return 'sharing'

    def getInformationTypes(self, pillar):
        """See `ISharingService`."""
        allowed_types = [
            InformationType.EMBARGOEDSECURITY,
            InformationType.USERDATA]
        # Products with current commercial subscriptions are also allowed to
        # have a PROPRIETARY information type.
        if (IProduct.providedBy(pillar) and
                pillar.has_current_commercial_subscription):
            allowed_types.append(InformationType.PROPRIETARY)

        result_data = []
        for x, policy in enumerate(allowed_types):
            item = dict(
                index=x,
                value=policy.name,
                title=policy.title,
                description=policy.description
            )
            result_data.append(item)
        return result_data

    def getSharingPermissions(self):
        """See `ISharingService`."""
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
    def getPillarSharees(self, pillar):
        """See `ISharingService`."""

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
                result.append(person_data)
            person_data = person_by_id[policy_grant.grantee.id]
            person_data['permissions'][policy_grant.policy.type.name] = (
                SharingPermission.ALL.name)
        return result

    @available_with_permission('launchpad.Edit', 'pillar')
    def updatePillarSharee(self, pillar, sharee, information_types,
                             user):
        """See `ISharingService`."""

        # We do not support adding sharees to project groups.
        assert not IProjectGroup.providedBy(pillar)

        pillar_info_types = [
            (pillar, information_type)
            for information_type in information_types]

        # Create any missing pillar access policies.
        policy_source = getUtility(IAccessPolicySource)
        pillar_policies = list(policy_source.find(pillar_info_types))
        existing_policy_types = [
            (pillar, pillar_policy.type) for pillar_policy in pillar_policies]
        required_policies = (
            set(pillar_info_types).difference(existing_policy_types))
        if len(required_policies) > 0:
            pillar_policies.extend(policy_source.create(required_policies))

        # We have the policies, we need to figure out which grants we need to
        # create. We also need to revoke any grants which are not required.
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        policy_grants = [(policy, sharee) for policy in pillar_policies]
        existing_grants = [
            (grant.policy, grant.grantee)
            for grant in policy_grant_source.find(policy_grants)]
        required_grants = set(policy_grants).difference(existing_grants)

        all_pillar_policies = policy_source.findByPillar([pillar])
        possible_policy_grants = [
            (policy, sharee) for policy in all_pillar_policies]
        possible_grants = [
            (grant.policy, grant.grantee)
            for grant in policy_grant_source.find(possible_policy_grants)]

        grants_to_revoke = set(possible_grants).difference(policy_grants)
        # Create any newly required grants.
        if len(required_grants) > 0:
            policy_grant_source.grant([(policy, sharee, user)
                                    for policy, sharee in required_grants])
        # Now revoke any existing grants no longer required.
        if len(grants_to_revoke) > 0:
            policy_grant_source.revoke(grants_to_revoke)

        # Return sharee data to the caller.
        request = get_current_web_service_request()
        resource = EntryResource(sharee, request)
        person_data = resource.toDataForJSON()
        permissions = {}
        for information_type in information_types:
            permissions[information_type.name] = SharingPermission.ALL.name
        person_data['permissions'] = permissions
        return person_data

    @available_with_permission('launchpad.Edit', 'pillar')
    def deletePillarSharee(self, pillar, sharee,
                             information_types=None):
        """See `ISharingService`."""

        policy_source = getUtility(IAccessPolicySource)
        if information_types is None:
            # We delete all policy grants for the pillar.
            pillar_policies = policy_source.findByPillar([pillar])
        else:
            # We delete selected policy grants for the pillar.
            pillar_policy_types = [
                (pillar, information_type)
                for information_type in information_types]
            pillar_policies = list(policy_source.find(pillar_policy_types))

        # First delete any access policy grants.
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        policy_grants = [(policy, sharee) for policy in pillar_policies]
        grants = [
            (grant.policy, grant.grantee)
            for grant in policy_grant_source.find(policy_grants)]
        policy_grant_source.revoke(grants)

        # Second delete any access artifact grants.
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        to_delete = ap_grant_flat.findArtifactsByGrantee(
            sharee, pillar_policies)
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        accessartifact_grant_source.revokeByArtifact(to_delete)

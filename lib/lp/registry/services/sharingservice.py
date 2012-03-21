# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for pillar and artifact sharing service."""
from lp.registry.model.person import Person

__metaclass__ = type
__all__ = [
    'SharingService',
    ]

from lazr.restful.interfaces import IWebBrowserOriginatingRequest
from lazr.restful.utils import get_current_web_service_request

from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized
from zope.traversing.browser.absoluteurl import absoluteURL

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
from lp.services.features import getFeatureFlag
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

    @property
    def write_enabled(self):
        return bool(getFeatureFlag(
            'disclosure.enhanced_sharing.writable'))

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
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        grantees = ap_grant_flat.findGranteesByPolicy(
            policies).order_by(Person.displayname)
        return grantees

    @available_with_permission('launchpad.Driver', 'pillar')
    def getPillarShareeData(self, pillar, grantees=None):
        """See `ISharingService`."""
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        grant_permissions = ap_grant_flat.findGranteePermissionsByPolicy(
            policies, grantees)

        result = []
        person_by_id = {}
        request = get_current_web_service_request()
        browser_request = IWebBrowserOriginatingRequest(request)
        for (grantee, policy, sharing_permission) in grant_permissions:
            if not grantee.id in person_by_id:
                person_data = {
                    'name': grantee.name,
                    'meta': 'team' if grantee.is_team else 'person',
                    'display_name': grantee.displayname,
                    'self_link': absoluteURL(grantee, request),
                    'permissions': {}}
                person_data['web_link'] = absoluteURL(grantee, browser_request)
                person_by_id[grantee.id] = person_data
                result.append(person_data)
            person_data = person_by_id[grantee.id]
            person_data['permissions'][policy.type.name] = sharing_permission
        return result

    @available_with_permission('launchpad.Edit', 'pillar')
    def sharePillarInformation(self, pillar, sharee, permissions, user):
        """See `ISharingService`."""

        # We do not support adding sharees to project groups.
        assert not IProjectGroup.providedBy(pillar)

        if not self.write_enabled:
            raise Unauthorized("This feature is not yet enabled.")

        # Separate out the info types according to permission.
        information_types = permissions.keys()
        info_types_for_all = [
            info_type for info_type in information_types
            if permissions[info_type] == SharingPermission.ALL]
        info_types_for_some = [
            info_type for info_type in information_types
            if permissions[info_type] == SharingPermission.SOME]
        info_types_for_nothing = [
            info_type for info_type in information_types
            if permissions[info_type] == SharingPermission.NOTHING]

        # The wanted policies are for the information_types in all.
        required_pillar_info_types = [
            (pillar, information_type)
            for information_type in information_types
            if information_type in info_types_for_all]
        policy_source = getUtility(IAccessPolicySource)
        policy_grant_source = getUtility(IAccessPolicyGrantSource)
        if len(required_pillar_info_types) > 0:
            wanted_pillar_policies = policy_source.find(
                required_pillar_info_types)
            # We need to figure out which policy grants to create or delete.
            wanted_policy_grants = [(policy, sharee)
                for policy in wanted_pillar_policies]
            existing_policy_grants = [
                (grant.policy, grant.grantee)
                for grant in policy_grant_source.find(wanted_policy_grants)]
            # Create any newly required policy grants.
            policy_grants_to_create = (
                set(wanted_policy_grants).difference(existing_policy_grants))
            if len(policy_grants_to_create) > 0:
                policy_grant_source.grant(
                    [(policy, sharee, user)
                    for policy, sharee in policy_grants_to_create])

        # Now revoke any existing policy grants for types with
        # permission 'some'.
        all_pillar_policies = policy_source.findByPillar([pillar])
        policy_grants_to_revoke = [
            (policy, sharee)
            for policy in all_pillar_policies
            if policy.type in info_types_for_some]
        if len(policy_grants_to_revoke) > 0:
            policy_grant_source.revoke(policy_grants_to_revoke)

        # For information types with permission 'nothing', we can simply
        # call the deletePillarSharee method directly.
        if len(info_types_for_nothing) > 0:
            self.deletePillarSharee(pillar, sharee, info_types_for_nothing)

        # Return sharee data to the caller.
        sharees = self.getPillarShareeData(pillar, [sharee])
        if not sharees:
            return None
        return sharees[0]

    @available_with_permission('launchpad.Edit', 'pillar')
    def deletePillarSharee(self, pillar, sharee,
                             information_types=None):
        """See `ISharingService`."""

        if not self.write_enabled:
            raise Unauthorized("This feature is not yet enabled.")

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
        if len(grants) > 0:
            policy_grant_source.revoke(grants)

        # Second delete any access artifact grants.
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        to_delete = ap_grant_flat.findArtifactsByGrantee(
            sharee, pillar_policies)
        if to_delete.count() > 0:
            accessartifact_grant_source = getUtility(
                IAccessArtifactGrantSource)
            accessartifact_grant_source.revokeByArtifact(to_delete)

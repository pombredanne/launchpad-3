# Copyright 2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Classes for pillar and artifact sharing service."""

__metaclass__ = type
__all__ = [
    'SharingService',
    ]

from itertools import product

from lazr.restful.interfaces import IWebBrowserOriginatingRequest
from lazr.restful.utils import (
    get_current_web_service_request,
    )

from storm.expr import (
    And,
    In,
    Not,
    Select,
    )
from zope.component import getUtility
from zope.interface import implements
from zope.security.interfaces import Unauthorized
from zope.traversing.browser.absoluteurl import absoluteURL

from lp.app.browser.tales import ObjectImageDisplayAPI
from lp.bugs.interfaces.bugtask import (
    BugTaskSearchParams,
    IBugTaskSet,
    )
from lp.code.interfaces.branchcollection import IAllBranches
from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifactGrantSource,
    IAccessArtifactSource,
    IAccessPolicyGrantFlatSource,
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.registry.interfaces.person import IPersonSet
from lp.registry.interfaces.product import IProduct
from lp.registry.interfaces.projectgroup import IProjectGroup
from lp.registry.interfaces.sharingjob import (
    IRemoveBugSubscriptionsJobSource,
    )
from lp.registry.interfaces.sharingservice import ISharingService
from lp.registry.model.accesspolicy import (
    AccessArtifactGrant,
    AccessPolicyGrant,
    AccessPolicyArtifact,
    )
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.lpstorm import IStore
from lp.services.features import getFeatureFlag
from lp.services.searchbuilder import any
from lp.services.webapp.authorization import (
    available_with_permission,
    check_permission,
    )


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
        return (
            bool(getFeatureFlag(
            'disclosure.enhanced_sharing.writable')))

    def getSharedArtifacts(self, pillar, person, user):
        """See `ISharingService`."""
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        flat_source = getUtility(IAccessPolicyGrantFlatSource)
        bug_ids = set()
        branch_ids = set()
        for artifact in flat_source.findArtifactsByGrantee(person, policies):
            if artifact.bug_id:
                bug_ids.add(artifact.bug_id)
            elif artifact.branch_id:
                branch_ids.add(artifact.branch_id)

        # Load the bugs.
        bugtasks = []
        if bug_ids:
            param = BugTaskSearchParams(user=user, bug=any(*bug_ids))
            param.setTarget(pillar)
            bugtasks = list(getUtility(IBugTaskSet).search(param))
        # Load the branches.
        branches = []
        if branch_ids:
            all_branches = getUtility(IAllBranches)
            wanted_branches = all_branches.visibleByUser(user).withIds(
                *branch_ids)
            branches = list(wanted_branches.getBranches())

        return bugtasks, branches

    def getVisibleArtifacts(self, person, branches=None, bugs=None):
        """See `ISharingService`."""
        bugs_by_id = {}
        branches_by_id = {}
        for bug in bugs or []:
            bugs_by_id[bug.id] = bug
        for branch in branches or []:
            branches_by_id[branch.id] = branch

        # Load the bugs.
        visible_bug_ids = []
        if bugs_by_id:
            param = BugTaskSearchParams(
                user=person, bug=any(*bugs_by_id.keys()))
            visible_bug_ids = set(getUtility(IBugTaskSet).searchBugIds(param))
        visible_bugs = [bugs_by_id[bug_id] for bug_id in visible_bug_ids]

        # Load the branches.
        visible_branches = []
        if branches_by_id:
            all_branches = getUtility(IAllBranches)
            wanted_branches = all_branches.visibleByUser(person).withIds(
                *branches_by_id.keys())
            visible_branches = list(wanted_branches.getBranches())

        return visible_bugs, visible_branches

    def getPeopleWithoutAccess(self, concrete_artifact, people):
        """See `ISharingService`."""
        # Public artifacts allow everyone to have access.
        access_artifacts = list(
            getUtility(IAccessArtifactSource).find([concrete_artifact]))
        if not access_artifacts:
            return []

        access_artifact = access_artifacts[0]
        # Determine the grantees who have access via an access policy grant.
        policy_grantees = (
            Select(
                (TeamParticipation.personID,),
                where=And(
                    AccessPolicyArtifact.abstract_artifact == access_artifact,
                    AccessPolicyGrant.policy_id ==
                        AccessPolicyArtifact.policy_id,
                    AccessPolicyGrant.grantee_id ==
                        TeamParticipation.teamID)))

        # Determine the grantees who have access via an access artifact grant.
        artifact_grantees = (
            Select(
                (TeamParticipation.personID,),
                where=And(
                    AccessArtifactGrant.abstract_artifact_id ==
                        access_artifact.id,
                    AccessArtifactGrant.grantee_id ==
                        TeamParticipation.teamID)))

        person_ids = [person.id for person in people]
        store = IStore(AccessArtifactGrant)
        result_set = store.find(
            Person,
            And(
                Not(In(Person.id, policy_grantees)),
                Not(In(Person.id, artifact_grantees))),
            In(Person.id, person_ids))

        return result_set

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
        # We want the permissions displayed in the following order.
        ordered_permissions = [
            SharingPermission.ALL,
            SharingPermission.SOME,
            SharingPermission.NOTHING
        ]
        sharing_permissions = []
        for x, permission in enumerate(ordered_permissions):
            item = dict(
                index=x,
                value=permission.name,
                title=permission.title,
                description=permission.description
            )
            sharing_permissions.append(item)
        return sharing_permissions

    @available_with_permission('launchpad.Driver', 'pillar')
    def getPillarSharees(self, pillar):
        """See `ISharingService`."""
        policies = getUtility(IAccessPolicySource).findByPillar([pillar])
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        # XXX 2012-03-22 wallyworld bug 961836
        # We want to use person_sort_key(Person.displayname, Person.name) but
        # StormRangeFactory doesn't support that yet.
        grant_permissions = ap_grant_flat.findGranteePermissionsByPolicy(
            policies).order_by(Person.displayname, Person.name)
        return grant_permissions

    @available_with_permission('launchpad.Driver', 'pillar')
    def getPillarShareeData(self, pillar):
        """See `ISharingService`."""
        grant_permissions = list(self.getPillarSharees(pillar))
        if not grant_permissions:
            return None
        return self.jsonShareeData(grant_permissions)

    def jsonShareeData(self, grant_permissions):
        """See `ISharingService`."""
        result = []
        request = get_current_web_service_request()
        browser_request = IWebBrowserOriginatingRequest(request)
        details_enabled = bool((getFeatureFlag(
            'disclosure.enhanced_sharing_details.enabled')))
        # We need to precache icon and validity information for the batch.
        grantee_ids = [grantee[0].id for grantee in grant_permissions]
        list(getUtility(IPersonSet).getPrecachedPersonsFromIDs(
            grantee_ids, need_icon=True, need_validity=True))
        for (grantee, permissions, shared_artifact_types) in grant_permissions:
            some_things_shared = (
                details_enabled and len(shared_artifact_types) > 0)
            sharee_permissions = {}
            for (policy, permission) in permissions.iteritems():
                sharee_permissions[policy.type.name] = permission.name
            shared_artifact_type_names = [
                info_type.name for info_type in shared_artifact_types]
            display_api = ObjectImageDisplayAPI(grantee)
            icon_url = display_api.custom_icon_url()
            sprite_css = display_api.sprite_css()
            result.append({
                'name': grantee.name,
                'icon_url': icon_url,
                'sprite_css': sprite_css,
                'display_name': grantee.displayname,
                'self_link': absoluteURL(grantee, request),
                'web_link': absoluteURL(grantee, browser_request),
                'permissions': sharee_permissions,
                'shared_artifact_types': shared_artifact_type_names,
                'shared_items_exist': some_things_shared})
        return result

    @available_with_permission('launchpad.Edit', 'pillar')
    def sharePillarInformation(self, pillar, sharee, user, permissions):
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
            self.deletePillarSharee(
                pillar, sharee, user, info_types_for_nothing)

        # Return sharee data to the caller.
        ap_grant_flat = getUtility(IAccessPolicyGrantFlatSource)
        grant_permissions = list(ap_grant_flat.findGranteePermissionsByPolicy(
            all_pillar_policies, [sharee]))
        if not grant_permissions:
            return None
        [sharee] = self.jsonShareeData(grant_permissions)
        return sharee

    @available_with_permission('launchpad.Edit', 'pillar')
    def deletePillarSharee(self, pillar, sharee, user,
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
        to_delete = list(ap_grant_flat.findArtifactsByGrantee(
            sharee, pillar_policies))
        if len(to_delete) > 0:
            accessartifact_grant_source = getUtility(
                IAccessArtifactGrantSource)
            accessartifact_grant_source.revokeByArtifact(to_delete, [sharee])

        # Create a job to remove subscriptions for artifacts the sharee can no
        # longer see.
        getUtility(IRemoveBugSubscriptionsJobSource).create(
            user, bugs=None, grantee=sharee, pillar=pillar,
            information_types=information_types)

    @available_with_permission('launchpad.Edit', 'pillar')
    def revokeAccessGrants(self, pillar, sharee, user, branches=None,
                           bugs=None):
        """See `ISharingService`."""

        if not self.write_enabled:
            raise Unauthorized("This feature is not yet enabled.")

        artifacts = []
        if branches:
            artifacts.extend(branches)
        if bugs:
            artifacts.extend(bugs)
        # Find the access artifacts associated with the bugs and branches.
        accessartifact_source = getUtility(IAccessArtifactSource)
        artifacts_to_delete = accessartifact_source.find(artifacts)
        # Revoke access to bugs/branches for the specified sharee.
        accessartifact_grant_source = getUtility(IAccessArtifactGrantSource)
        accessartifact_grant_source.revokeByArtifact(
            artifacts_to_delete, [sharee])

        # Create a job to remove subscriptions for artifacts the sharee can no
        # longer see.
        if bugs:
            getUtility(IRemoveBugSubscriptionsJobSource).create(
                user, bugs, grantee=sharee, pillar=pillar)
        # XXX 2012-06-13 wallyworld bug=1012448
        # Remove branch subscriptions when information type fully implemented.

    def ensureAccessGrants(self, sharees, user, branches=None, bugs=None,
                           ignore_permissions=False):
        """See `ISharingService`."""

        if not ignore_permissions and not self.write_enabled:
            raise Unauthorized("This feature is not yet enabled.")

        artifacts = []
        if branches:
            artifacts.extend(branches)
        if bugs:
            artifacts.extend(bugs)
        if not ignore_permissions:
            # The user needs to have launchpad.Edit permission on all supplied
            # bugs and branches or else we raise an Unauthorized exception.
            for artifact in artifacts or []:
                if not check_permission('launchpad.Edit', artifact):
                    raise Unauthorized

        # Ensure there are access artifacts associated with the bugs and
        # branches.
        artifacts = getUtility(IAccessArtifactSource).ensure(artifacts)
        aagsource = getUtility(IAccessArtifactGrantSource)
        artifacts_with_grants = [
            artifact_grant.abstract_artifact
            for artifact_grant in
            aagsource.find(product(artifacts, sharees))]
        # Create access to bugs/branches for the specified sharee for which a
        # grant does not already exist.
        missing_artifacts = set(artifacts) - set(artifacts_with_grants)
        getUtility(IAccessArtifactGrantSource).grant(
            list(product(missing_artifacts, sharees, [user])))

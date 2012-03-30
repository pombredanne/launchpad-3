# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for pillar and artifact access policies."""

__metaclass__ = type
__all__ = [
    'AccessArtifact',
    'AccessPolicy',
    'AccessPolicyArtifact',
    'AccessPolicyGrant',
    ]

from collections import defaultdict

import pytz
from storm.expr import (
    And,
    In,
    Join,
    Or,
    Select,
    SQL,
    With,
    )
from storm.properties import (
    DateTime,
    Int,
    )
from storm.references import Reference
from zope.component import getUtility
from zope.interface import implements

from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifact,
    IAccessArtifactGrant,
    IAccessArtifactGrantSource,
    IAccessPolicy,
    IAccessPolicyArtifact,
    IAccessPolicyArtifactSource,
    IAccessPolicyGrant,
    )
from lp.registry.model.person import Person
from lp.registry.model.teammembership import TeamParticipation
from lp.services.database.bulk import create
from lp.services.database.decoratedresultset import DecoratedResultSet
from lp.services.database.enumcol import DBEnum
from lp.services.database.lpstorm import IStore
from lp.services.database.stormbase import StormBase


class AccessArtifact(StormBase):
    implements(IAccessArtifact)

    __storm_table__ = 'AccessArtifact'

    id = Int(primary=True)
    bug_id = Int(name='bug')
    bug = Reference(bug_id, 'Bug.id')
    branch_id = Int(name='branch')
    branch = Reference(branch_id, 'Branch.id')

    @property
    def concrete_artifact(self):
        artifact = self.bug or self.branch
        return artifact

    @classmethod
    def _constraintForConcrete(cls, concrete_artifact):
        from lp.bugs.interfaces.bug import IBug
        from lp.code.interfaces.branch import IBranch
        if IBug.providedBy(concrete_artifact):
            col = cls.bug
        elif IBranch.providedBy(concrete_artifact):
            col = cls.branch
        else:
            raise ValueError(
                "%r is not a valid artifact" % concrete_artifact)
        return col == concrete_artifact

    @classmethod
    def find(cls, concrete_artifacts):
        """See `IAccessArtifactSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                cls._constraintForConcrete(artifact)
                for artifact in concrete_artifacts)))

    @classmethod
    def ensure(cls, concrete_artifacts):
        """See `IAccessArtifactSource`."""
        from lp.bugs.interfaces.bug import IBug
        from lp.code.interfaces.branch import IBranch

        existing = list(cls.find(concrete_artifacts))
        if len(existing) == len(concrete_artifacts):
            return existing

        # Not everything exists. Create missing ones.
        needed = (
            set(concrete_artifacts) -
            set(abstract.concrete_artifact for abstract in existing))

        insert_values = []
        for concrete in needed:
            if IBug.providedBy(concrete):
                insert_values.append((concrete, None))
            elif IBranch.providedBy(concrete):
                insert_values.append((None, concrete))
            else:
                raise ValueError("%r is not a supported artifact" % concrete)
        new = create((cls.bug, cls.branch), insert_values, get_objects=True)
        return list(existing) + new

    @classmethod
    def delete(cls, concrete_artifacts):
        """See `IAccessPolicyArtifactSource`."""
        abstracts = list(cls.find(concrete_artifacts))
        if len(abstracts) == 0:
            return
        ids = [abstract.id for abstract in abstracts]
        getUtility(IAccessArtifactGrantSource).revokeByArtifact(abstracts)
        getUtility(IAccessPolicyArtifactSource).deleteByArtifact(abstracts)
        IStore(abstract).find(cls, cls.id.is_in(ids)).remove()


class AccessPolicy(StormBase):
    implements(IAccessPolicy)

    __storm_table__ = 'AccessPolicy'

    id = Int(primary=True)
    product_id = Int(name='product')
    product = Reference(product_id, 'Product.id')
    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, 'Distribution.id')
    type = DBEnum(allow_none=True, enum=InformationType)

    @property
    def pillar(self):
        return self.product or self.distribution

    @classmethod
    def create(cls, policies):
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.product import IProduct

        insert_values = []
        for pillar, type in policies:
            if IProduct.providedBy(pillar):
                insert_values.append((pillar, None, type))
            elif IDistribution.providedBy(pillar):
                insert_values.append((None, pillar, type))
            else:
                raise ValueError("%r is not a supported pillar" % pillar)
        return create(
            (cls.product, cls.distribution, cls.type), insert_values,
            get_objects=True)

    @classmethod
    def _constraintForPillar(cls, pillar):
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.product import IProduct
        if IProduct.providedBy(pillar):
            col = cls.product
        elif IDistribution.providedBy(pillar):
            col = cls.distribution
        else:
            raise ValueError("%r is not a supported pillar" % pillar)
        return col == pillar

    @classmethod
    def find(cls, pillars_and_types):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls._constraintForPillar(pillar), cls.type == type)
                for (pillar, type) in pillars_and_types)))

    @classmethod
    def findByID(cls, ids):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(cls, cls.id.is_in(ids))

    @classmethod
    def findByPillar(cls, pillars):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(
            cls,
            Or(*(cls._constraintForPillar(pillar) for pillar in pillars)))

    @classmethod
    def findByPillarAndGrantee(cls, pillars):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(
            cls,
            Or(*(cls._constraintForPillar(pillar) for pillar in pillars)))


class AccessPolicyArtifact(StormBase):
    implements(IAccessPolicyArtifact)

    __storm_table__ = 'AccessPolicyArtifact'
    __storm_primary__ = 'abstract_artifact_id', 'policy_id'

    abstract_artifact_id = Int(name='artifact')
    abstract_artifact = Reference(
        abstract_artifact_id, 'AccessArtifact.id')
    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')

    @classmethod
    def create(cls, links):
        """See `IAccessPolicyArtifactSource`."""
        return create(
            (cls.abstract_artifact, cls.policy), links,
            get_objects=True)

    @classmethod
    def find(cls, links):
        """See `IAccessArtifactGrantSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls.abstract_artifact == artifact, cls.policy == policy)
                for (artifact, policy) in links)))

    @classmethod
    def findByArtifact(cls, artifacts):
        """See `IAccessPolicyArtifactSource`."""
        ids = [artifact.id for artifact in artifacts]
        return IStore(cls).find(cls, cls.abstract_artifact_id.is_in(ids))

    @classmethod
    def findByPolicy(cls, policies):
        """See `IAccessPolicyArtifactSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(cls, cls.policy_id.is_in(ids))

    @classmethod
    def deleteByArtifact(cls, artifacts):
        """See `IAccessPolicyArtifactSource`."""
        cls.findByArtifact(artifacts).remove()


class AccessArtifactGrant(StormBase):
    implements(IAccessArtifactGrant)

    __storm_table__ = 'AccessArtifactGrant'
    __storm_primary__ = 'abstract_artifact_id', 'grantee_id'

    abstract_artifact_id = Int(name='artifact')
    abstract_artifact = Reference(
        abstract_artifact_id, 'AccessArtifact.id')
    grantee_id = Int(name='grantee')
    grantee = Reference(grantee_id, 'Person.id')
    grantor_id = Int(name='grantor')
    grantor = Reference(grantor_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC)

    @property
    def concrete_artifact(self):
        if self.abstract_artifact is not None:
            return self.abstract_artifact.concrete_artifact

    @classmethod
    def grant(cls, grants):
        """See `IAccessArtifactGrantSource`."""
        return create(
            (cls.abstract_artifact, cls.grantee, cls.grantor), grants,
            get_objects=True)

    @classmethod
    def find(cls, grants):
        """See `IAccessArtifactGrantSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls.abstract_artifact == artifact, cls.grantee == grantee)
                for (artifact, grantee) in grants)))

    @classmethod
    def findByArtifact(cls, artifacts):
        """See `IAccessArtifactGrantSource`."""
        ids = [artifact.id for artifact in artifacts]
        return IStore(cls).find(cls, cls.abstract_artifact_id.is_in(ids))

    @classmethod
    def revokeByArtifact(cls, artifacts):
        """See `IAccessPolicyGrantSource`."""
        cls.findByArtifact(artifacts).remove()


class AccessPolicyGrant(StormBase):
    implements(IAccessPolicyGrant)

    __storm_table__ = 'AccessPolicyGrant'
    __storm_primary__ = 'policy_id', 'grantee_id'

    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')
    grantee_id = Int(name='grantee')
    grantee = Reference(grantee_id, 'Person.id')
    grantor_id = Int(name='grantor')
    grantor = Reference(grantor_id, 'Person.id')
    date_created = DateTime(tzinfo=pytz.UTC)

    @classmethod
    def grant(cls, grants):
        """See `IAccessPolicyGrantSource`."""
        return create(
            (cls.policy, cls.grantee, cls.grantor), grants, get_objects=True)

    @classmethod
    def find(cls, grants):
        """See `IAccessPolicyGrantSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls.policy == policy, cls.grantee == grantee)
                for (policy, grantee) in grants)))

    @classmethod
    def findByPolicy(cls, policies):
        """See `IAccessPolicyGrantSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(cls, cls.policy_id.is_in(ids))

    @classmethod
    def revoke(cls, grants):
        """See `IAccessPolicyGrantSource`."""
        cls.find(grants).remove()


class AccessPolicyGrantFlat(StormBase):
    __storm_table__ = 'AccessPolicyGrantFlat'

    id = Int(primary=True)
    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')
    abstract_artifact_id = Int(name='artifact')
    abstract_artifact = Reference(
        abstract_artifact_id, 'AccessArtifact.id')
    grantee_id = Int(name='grantee')
    grantee = Reference(grantee_id, 'Person.id')

    @classmethod
    def findGranteesByPolicy(cls, policies):
        """See `IAccessPolicyGrantFlatSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(
            Person, Person.id == cls.grantee_id, cls.policy_id.is_in(ids))

    @classmethod
    def _populatePermissionsCache(cls, permissions_cache, grantee_ids,
                                  policies_by_id, persons_by_id):
        sharing_permission_term = SQL(
            "CASE MIN(COALESCE(artifact, 0)) WHEN 0 THEN ? ELSE ? END",
            (SharingPermission.ALL.name, SharingPermission.SOME.name))
        constraints = [
            cls.grantee_id.is_in(grantee_ids),
            cls.policy_id.is_in(policies_by_id.keys())]
        result_set = IStore(cls).find(
            (cls.grantee_id, cls.policy_id, sharing_permission_term),
            *constraints).group_by(cls.grantee_id, cls.policy_id)
        for (person_id, policy_id, permission) in result_set:
            person = persons_by_id[person_id]
            policy = policies_by_id[policy_id]
            permissions_cache[person][policy] = (
                SharingPermission.items[str(permission)])

    @classmethod
    def _populateGranteePermissions(cls, policies_by_id, result_set):
        # A cache for the sharing permissions, keyed on grantee
        permissions_cache = defaultdict(dict)

        def set_permission(grantee):
            # Lookup the permissions from the previously loaded cache.
            return grantee[0], permissions_cache[grantee[0]]

        def load_permissions(grantees):
            # We now have the grantees and policies we want in the result so
            # load any corresponding permissions and cache them.
            if permissions_cache:
                return
            grantee_ids = set()
            grantee_by_id = dict()
            for grantee in grantees:
                grantee_ids.add(grantee[0].id)
                grantee_by_id[grantee[0].id] = grantee[0]
            cls._populatePermissionsCache(
                permissions_cache, grantee_ids, policies_by_id, grantee_by_id)
        return DecoratedResultSet(
            result_set,
            result_decorator=set_permission, pre_iter_hook=load_permissions)

    @classmethod
    def findGranteePermissionsByPolicy(cls, policies, grantees=None):
        """See `IAccessPolicyGrantFlatSource`."""
        policies_by_id = dict((policy.id, policy) for policy in policies)
        constraints = [cls.policy_id.is_in(policies_by_id.keys())]
        if grantees:
            grantee_ids = [grantee.id for grantee in grantees]
            constraints.append(cls.grantee_id.is_in(grantee_ids))
        # Since the sort time dominates this query, we do the DISTINCT
        # in a subquery to ensure it's performed first.
        result_set = IStore(cls).find(
            (Person,),
            In(
                Person.id,
                Select(
                    (cls.grantee_id,), where=And(*constraints),
                    distinct=True)))
        return cls._populateGranteePermissions(policies_by_id, result_set)

    @classmethod
    def _indirectGranteeSnippets(cls, store, policies_by_id):
        grantee_with_expr = With("grantees", store.find(
            cls.grantee_id, cls.policy_id.is_in(policies_by_id.keys())
        ).config(distinct=True)._get_select())
        grantee_id_select = Select(
            (TeamParticipation.personID,),
            tables=(TeamParticipation, Join("grantees",
                SQL("grantees.grantee = TeamParticipation.team"))),
            distinct=True)
        return grantee_with_expr, grantee_id_select

    @classmethod
    def _populateIndirectGranteePermissions(cls,
                                            policies_by_id, result_set):
        # A cache for the sharing permissions, keyed on grantee.
        permissions_cache = defaultdict(dict)
        # A cache of teams belonged to, keyed by grantee.
        via_teams_cache = defaultdict(list)
        grantees_by_id = dict()

        def set_permission(grantee):
            # Lookup the permissions from the previously loaded cache.
            via_team_ids = via_teams_cache[grantee[0].id]
            via_teams = [grantees_by_id[team_id] for team_id in via_team_ids]
            permissions = permissions_cache[grantee[0]]
            # For access via teams, we need to use the team permissions. If a
            # person has access via more than one team, we use the most
            # powerful permission of all that are there.
            for team in via_teams:
                team_permissions = permissions_cache[team]
                for info_type, permission in team_permissions.items():
                    permission_to_use = permissions.get(info_type, permission)
                    if permission == SharingPermission.ALL:
                        permission_to_use = permission
                    permissions[info_type] = permission_to_use
            return grantee[0], permissions, via_teams or None

        def load_teams_and_permissions(grantees):
            # We now have the grantees we want in the result so load any
            # associated team memberships and permissions and cache them.
            if permissions_cache:
                return
            store = IStore(cls)
            for grantee in grantees:
                grantees_by_id[grantee[0].id] = grantee[0]
            # Find any teams associated with the grantees. If grantees is a
            # sliced list (for batching), it may contain indirect grantees but
            # not the team they belong to so that needs to be fixed below.
            grantee_with_expr, grantee_id_select = (
                cls._indirectGranteeSnippets(store, policies_by_id))
            result_set = store.with_(grantee_with_expr).find(
                (TeamParticipation.teamID, TeamParticipation.personID),
                Or(
                    TeamParticipation.teamID.is_in(grantees_by_id.keys()),
                    TeamParticipation.personID.is_in(grantees_by_id.keys())),
                TeamParticipation.teamID.is_in(grantee_id_select)
            )
            team_ids = set()
            for team_id, team_member_id in result_set:
                if (team_id != team_member_id
                    and team_member_id in grantees_by_id.keys()):
                        via_teams_cache[team_member_id].append(team_id)
                team_ids.add(team_id)
            # Load and cache the required teams.
            persons = store.find(Person, Person.id.is_in(team_ids))
            for person in persons:
                grantees_by_id[person.id] = person
            cls._populatePermissionsCache(
                permissions_cache, grantees_by_id.keys(), policies_by_id,
                grantees_by_id)

        return DecoratedResultSet(
            result_set,
            result_decorator=set_permission,
            pre_iter_hook=load_teams_and_permissions)

    @classmethod
    def findIndirectGranteePermissionsByPolicy(cls, policies):
        """See `IAccessPolicyGrantFlatSource`."""
        policies_by_id = dict((policy.id, policy) for policy in policies)
        store = IStore(cls)
        grantee_with_expr, grantee_id_select = cls._indirectGranteeSnippets(
            store, policies_by_id)
        result_set = store.with_(grantee_with_expr).find(
            (Person,), In(Person.id, grantee_id_select))
        return cls._populateIndirectGranteePermissions(
            policies_by_id, result_set)

    @classmethod
    def findArtifactsByGrantee(cls, grantee, policies):
        """See `IAccessPolicyGrantFlatSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(
            AccessArtifact,
            AccessArtifact.id == cls.abstract_artifact_id,
            cls.grantee_id == grantee.id,
            cls.policy_id.is_in(ids))

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
    Or,
    Select,
    SQL,
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
        if len(pillars_and_types) == 0:
            return []
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
    def findByArtifact(cls, artifacts, grantees=None):
        """See `IAccessArtifactGrantSource`."""
        artifact_ids = [artifact.id for artifact in artifacts]
        constraints = [cls.abstract_artifact_id.is_in(artifact_ids)]
        if grantees:
            grantee_ids = [grantee.id for grantee in grantees]
            constraints.append(cls.grantee_id.is_in(grantee_ids))
        return IStore(cls).find(cls, *constraints)

    @classmethod
    def revokeByArtifact(cls, artifacts, grantees=None):
        """See `IAccessPolicyGrantSource`."""
        cls.findByArtifact(artifacts, grantees).remove()


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
    def findGranteePermissionsByPolicy(cls, policies, grantees=None):
        """See `IAccessPolicyGrantFlatSource`."""
        policies_by_id = dict((policy.id, policy) for policy in policies)

        # A cache for the sharing permissions, keyed on grantee
        permissions_cache = defaultdict(dict)
        # Information types for which there are shared artifacts.
        shared_artifact_info_types = defaultdict(list)

        def set_permission(person):
            # Lookup the permissions from the previously loaded cache.
            return (
                person[0],
                permissions_cache[person[0]],
                shared_artifact_info_types[person[0]])

        def load_permissions(people):
            # We now have the grantees and policies we want in the result so
            # load any corresponding permissions and cache them.
            people_by_id = dict(
                (person[0].id, person[0]) for person in people)
            all_permission_term = SQL("bool_or(artifact IS NULL) as all")
            some_permission_term = SQL(
                "bool_or(artifact IS NOT NULL) as some")
            constraints = [
                cls.grantee_id.is_in(people_by_id.keys()),
                cls.policy_id.is_in(policies_by_id.keys())]
            result_set = IStore(cls).find(
                (cls.grantee_id, cls.policy_id, all_permission_term,
                 some_permission_term),
                *constraints).group_by(cls.grantee_id, cls.policy_id)
            for (person_id, policy_id, has_all, has_some) in result_set:
                person = people_by_id[person_id]
                policy = policies_by_id[policy_id]
                permissions_cache[person][policy] = (
                    SharingPermission.ALL if has_all
                    else SharingPermission.SOME)
                if has_some:
                    shared_artifact_info_types[person].append(policy.type)

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
        return DecoratedResultSet(
            result_set,
            result_decorator=set_permission, pre_iter_hook=load_permissions)

    @classmethod
    def findArtifactsByGrantee(cls, grantee, policies):
        """See `IAccessPolicyGrantFlatSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(
            AccessArtifact,
            AccessArtifact.id == cls.abstract_artifact_id,
            cls.grantee_id == grantee.id,
            cls.policy_id.is_in(ids))

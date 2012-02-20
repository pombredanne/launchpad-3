# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for pillar and artifact access policies."""

__metaclass__ = type
__all__ = [
    'AccessArtifact',
    'AccessPolicy',
    'AccessPolicyGrant',
    ]

from storm.databases.postgres import Returning
from storm.expr import (
    And,
    Or,
    )
from storm.properties import (
    DateTime,
    Int,
    )
from storm.references import Reference
from zope.interface import implements

from lp.registry.interfaces.accesspolicy import (
    AccessPolicyType,
    IAccessArtifact,
    IAccessArtifactGrant,
    IAccessPolicy,
    IAccessPolicyGrant,
    )
from lp.registry.interfaces.person import IPerson
from lp.services.database.bulk import load
from lp.services.database.enumcol import DBEnum
from lp.services.database.lpstorm import IStore
from lp.services.database.stormbase import StormBase
from lp.services.database.stormexpr import BulkInsert


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
        assert artifact is not None
        return artifact

    @classmethod
    def _getConcreteAttribute(cls, concrete_artifact):
        from lp.bugs.interfaces.bug import IBug
        from lp.code.interfaces.branch import IBranch
        if IBug.providedBy(concrete_artifact):
            return cls.bug
        elif IBranch.providedBy(concrete_artifact):
            return cls.branch
        else:
            raise ValueError(
                "%r is not a valid artifact" % concrete_artifact)

    @classmethod
    def find(cls, concrete_artifacts):
        """See `IAccessArtifactSource`."""
        constraints = (
            cls._getConcreteAttribute(artifact) == artifact
            for artifact in concrete_artifacts)
        return IStore(cls).find(cls, Or(*constraints))

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
                insert_values.append((concrete.id, None))
            elif IBranch.providedBy(concrete):
                insert_values.append((None, concrete.id))
            else:
                raise ValueError("%r is not a supported artifact" % concrete)
        result = IStore(cls).execute(
            Returning(BulkInsert(
                (cls.bug_id, cls.branch_id),
                expr=insert_values, primary_columns=cls.id)))
        created = load(cls, (cols[0] for cols in result))

        return list(existing) + created

    @classmethod
    def delete(cls, concrete_artifacts):
        """See `IAccessPolicyArtifactSource`."""
        ids = [abstract.id for abstract in cls.find(concrete_artifacts)]
        if len(ids) == 0:
            return
        IStore(abstract).find(
            AccessArtifactGrant,
            AccessArtifactGrant.abstract_artifact_id.is_in(ids)).remove()
        IStore(abstract).find(cls, cls.id.is_in(ids)).remove()


class AccessPolicy(StormBase):
    implements(IAccessPolicy)

    __storm_table__ = 'AccessPolicy'

    id = Int(primary=True)
    product_id = Int(name='product')
    product = Reference(product_id, 'Product.id')
    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, 'Distribution.id')
    type = DBEnum(allow_none=True, enum=AccessPolicyType)

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
                insert_values.append((pillar.id, None, type.value))
            elif IDistribution.providedBy(pillar):
                insert_values.append((None, pillar.id, type.value))
            else:
                raise ValueError("%r is not a supported pillar" % pillar)
        result = IStore(cls).execute(
            Returning(BulkInsert(
                (cls.product_id, cls.distribution_id, cls.type),
                expr=insert_values, primary_columns=cls.id)))
        return load(AccessPolicy, (cols[0] for cols in result))

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
    def findByIDs(cls, ids):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(cls, cls.id.is_in(ids))

    @classmethod
    def findByPillars(cls, pillars):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(
            cls,
            Or(*(cls._constraintForPillar(pillar) for pillar in pillars)))

    @classmethod
    def findByPillarsAndTypes(cls, pillars_and_types):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls._constraintForPillar(pillar), cls.type == type)
                for (pillar, type) in pillars_and_types)))


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
    date_created = DateTime()

    @property
    def concrete_artifact(self):
        if self.abstract_artifact is not None:
            return self.abstract_artifact.concrete_artifact

    @classmethod
    def grant(cls, artifact, grantee, grantor):
        """See `IAccessArtifactGrantSource`."""
        grant = cls()
        grant.abstract_artifact = artifact
        grant.grantee = grantee
        grant.grantor = grantor
        IStore(cls).add(grant)
        return grant

    @classmethod
    def get(cls, artifact, grantee):
        """See `IAccessArtifactGrantSource`."""
        assert IAccessArtifact.providedBy(artifact)
        assert IPerson.providedBy(grantee)
        return IStore(cls).get(cls, (artifact.id, grantee.id))

    @classmethod
    def findByArtifact(cls, artifact):
        """See `IAccessArtifactGrantSource`."""
        return IStore(cls).find(cls, abstract_artifact=artifact)


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
    date_created = DateTime()

    @classmethod
    def grant(cls, policy, grantee, grantor):
        """See `IAccessPolicyGrantSource`."""
        grant = cls()
        grant.policy = policy
        grant.grantee = grantee
        grant.grantor = grantor
        IStore(cls).add(grant)
        return grant

    @classmethod
    def get(cls, policy, grantee):
        """See `IAccessPolicyGrantSource`."""
        assert IAccessPolicy.providedBy(policy)
        assert IPerson.providedBy(grantee)
        return IStore(cls).get(cls, (policy.id, grantee.id))

    @classmethod
    def findByPolicy(cls, policy):
        """See `IAccessPolicyGrantSource`."""
        return IStore(cls).find(cls, policy=policy)

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
    Insert,
    Or,
    )
from storm.properties import (
    DateTime,
    Int,
    )
from storm.references import Reference
from zope.component import getUtility
from zope.interface import implements

from lp.registry.interfaces.accesspolicy import (
    AccessPolicyType,
    IAccessArtifact,
    IAccessArtifactGrant,
    IAccessArtifactGrantSource,
    IAccessPolicy,
    IAccessPolicyGrant,
    )
from lp.services.database.bulk import load
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
        assert artifact is not None
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
                insert_values.append((concrete.id, None))
            elif IBranch.providedBy(concrete):
                insert_values.append((None, concrete.id))
            else:
                raise ValueError("%r is not a supported artifact" % concrete)
        result = IStore(cls).execute(
            Returning(Insert(
                (cls.bug_id, cls.branch_id),
                expr=insert_values, primary_columns=cls.id)))
        created = load(cls, (cols[0] for cols in result))

        return list(existing) + created

    @classmethod
    def delete(cls, concrete_artifacts):
        """See `IAccessPolicyArtifactSource`."""
        abstracts = list(cls.find(concrete_artifacts))
        ids = [abstract.id for abstract in abstracts]
        if len(ids) == 0:
            return
        getUtility(IAccessArtifactGrantSource).revokeByArtifacts(abstracts)
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
            Returning(Insert(
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
    def grant(cls, grants):
        """See `IAccessArtifactGrantSource`."""
        insert_values = [
            (artifact.id, grantee.id, grantor.id)
            for (artifact, grantee, grantor) in grants]
        result = IStore(cls).execute(
            Returning(Insert(
                (cls.abstract_artifact_id, cls.grantee_id, cls.grantor_id),
                expr=insert_values,
                primary_columns=(cls.abstract_artifact_id, cls.grantee_id))))
        return load(cls, result)

    @classmethod
    def find(cls, grants):
        """See `IAccessArtifactGrantSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls.abstract_artifact == artifact, cls.grantee == grantee)
                for (artifact, grantee) in grants)))

    @classmethod
    def findByArtifacts(cls, artifacts):
        """See `IAccessArtifactGrantSource`."""
        ids = [artifact.id for artifact in artifacts]
        return IStore(cls).find(cls, cls.abstract_artifact_id.is_in(ids))

    @classmethod
    def revokeByArtifacts(cls, artifacts):
        """See `IAccessPolicyGrantSource`."""
        cls.findByArtifacts(artifacts).remove()


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
    def grant(cls, grants):
        """See `IAccessPolicyGrantSource`."""
        insert_values = [
            (policy.id, grantee.id, grantor.id)
            for (policy, grantee, grantor) in grants]
        result = IStore(cls).execute(
            Returning(Insert(
                (cls.policy_id, cls.grantee_id, cls.grantor_id),
                expr=insert_values,
                primary_columns=(cls.policy_id, cls.grantee_id))))
        return load(cls, result)

    @classmethod
    def find(cls, grants):
        """See `IAccessPolicyGrantSource`."""
        return IStore(cls).find(
            cls,
            Or(*(
                And(cls.policy == policy, cls.grantee == grantee)
                for (policy, grantee) in grants)))

    @classmethod
    def findByPolicies(cls, policies):
        """See `IAccessPolicyGrantSource`."""
        ids = [policy.id for policy in policies]
        return IStore(cls).find(cls, cls.policy_id.is_in(ids))

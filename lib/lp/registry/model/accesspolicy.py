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

import pytz
from storm.expr import (
    And,
    Or,
    )
from storm.properties import (
    DateTime,
    Int,
    )
from storm.references import Reference
from zope.component import getUtility
from zope.interface import implements

from lp.registry.enums import AccessPolicyType
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifact,
    IAccessArtifactGrant,
    IAccessArtifactGrantSource,
    IAccessPolicy,
    IAccessPolicyArtifact,
    IAccessPolicyGrant,
    )
from lp.registry.model.person import Person
from lp.services.database.bulk import create
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

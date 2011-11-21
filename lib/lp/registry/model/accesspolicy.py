# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for pillar and artifact access policies."""

__metaclass__ = type
__all__ = [
    'AccessPolicy',
    'AccessPolicyArtifact',
    'AccessPolicyGrant',
    ]

from storm.properties import (
    Int,
    DateTime,
    )
from storm.references import Reference
from zope.interface import implements

from canonical.database.enumcol import DBEnum
from canonical.launchpad.interfaces.lpstorm import IStore
from lp.registry.interfaces.accesspolicy import (
    AccessPolicyType,
    IAccessPolicy,
    IAccessPolicyArtifact,
    IAccessPolicyGrant,
    )
from lp.services.database.stormbase import StormBase


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
    def create(cls, pillar, type):
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.product import IProduct
        obj = cls()
        if IProduct.providedBy(pillar):
            obj.product = pillar
        elif IDistribution.providedBy(pillar):
            obj.distribution = pillar
        else:
            raise AssertionError("%r is not a supported pillar" % pillar)
        obj.type = type
        IStore(cls).add(obj)
        return obj

    @classmethod
    def _constraintForPillar(cls, pillar):
        from lp.registry.interfaces.distribution import IDistribution
        from lp.registry.interfaces.product import IProduct
        if IProduct.providedBy(pillar):
            col = cls.product
        elif IDistribution.providedBy(pillar):
            col = cls.distribution
        else:
            raise AssertionError("%r is not a supported pillar" % pillar)
        return col == pillar

    @classmethod
    def getByID(cls, id):
        """See `IAccessPolicySource`."""
        return IStore(cls).get(cls, id)

    @classmethod
    def findByPillar(cls, pillar):
        """See `IAccessPolicySource`."""
        return IStore(cls).find(cls, cls._constraintForPillar(pillar))

    @classmethod
    def getByPillarAndType(cls, pillar, type):
        """See `IAccessPolicySource`."""
        return cls.findByPillar(pillar).find(type=type).one()


class AccessPolicyArtifact(StormBase):
    implements(IAccessPolicyArtifact)

    __storm_table__ = 'AccessPolicyArtifact'

    id = Int(primary=True)
    bug_id = Int(name='bug')
    bug = Reference(bug_id, 'Bug.id')
    branch_id = Int(name='branch')
    branch = Reference(branch_id, 'Branch.id')
    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')

    @property
    def concrete_artifact(self):
        artifact = self.bug or self.branch
        assert artifact is not None
        return artifact

    @staticmethod
    def _getConcreteAttribute(concrete_artifact):
        from lp.bugs.interfaces.bug import IBug
        from lp.code.interfaces.branch import IBranch
        if IBug.providedBy(concrete_artifact):
            return 'bug'
        elif IBranch.providedBy(concrete_artifact):
            return 'branch'
        else:
            raise AssertionError(
                "%r is not a valid artifact" % concrete_artifact)

    @classmethod
    def get(cls, concrete_artifact):
        """See `IAccessPolicyArtifactSource`."""
        constraints = {
            cls._getConcreteAttribute(concrete_artifact): concrete_artifact}
        return IStore(cls).find(cls, **constraints).one()

    @classmethod
    def ensure(cls, concrete_artifact):
        """See `IAccessPolicyArtifactSource`."""
        existing = cls.get(concrete_artifact)
        if existing is not None:
            return existing
        # No existing object. Create a new one.
        obj = cls()
        setattr(
            obj, cls._getConcreteAttribute(concrete_artifact),
            concrete_artifact)
        IStore(cls).add(obj)
        return obj

    @classmethod
    def delete(cls, concrete_artifact):
        """See `IAccessPolicyArtifactSource`."""
        abstract = cls.ensure(concrete_artifact)
        IStore(abstract).find(
            AccessPolicyGrant, abstract_artifact=abstract).remove()
        IStore(abstract).find(AccessPolicyArtifact, id=abstract.id).remove()


class AccessPolicyGrant(StormBase):
    implements(IAccessPolicyGrant)

    __storm_table__ = 'AccessPolicyGrant'

    id = Int(primary=True)
    grantee_id = Int(name='grantee')
    grantee = Reference(grantee_id, 'Person.id')
    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')
    abstract_artifact_id = Int(name='artifact')
    abstract_artifact = Reference(
        abstract_artifact_id, 'AccessPolicyArtifact.id')
    grantor_id = Int(name='grantor')
    grantor = Reference(grantor_id, 'Person.id')
    date_created = DateTime()

    @property
    def concrete_artifact(self):
        if self.abstract_artifact is not None:
            return self.abstract_artifact.concrete_artifact

    @classmethod
    def grant(cls, grantee, grantor, object):
        """See `IAccessPolicyGrantSource`."""
        grant = cls()
        grant.grantee = grantee
        grant.grantor = grantor
        if IAccessPolicy.providedBy(object):
            grant.policy = object
        elif IAccessPolicyArtifact.providedBy(object):
            grant.abstract_artifact = object
        else:
            raise AssertionError("Unsupported object: %r" % object)
        IStore(cls).add(grant)
        return grant

    @classmethod
    def getByID(cls, id):
        """See `IAccessPolicyGrantSource`."""
        return IStore(cls).get(cls, id)

    @classmethod
    def findByPolicy(cls, policy):
        """See `IAccessPolicyGrantSource`."""
        return IStore(cls).find(cls, policy=policy)

# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Model classes for pillar and artifact access policies."""

__metaclass__ = type
__all__ = [
    'AccessPolicy',
    'AccessPolicyArtifact',
    'AccessPolicyPermission',
    ]

from storm.properties import (
    Int,
    Unicode,
    )
from storm.references import (
    Reference,
    ReferenceSet,
    )
from lp.services.database.stormbase import StormBase


class AccessPolicy(StormBase):
    __storm_table__ = 'AccessPolicy'

    id = Int(primary=True)
    product_id = Int(name='product')
    product = Reference(product_id, 'Product.id')
    distribution_id = Int(name='distribution')
    distribution = Reference(distribution_id, 'Distribution.id')
    display_name = Unicode()

    permissions = ReferenceSet(id, "AccessPolicyPermission.policy_id")


class AccessPolicyArtifact(StormBase):
    __storm_table__ = 'AccessPolicyArtifact'

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


class AccessPolicyPermission(StormBase):
    __storm_table__ = 'AccessPolicyPermission'

    id = Int(primary=True)
    policy_id = Int(name='policy')
    policy = Reference(policy_id, 'AccessPolicy.id')
    person_id = Int(name='person')
    person = Reference(person_id, 'Person.id')
    abstract_artifact_id = Int(name='artifact')
    abstract_artifact = Reference(
        abstract_artifact_id, 'AccessPolicyArtifact.id')

    @property
    def concrete_artifact(self):
        if self.abstract_artifact is not None:
            return self.abstract_artifact.concrete_artifact

# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.exceptions import LostObjectError
from testtools.matchers import AllMatch
from zope.component import getUtility

from lp.registry.enums import AccessPolicyType
from lp.registry.interfaces.accesspolicy import (
    IAccessArtifact,
    IAccessArtifactGrant,
    IAccessArtifactGrantSource,
    IAccessArtifactSource,
    IAccessPolicy,
    IAccessPolicyArtifact,
    IAccessPolicyArtifactSource,
    IAccessPolicyGrant,
    IAccessPolicyGrantFlatSource,
    IAccessPolicyGrantSource,
    IAccessPolicySource,
    )
from lp.services.database.lpstorm import IStore
from lp.testing import TestCaseWithFactory
from lp.testing.layers import DatabaseFunctionalLayer
from lp.testing.matchers import Provides


class TestAccessPolicy(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertThat(
            self.factory.makeAccessPolicy(), Provides(IAccessPolicy))

    def test_pillar(self):
        product = self.factory.makeProduct()
        policy = self.factory.makeAccessPolicy(pillar=product)
        self.assertEqual(product, policy.pillar)


class TestAccessPolicySource(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_create(self):
        wanted = [
            (self.factory.makeProduct(), AccessPolicyType.PROPRIETARY),
            (self.factory.makeDistribution(), AccessPolicyType.USERDATA),
            ]
        policies = getUtility(IAccessPolicySource).create(wanted)
        self.assertThat(
            policies,
            AllMatch(Provides(IAccessPolicy)))
        self.assertContentEqual(
            wanted,
            [(policy.pillar, policy.type) for policy in policies])

    def test_find(self):
        # find() finds the right policies.
        product = self.factory.makeProduct()
        distribution = self.factory.makeDistribution()
        other_product = self.factory.makeProduct()

        wanted = [
            (product, AccessPolicyType.PROPRIETARY),
            (product, AccessPolicyType.USERDATA),
            (distribution, AccessPolicyType.PROPRIETARY),
            (distribution, AccessPolicyType.USERDATA),
            (other_product, AccessPolicyType.PROPRIETARY),
            ]
        getUtility(IAccessPolicySource).create(wanted)

        query = [
            (product, AccessPolicyType.PROPRIETARY),
            (product, AccessPolicyType.USERDATA),
            (distribution, AccessPolicyType.USERDATA),
            ]
        self.assertContentEqual(
            query,
            [(policy.pillar, policy.type) for policy in
             getUtility(IAccessPolicySource).find(query)])

        query = [(distribution, AccessPolicyType.PROPRIETARY)]
        self.assertContentEqual(
            query,
            [(policy.pillar, policy.type) for policy in
             getUtility(IAccessPolicySource).find(query)])

    def test_findByID(self):
        # findByID finds the right policies.
        policies = [self.factory.makeAccessPolicy() for i in range(2)]
        self.factory.makeAccessPolicy()
        self.assertContentEqual(
            policies,
            getUtility(IAccessPolicySource).findByID(
                [policy.id for policy in policies]))

    def test_findByPillar(self):
        # findByPillar finds only the relevant policies.
        product = self.factory.makeProduct()
        distribution = self.factory.makeProduct()
        other_product = self.factory.makeProduct()
        wanted = [
            (pillar, type)
            for type in AccessPolicyType.items
            for pillar in (product, distribution, other_product)]
        policies = getUtility(IAccessPolicySource).create(wanted)
        self.assertContentEqual(
            policies,
            getUtility(IAccessPolicySource).findByPillar(
                [product, distribution, other_product]))
        self.assertContentEqual(
            [policy for policy in policies if policy.pillar == product],
            getUtility(IAccessPolicySource).findByPillar([product]))


class TestAccessArtifact(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertThat(
            self.factory.makeAccessArtifact(),
            Provides(IAccessArtifact))


class TestAccessArtifactSourceOnce(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_ensure_other_fails(self):
        # ensure() rejects unsupported objects.
        self.assertRaises(
            ValueError,
            getUtility(IAccessArtifactSource).ensure,
            [self.factory.makeProduct()])


class BaseAccessArtifactTests:
    layer = DatabaseFunctionalLayer

    def getConcreteArtifact(self):
        raise NotImplementedError()

    def test_ensure(self):
        # ensure() creates abstract artifacts which map to the
        # concrete ones.
        concretes = [self.getConcreteArtifact() for i in range(2)]
        abstracts = getUtility(IAccessArtifactSource).ensure(concretes)
        self.assertContentEqual(
            concretes,
            [abstract.concrete_artifact for abstract in abstracts])

    def test_find(self):
        # find() finds abstract artifacts which map to the concrete ones.
        concretes = [self.getConcreteArtifact() for i in range(2)]
        abstracts = getUtility(IAccessArtifactSource).ensure(concretes)
        self.assertContentEqual(
            abstracts, getUtility(IAccessArtifactSource).find(concretes))

    def test_ensure_twice(self):
        # ensure() will reuse an existing matching abstract artifact if
        # it exists.
        concrete1 = self.getConcreteArtifact()
        concrete2 = self.getConcreteArtifact()
        [abstract1] = getUtility(IAccessArtifactSource).ensure([concrete1])

        abstracts = getUtility(IAccessArtifactSource).ensure(
            [concrete1, concrete2])
        self.assertIn(abstract1, abstracts)
        self.assertContentEqual(
            [concrete1, concrete2],
            [abstract.concrete_artifact for abstract in abstracts])

    def test_delete(self):
        # delete() removes the abstract artifacts and any associated
        # grants.
        concretes = [self.getConcreteArtifact() for i in range(2)]
        abstracts = getUtility(IAccessArtifactSource).ensure(concretes)
        grant = self.factory.makeAccessArtifactGrant(artifact=abstracts[0])

        # Make some other grants to ensure they're unaffected.
        other_grants = [
            self.factory.makeAccessArtifactGrant(
                artifact=self.factory.makeAccessArtifact()),
            self.factory.makeAccessPolicyGrant(
                policy=self.factory.makeAccessPolicy()),
            ]

        getUtility(IAccessArtifactSource).delete(concretes)
        IStore(grant).invalidate()
        self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertRaises(
            LostObjectError, getattr, abstracts[0], 'concrete_artifact')

        for other_grant in other_grants:
            self.assertIsNot(None, other_grant.grantor)

    def test_delete_noop(self):
        # delete() works even if there's no abstract artifact.
        concrete = self.getConcreteArtifact()
        getUtility(IAccessArtifactSource).delete([concrete])


class TestAccessArtifactBranch(BaseAccessArtifactTests,
                               TestCaseWithFactory):

    def getConcreteArtifact(self):
        return self.factory.makeBranch()


class TestAccessArtifactBug(BaseAccessArtifactTests,
                            TestCaseWithFactory):

    def getConcreteArtifact(self):
        return self.factory.makeBug()


class TestAccessArtifactGrant(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertThat(
            self.factory.makeAccessArtifactGrant(),
            Provides(IAccessArtifactGrant))

    def test_concrete_artifact(self):
        bug = self.factory.makeBug()
        abstract = self.factory.makeAccessArtifact(bug)
        grant = self.factory.makeAccessArtifactGrant(artifact=abstract)
        self.assertEqual(bug, grant.concrete_artifact)


class TestAccessArtifactGrantSource(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_grant(self):
        wanted = [
            (self.factory.makeAccessArtifact(), self.factory.makePerson(),
             self.factory.makePerson()),
            (self.factory.makeAccessArtifact(), self.factory.makePerson(),
             self.factory.makePerson()),
            ]
        grants = getUtility(IAccessArtifactGrantSource).grant(wanted)
        self.assertContentEqual(
            wanted,
            [(g.abstract_artifact, g.grantee, g.grantor) for g in grants])

    def test_find(self):
        # find() finds the right grants.
        grants = [self.factory.makeAccessArtifactGrant() for i in range(2)]
        self.assertContentEqual(
            grants,
            getUtility(IAccessArtifactGrantSource).find(
                [(g.abstract_artifact, g.grantee) for g in grants]))

    def test_findByArtifact(self):
        # findByArtifact() finds only the relevant grants.
        artifact = self.factory.makeAccessArtifact()
        grants = [
            self.factory.makeAccessArtifactGrant(artifact=artifact)
            for i in range(3)]
        self.factory.makeAccessArtifactGrant()
        self.assertContentEqual(
            grants,
            getUtility(IAccessArtifactGrantSource).findByArtifact([artifact]))

    def test_revokeByArtifact(self):
        # revokeByArtifact() removes the relevant grants.
        artifact = self.factory.makeAccessArtifact()
        grant = self.factory.makeAccessArtifactGrant(artifact=artifact)
        other_grant = self.factory.makeAccessArtifactGrant()
        getUtility(IAccessArtifactGrantSource).revokeByArtifact([artifact])
        IStore(grant).invalidate()
        self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertIsNot(None, other_grant.grantor)


class TestAccessPolicyArtifact(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertThat(
            self.factory.makeAccessPolicyArtifact(),
            Provides(IAccessPolicyArtifact))


class TestAccessPolicyArtifactSource(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_create(self):
        wanted = [
            (self.factory.makeAccessArtifact(),
             self.factory.makeAccessPolicy()),
            (self.factory.makeAccessArtifact(),
             self.factory.makeAccessPolicy()),
            ]
        links = getUtility(IAccessPolicyArtifactSource).create(wanted)
        self.assertContentEqual(
            wanted,
            [(link.abstract_artifact, link.policy) for link in links])

    def test_find(self):
        links = [self.factory.makeAccessPolicyArtifact() for i in range(3)]
        self.assertContentEqual(
            links,
            getUtility(IAccessPolicyArtifactSource).find(
                [(link.abstract_artifact, link.policy) for link in links]))

    def test_findByArtifact(self):
        # findByArtifact() finds only the relevant links.
        artifact = self.factory.makeAccessArtifact()
        links = [
            self.factory.makeAccessPolicyArtifact(artifact=artifact)
            for i in range(3)]
        self.factory.makeAccessPolicyArtifact()
        self.assertContentEqual(
            links,
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [artifact]))

    def test_findByPolicy(self):
        # findByPolicy() finds only the relevant links.
        policy = self.factory.makeAccessPolicy()
        links = [
            self.factory.makeAccessPolicyArtifact(policy=policy)
            for i in range(3)]
        self.factory.makeAccessPolicyArtifact()
        self.assertContentEqual(
            links,
            getUtility(IAccessPolicyArtifactSource).findByPolicy([policy]))

    def test_deleteByArtifact(self):
        # deleteByArtifact() removes the relevant grants.
        grant = self.factory.makeAccessPolicyArtifact()
        other_grant = self.factory.makeAccessPolicyArtifact()
        getUtility(IAccessPolicyArtifactSource).deleteByArtifact(
            [grant.abstract_artifact])
        self.assertContentEqual(
            [],
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [grant.abstract_artifact]))
        self.assertContentEqual(
            [other_grant],
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [other_grant.abstract_artifact]))


class TestAccessPolicyGrant(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_provides_interface(self):
        self.assertThat(
            self.factory.makeAccessPolicyGrant(),
            Provides(IAccessPolicyGrant))


class TestAccessPolicyGrantSource(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_grant(self):
        wanted = [
            (self.factory.makeAccessPolicy(), self.factory.makePerson(),
             self.factory.makePerson()),
            (self.factory.makeAccessPolicy(), self.factory.makePerson(),
             self.factory.makePerson()),
            ]
        grants = getUtility(IAccessPolicyGrantSource).grant(wanted)
        self.assertContentEqual(
            wanted, [(g.policy, g.grantee, g.grantor) for g in grants])

    def test_find(self):
        # find() finds the right grants.
        grants = [self.factory.makeAccessPolicyGrant() for i in range(2)]
        self.assertContentEqual(
            grants,
            getUtility(IAccessPolicyGrantSource).find(
                [(g.policy, g.grantee) for g in grants]))

    def test_findByPolicy(self):
        # findByPolicy() finds only the relevant grants.
        policy = self.factory.makeAccessPolicy()
        grants = [
            self.factory.makeAccessPolicyGrant(policy=policy)
            for i in range(3)]
        self.factory.makeAccessPolicyGrant()
        self.assertContentEqual(
            grants,
            getUtility(IAccessPolicyGrantSource).findByPolicy([policy]))


class TestAccessPolicyGrantFlatSource(TestCaseWithFactory):
    layer = DatabaseFunctionalLayer

    def test_findGranteesByPolicy(self):
        # findGranteesByPolicy() returns anyone with a grant for any of
        # the policies or the policies' artifacts.
        apgfs = getUtility(IAccessPolicyGrantFlatSource)

        # People with grants on the policy show up.
        policy = self.factory.makeAccessPolicy()
        policy_grant = self.factory.makeAccessPolicyGrant(policy=policy)
        self.assertContentEqual(
            [policy_grant.grantee], apgfs.findGranteesByPolicy([policy]))

        # But not people with grants on artifacts.
        artifact_grant = self.factory.makeAccessArtifactGrant()
        self.assertContentEqual(
            [policy_grant.grantee], apgfs.findGranteesByPolicy([policy]))

        # Unless the artifacts are linked to the policy.
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=policy)
        self.assertContentEqual(
            [policy_grant.grantee, artifact_grant.grantee],
            apgfs.findGranteesByPolicy([policy]))

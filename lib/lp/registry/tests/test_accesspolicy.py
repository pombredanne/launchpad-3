# Copyright 2011-2012 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from storm.exceptions import LostObjectError
from testtools.matchers import AllMatch
from zope.component import getUtility

from lp.registry.enums import (
    InformationType,
    SharingPermission,
    )
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
from lp.registry.model.person import Person
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
            (self.factory.makeProduct(), InformationType.PROPRIETARY),
            (self.factory.makeDistribution(),
                InformationType.UNEMBARGOEDSECURITY),
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
            (product, InformationType.PROPRIETARY),
            (product, InformationType.UNEMBARGOEDSECURITY),
            (distribution, InformationType.PROPRIETARY),
            (distribution, InformationType.UNEMBARGOEDSECURITY),
            (other_product, InformationType.PROPRIETARY),
            ]
        getUtility(IAccessPolicySource).create(wanted)

        query = [
            (product, InformationType.PROPRIETARY),
            (product, InformationType.UNEMBARGOEDSECURITY),
            (distribution, InformationType.UNEMBARGOEDSECURITY),
            ]
        self.assertContentEqual(
            query,
            [(policy.pillar, policy.type) for policy in
             getUtility(IAccessPolicySource).find(query)])

        query = [(distribution, InformationType.PROPRIETARY)]
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
        policies = (
            (product, InformationType.EMBARGOEDSECURITY),
            (product, InformationType.USERDATA),
            (distribution, InformationType.EMBARGOEDSECURITY),
            (distribution, InformationType.USERDATA),
            (other_product, InformationType.EMBARGOEDSECURITY),
            (other_product, InformationType.USERDATA),
            )
        self.assertContentEqual(
            policies,
            [(ap.pillar, ap.type)
                for ap in getUtility(IAccessPolicySource).findByPillar(
                [product, distribution, other_product])])
        self.assertContentEqual(
            [policy for policy in policies if policy[0] == product],
            [(ap.pillar, ap.type)
                for ap in getUtility(IAccessPolicySource).findByPillar(
                    [product])])


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
        link = self.factory.makeAccessPolicyArtifact(artifact=abstracts[0])
        self.assertContentEqual(
            [link],
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [abstracts[0]]))

        # Make some other grants and links to ensure they're unaffected.
        other_grants = [
            self.factory.makeAccessArtifactGrant(
                artifact=self.factory.makeAccessArtifact()),
            self.factory.makeAccessPolicyGrant(
                policy=self.factory.makeAccessPolicy()),
            ]
        other_link = self.factory.makeAccessPolicyArtifact()

        getUtility(IAccessArtifactSource).delete(concretes)
        IStore(grant).invalidate()
        self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertRaises(
            LostObjectError, getattr, abstracts[0], 'concrete_artifact')

        for other_grant in other_grants:
            self.assertIsNot(None, other_grant.grantor)

        self.assertContentEqual(
            [],
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [abstracts[0]]))
        self.assertContentEqual(
            [other_link],
            getUtility(IAccessPolicyArtifactSource).findByArtifact(
                [other_link.abstract_artifact]))

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

    def test_findByArtifact_specified_grantees(self):
        # findByArtifact() finds only the relevant grants for the specified
        # grantees.
        artifact = self.factory.makeAccessArtifact()
        grantees = [self.factory.makePerson() for i in range(3)]
        grants = [
            self.factory.makeAccessArtifactGrant(
                artifact=artifact, grantee=grantee)
            for grantee in grantees]
        self.factory.makeAccessArtifactGrant()
        self.assertContentEqual(
            grants[:2],
            getUtility(IAccessArtifactGrantSource).findByArtifact(
                [artifact], grantees=grantees[:2]))

    def test_revokeByArtifact(self):
        # revokeByArtifact() removes the relevant grants.
        artifact = self.factory.makeAccessArtifact()
        grant = self.factory.makeAccessArtifactGrant(artifact=artifact)
        other_grant = self.factory.makeAccessArtifactGrant()
        getUtility(IAccessArtifactGrantSource).revokeByArtifact([artifact])
        IStore(grant).invalidate()
        self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertIsNot(None, other_grant.grantor)

    def test_revokeByArtifact_specified_grantees(self):
        # revokeByArtifact() removes the relevant grants for the specified
        # grantees.
        artifact = self.factory.makeAccessArtifact()
        grantee = self.factory.makePerson()
        someone_else = self.factory.makePerson()
        grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=grantee)
        someone_else_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=someone_else)
        other_grant = self.factory.makeAccessArtifactGrant()
        aags = getUtility(IAccessArtifactGrantSource)
        aags.revokeByArtifact([artifact], [grantee])
        IStore(grant).invalidate()
        self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertEqual(
            someone_else_grant, aags.findByArtifact([artifact])[0])
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

    def test_revoke(self):
        # revoke() removes the specified grants.
        policy = self.factory.makeAccessPolicy()
        grants = [
            self.factory.makeAccessPolicyGrant(policy=policy)
            for i in range(3)]

        # Make some other grants to ensure they're unaffected.
        other_grants = [
            self.factory.makeAccessPolicyGrant(policy=policy)
            for i in range(3)]
        other_grants.extend([
            self.factory.makeAccessPolicyGrant()
            for i in range(3)])

        to_delete = [(grant.policy, grant.grantee) for grant in grants]
        getUtility(IAccessPolicyGrantSource).revoke(to_delete)
        IStore(policy).invalidate()

        for grant in grants:
            self.assertRaises(LostObjectError, getattr, grant, 'grantor')
        self.assertEqual(
            0, getUtility(IAccessPolicyGrantSource).find(to_delete).count())
        for other_grant in other_grants:
            self.assertIsNot(None, other_grant.grantor)


class TestAccessPolicyGrantFlatSource(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def setUp(self):
        super(TestAccessPolicyGrantFlatSource, self).setUp()
        self.apgfs = getUtility(IAccessPolicyGrantFlatSource)

    def _makePolicyGrants(self):
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        policy_grant = self.factory.makeAccessPolicyGrant(policy=policy)
        return policy, policy_with_no_grantees, policy_grant

    def test_findGranteesByPolicy(self):
        # findGranteesByPolicy() returns anyone with a grant for any of
        # the policies or the policies' artifacts.
        # This test checks that people with policy grants are returned.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        self.assertContentEqual(
            [policy_grant.grantee],
            self.apgfs.findGranteesByPolicy([policy, policy_with_no_grantees]))

    def test_findGranteesByPolicyIgnoreArtifactGrants(self):
        # findGranteesByPolicy() returns anyone with a grant for any of
        # the policies or the policies' artifacts.
        # This test checks that people with grants on artifacts which are not
        # linked to the access policy are ignored.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        self.assertContentEqual(
            [policy_grant.grantee],
            self.apgfs.findGranteesByPolicy([policy, policy_with_no_grantees]))
        self.factory.makeAccessArtifactGrant()
        self.assertContentEqual(
            [policy_grant.grantee],
            self.apgfs.findGranteesByPolicy([policy, policy_with_no_grantees]))

    def test_findGranteesByPolicyIncludeArtifactGrants(self):
        # findGranteesByPolicy() returns anyone with a grant for any of
        # the policies or the policies' artifacts.
        # This test checks that people with grants on artifacts which are
        # linked to the access policy are included.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        artifact_grant = self.factory.makeAccessArtifactGrant()
        self.assertContentEqual(
            [policy_grant.grantee],
            self.apgfs.findGranteesByPolicy([policy, policy_with_no_grantees]))
        another_policy = self.factory.makeAccessPolicy()
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=another_policy)
        self.assertContentEqual(
            [policy_grant.grantee, artifact_grant.grantee],
            self.apgfs.findGranteesByPolicy([
                policy, another_policy, policy_with_no_grantees]))

    def test_findGranteePermissionsByPolicy(self):
        # findGranteePermissionsByPolicy() returns anyone with a grant for any
        # of the policies or the policies' artifacts.
        # This test checks that people with policy grants are returned.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        self.assertContentEqual(
            [(policy_grant.grantee, {policy: SharingPermission.ALL}, [])],
            self.apgfs.findGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findGranteePermissionsIgnoreArtifactGrants(self):
        # findGranteePermissionsByPolicy() returns anyone with a grant for any
        # of the policies or the policies' artifacts.
        # This test checks that people with grants on artifacts which are not
        # linked to the access policy are ignored.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=policy_grant.grantee)
        self.factory.makeAccessArtifactGrant(artifact=artifact)
        self.assertContentEqual(
            [(policy_grant.grantee, {policy: SharingPermission.ALL}, [])],
            self.apgfs.findGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findGranteePermissionsIncludeArtifactGrants(self):
        # findGranteePermissionsByPolicy() returns anyone with a grant for any
        # of the policies or the policies' artifacts.
        # This test checks that people with grants on artifacts which are
        # linked to the access policy are included.
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        artifact = self.factory.makeAccessArtifact()
        artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=policy_grant.grantee)
        other_artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact)
        another_policy = self.factory.makeAccessPolicy()
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=another_policy)
        self.assertContentEqual(
            [(policy_grant.grantee, {
                policy: SharingPermission.ALL,
                another_policy: SharingPermission.SOME},
              [another_policy.type]),
             (other_artifact_grant.grantee, {
                 another_policy: SharingPermission.SOME},
              [another_policy.type])],
            self.apgfs.findGranteePermissionsByPolicy([
                policy, another_policy, policy_with_no_grantees]))

    def test_findGranteePermissionsByPolicySlicing(self):
        # findGranteePermissionsByPolicy() returns anyone with a grant for any
        # of the policies or the policies' artifacts.
        # This test checks that slicing works by person, not by
        # (person, policy).
        (policy, policy_with_no_grantees,
         policy_grant) = self._makePolicyGrants()
        another_policy = self.factory.makeAccessPolicy()
        self.assertContentEqual(
            [(policy_grant.grantee, {
                policy: SharingPermission.ALL}, [])],
            self.apgfs.findGranteePermissionsByPolicy([
                policy, another_policy, policy_with_no_grantees]).order_by(
                    Person.id)[:1])

    def test_findGranteePermissionsByPolicy_shared_artifact_types(self):
        # findGranteePermissionsByPolicy() returns all information types for
        # which grantees have been granted access one or more artifacts of that
        # type.
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        policy_grant = self.factory.makeAccessPolicyGrant(policy=policy)
        artifact = self.factory.makeAccessArtifact()
        artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=policy_grant.grantee)
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=policy)
        self.assertContentEqual(
            [(policy_grant.grantee, {policy: SharingPermission.ALL},
              [policy.type])],
            self.apgfs.findGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findGranteePermissionsByPolicy_filter_grantees(self):
        # findGranteePermissionsByPolicy() returns anyone with a grant for any
        # of the policies or the policies' artifacts so long as the grantee is
        # in the specified list of grantees.
        policy = self.factory.makeAccessPolicy()
        grantee_in_result = self.factory.makePerson()
        grantee_not_in_result = self.factory.makePerson()
        policy_grant = self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=grantee_in_result)
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=grantee_not_in_result)
        self.assertContentEqual(
            [(policy_grant.grantee, {policy: SharingPermission.ALL}, [])],
            self.apgfs.findGranteePermissionsByPolicy(
                [policy], [grantee_in_result]))

    def _make_IndirectGrants(self):
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        indirect_person_grantee = self.factory.makePerson()
        team_grantee = self.factory.makeTeam(members=[indirect_person_grantee])
        self.factory.makeAccessPolicyGrant(policy=policy, grantee=team_grantee)
        return (
            policy, policy_with_no_grantees, team_grantee,
            indirect_person_grantee)

    def test_findIndirectGranteePermissionsByPolicy(self):
        # findIndirectGranteePermissionsByPolicy() returns anyone with a grant
        # for any of the policies or the policies' artifacts. The result
        # includes members of teams with access and a list of teams via which
        # they have gained access.
        # This test checks that people with policy grants are returned.
        (policy,
         policy_with_no_grantees,
         team_grantee, indirect_person_grantee) = self._make_IndirectGrants()
        policy_info = {policy: SharingPermission.ALL}
        expected_grantees = [
            (member, policy_info, [team_grantee], [])
            for member in team_grantee.activemembers]
        expected_grantees.append(
            (team_grantee, policy_info, None, []))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findIndirectGranteePermissionsIgnoreArtifactGrants(self):
        # findIndirectGranteePermissionsByPolicy() returns anyone with a grant
        # for any of the policies or the policies' artifacts. The result
        # includes members of teams with access and a list of teams via which
        # they have gained access.
        # This test checks that people with grants on artifacts which are not
        # linked to the access policy are ignored.
        (policy,
         policy_with_no_grantees,
         team_grantee, indirect_person_grantee) = self._make_IndirectGrants()
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=team_grantee)
        self.factory.makeAccessArtifactGrant(artifact=artifact)
        policy_info = {policy: SharingPermission.ALL}
        expected_grantees = [
            (member, policy_info, [team_grantee], [])
            for member in team_grantee.activemembers]
        expected_grantees.append(
            (team_grantee, policy_info, None, []))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findIndirectGranteePermissionsIncludeArtifactGrants(self):
        # findIndirectGranteePermissionsByPolicy() returns anyone with a grant
        # for any of the policies or the policies' artifacts. The result
        # includes members of teams with access and a list of teams via which
        # they have gained access.
        # This test checks that people with grants on artifacts which are
        # linked to the access policy are included.
        (policy,
         policy_with_no_grantees,
         team_grantee, indirect_person_grantee) = self._make_IndirectGrants()
        artifact = self.factory.makeAccessArtifact()
        artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=team_grantee)
        other_artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact)
        another_policy = self.factory.makeAccessPolicy()
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=another_policy)
        policy_info = {
            policy: SharingPermission.ALL,
            another_policy: SharingPermission.SOME}
        expected_grantees = [
            (member, policy_info, [team_grantee], [another_policy.type])
            for member in team_grantee.activemembers]
        expected_grantees.append(
            (team_grantee, policy_info, None, [another_policy.type]))
        expected_grantees.append(
            (other_artifact_grant.grantee,
             {another_policy: SharingPermission.SOME}, None,
             [another_policy.type]))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy([
                policy, another_policy, policy_with_no_grantees]))

    def test_findIndirectGranteePermissionsByPolicySlicing(self):
        # findIndirectGranteePermissionsByPolicy() returns anyone with a grant
        # for any of the policies or the policies' artifacts. The result
        # includes members of teams with access and a list of teams via which
        # they have gained access.
        # This test checks that slicing works by person, not by
        # (person, policy).
        (policy,
         policy_with_no_grantees,
         team_grantee, indirect_person_grantee) = self._make_IndirectGrants()
        another_policy = self.factory.makeAccessPolicy()
        self.assertContentEqual(
            [(indirect_person_grantee, {
                policy: SharingPermission.ALL}, [team_grantee], [])],
            self.apgfs.findIndirectGranteePermissionsByPolicy([
                policy, another_policy, policy_with_no_grantees]).order_by(
                    Person.id)[:1])

    def test_findIndirectGranteePermissionsByPolicy_filter_grantees(
                                                                        self):
        # findIndirectGranteePermissionsByPolicy() returns anyone with a grant
        # for any of the policies or the policies' artifacts so long as the
        # grantee is in the specified list of grantees.
        policy = self.factory.makeAccessPolicy()
        grantee_not_in_result = self.factory.makePerson()
        indirect_person_grantee = self.factory.makePerson()
        team_grantee = self.factory.makeTeam(members=[indirect_person_grantee])
        self.factory.makeAccessPolicyGrant(policy=policy, grantee=team_grantee)
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=grantee_not_in_result)
        self.assertContentEqual(
            [(indirect_person_grantee, {policy: SharingPermission.ALL},
              [team_grantee], [])],
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy], [indirect_person_grantee]))

    def test_findIndirectGranteePermissionsMultiTeam(self):
        # Test that findIndirectGranteePermissionsByPolicy() works correctly
        # when a user is granted access via membership of more than one team.
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        # Make an indirect grantee belonging to team1 and team2.
        indirect_person_grantee = self.factory.makePerson()
        team_grantee1 = self.factory.makeTeam(
            members=[indirect_person_grantee])
        # Make a team for indirect grantee which should not appear in the
        # results.
        self.factory.makeTeam(members=[indirect_person_grantee])
        team_grantee2 = self.factory.makeTeam(
            members=[indirect_person_grantee])
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=team_grantee1)
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=team_grantee2)
        policy_info = {policy: SharingPermission.ALL}
        # Indirect grantee has access.
        expected_grantees = [
            (indirect_person_grantee, policy_info,
             sorted([team_grantee1, team_grantee2],
                key=lambda x: x.displayname), [])]
        # All other team members have access.
        expected_grantees.extend([(member, policy_info, [team_grantee1], [])
            for member in team_grantee1.activemembers
            if member != indirect_person_grantee])
        expected_grantees.extend([(member, policy_info, [team_grantee2], [])
            for member in team_grantee2.activemembers
            if member != indirect_person_grantee])
        # The team itself has access also.
        expected_grantees.append((team_grantee1, policy_info, None, []))
        expected_grantees.append((team_grantee2, policy_info, None, []))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findIndirectGranteePermissionsDirect(self):
        # Test that findIndirectGranteePermissionsByPolicy() works correctly
        # when a user is granted access directly as well as via membership of a
        # team.
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        # Make an direct grantee.
        person_grantee = self.factory.makePerson()
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=person_grantee)
        # Make a team grantee with the person grantee as a member.
        team_grantee = self.factory.makeTeam(owner=self.factory.makePerson(),
            members=[person_grantee])
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=team_grantee)
        # Make a team for indirect grantee which should not appear in the
        # results.
        self.factory.makeTeam(members=[person_grantee])
        policy_info = {policy: SharingPermission.ALL}
        # Direct grantee has access.
        expected_grantees = [(person_grantee, policy_info, None, [])]
        # All other team members have indirect access.
        expected_grantees.extend([(member, policy_info, [team_grantee], [])
            for member in team_grantee.activemembers
            if member != person_grantee])
        # The team itself has access also.
        expected_grantees.append((team_grantee, policy_info, None, []))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findIndirectGranteePermissionsMultiTeamPermissions(self):
        # Test that findIndirectGranteePermissionsByPolicy() works correctly
        # when a user is granted access via membership of more than one team
        # where each team has a different level of access. If an indirect
        # grantee has both ALL and SOME, then ALL is shown.
        policy_with_no_grantees = self.factory.makeAccessPolicy()
        policy = self.factory.makeAccessPolicy()
        indirect_person_grantee = self.factory.makePerson()

        # One team has ALL access.
        team_grantee1 = self.factory.makeTeam(
            members=[indirect_person_grantee])
        self.factory.makeAccessPolicyGrant(
            policy=policy, grantee=team_grantee1)

        # Another team has SOME access.
        indirect_person_grantee2 = self.factory.makePerson()
        team_grantee2 = self.factory.makeTeam(
            members=[indirect_person_grantee, indirect_person_grantee2])
        artifact = self.factory.makeAccessArtifact()
        artifact_grant = self.factory.makeAccessArtifactGrant(
            artifact=artifact, grantee=team_grantee2)
        self.factory.makeAccessPolicyArtifact(
            artifact=artifact_grant.abstract_artifact, policy=policy)

        policy_info = {policy: SharingPermission.ALL}
        expected_grantees = [
            (indirect_person_grantee, policy_info,
             sorted([team_grantee1, team_grantee2],
                key=lambda x: x.displayname), [policy.type])]
        expected_grantees.extend([(member, policy_info, [team_grantee1], [])
            for member in team_grantee1.activemembers
            if member != indirect_person_grantee])
        expected_grantees.append((team_grantee1, policy_info, None, []))
        policy_info = {policy: SharingPermission.SOME}
        expected_grantees.extend(
            [(member, policy_info, [team_grantee2], [policy.type])
            for member in team_grantee2.activemembers
            if member != indirect_person_grantee])
        expected_grantees.append(
            (team_grantee2, policy_info, None, [policy.type]))
        self.assertContentEqual(
            expected_grantees,
            self.apgfs.findIndirectGranteePermissionsByPolicy(
                [policy, policy_with_no_grantees]))

    def test_findArtifactsByGrantee(self):
        # findArtifactsByGrantee() returns the artifacts for grantee for any of
        # the policies.
        policy = self.factory.makeAccessPolicy()
        grantee = self.factory.makePerson()
        # Artifacts not linked to the policy do not show up.
        artifact = self.factory.makeAccessArtifact()
        self.factory.makeAccessArtifactGrant(artifact, grantee)
        self.assertContentEqual(
            [], self.apgfs.findArtifactsByGrantee(grantee, [policy]))
        # Artifacts linked to the policy do show up.
        self.factory.makeAccessPolicyArtifact(artifact=artifact, policy=policy)
        self.assertContentEqual(
            [artifact], self.apgfs.findArtifactsByGrantee(grantee, [policy]))

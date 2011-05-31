# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the BugSummary class and underlying database triggers."""

__metaclass__ = type

from canonical.launchpad.interfaces.lpstorm import IMasterStore
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.interfaces.bugsummary import IBugSummary
from lp.bugs.interfaces.bugtask import BugTaskStatus
from lp.bugs.model.bug import BugTag
from lp.bugs.model.bugsummary import BugSummary
from lp.bugs.model.bugtask import BugTask
from lp.registry.model.teammembership import TeamParticipation
from lp.testing import (
    login_celebrity,
    TestCaseWithFactory,
    )


class TestBugSummary(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    def setUp(self):
        super(TestBugSummary, self).setUp()

        # Some things we are testing are impossible as mere mortals,
        # but might happen from the SQL command line.
        # XXX: Should we just grant mortals permission to UPDATE BugTag
        # etc. ?
        LaunchpadZopelessLayer.switchDbUser('testadmin')

        # XXX: Unnecessary?
        # And stop security wrappers getting in the way since they are
        # uninteresting to these tests.
        # login_celebrity('admin')

        self.store = IMasterStore(BugSummary)

    def getPublicCount(self, *bugsummary_find_expr):
        return self.getCount(None, *bugsummary_find_expr)

    def getCount(self, person, *bugsummary_find_expr):
        # Flush any changes. This causes the database triggers to fire
        # and BugSummary records to be created.
        self.store.flush()

        # Invalidate all BugSummary records from the cache. The current
        # test may have already pulled in BugSummary records that may
        # now be invalid. This normally isn't a problem, as normal code
        # is only ever interested in BugSummary records created in
        # previous transactions.
        self.store.invalidate()

        public_summaries = self.store.find(
            BugSummary,
            BugSummary.viewed_by == None,
            *bugsummary_find_expr)
        private_summaries = self.store.find(
            BugSummary,
            BugSummary.viewed_by_id == TeamParticipation.teamID,
            TeamParticipation.person == person)
        all_summaries = public_summaries.union(private_summaries, all=True)

        # Note that if there a 0 records found, sum() returns None, but
        # we prefer to return 0 here.
        return all_summaries.sum(BugSummary.count) or 0

    def test_providesInterface(self):
        bug_summary = self.store.find(BugSummary)[0]
        self.assertTrue(IBugSummary.providedBy(bug_summary))

    def test_addTag(self):
        tag = u'pustular'

        # Ensure nothing using our tag yet.
        self.assertEqual(self.getPublicCount(BugSummary.tag == tag), 0)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertEqual(
            self.getPublicCount(
                BugSummary.product == product,
                BugSummary.tag == tag),
            3)

        # There should be no other BugSummary rows.
        self.assertEqual(self.getPublicCount(BugSummary.tag == tag), 3)

    def test_changeTag(self):
        old_tag = u'pustular'
        new_tag = u'flatulent'

        # Ensure nothing using our tags yet.
        self.assertEqual(self.getPublicCount(BugSummary.tag == old_tag), 0)
        self.assertEqual(self.getPublicCount(BugSummary.tag == new_tag), 0)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = old_tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertEqual(
            self.getPublicCount(
                BugSummary.product == product,
                BugSummary.tag == old_tag
                ), 3)

        for count in reversed(range(3)):
            bug_tag = self.store.find(BugTag, tag=old_tag).any()
            bug_tag.tag = new_tag

            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.tag == old_tag),
                count)
            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.tag == new_tag),
                3 - count)

        # There should be no other BugSummary rows.
        self.assertEqual(self.getPublicCount(BugSummary.tag == old_tag), 0)
        self.assertEqual(self.getPublicCount(BugSummary.tag == new_tag), 3)

    def test_removeTag(self):
        tag = u'pustular'

        # Ensure nothing using our tags yet.
        self.assertEqual(self.getPublicCount(BugSummary.tag == tag), 0)

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_tag = BugTag()
            bug_tag.bug = bug
            bug_tag.tag = tag
            self.store.add(bug_tag)

        # Number of tagged tasks for a particular product
        self.assertEqual(
            self.getPublicCount(
                BugSummary.product == product,
                BugSummary.tag == tag
                ), 3)

        for count in reversed(range(3)):
            bug_tag = self.store.find(BugTag, tag=tag).any()
            self.store.remove(bug_tag)
            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.tag == tag
                    ), count)

        # There should be no other BugSummary rows.
        self.assertEqual(self.getPublicCount(BugSummary.tag == tag), 0)

    def test_changeStatus(self):
        org_status = BugTaskStatus.NEW
        new_status = BugTaskStatus.INVALID

        product = self.factory.makeProduct()

        for count in range(3):
            bug = self.factory.makeBug(product=product)
            bug_task = self.store.find(BugTask, bug=bug).one()
            bug_task.status = org_status

            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.status == org_status),
                count + 1)

        for count in reversed(range(3)):
            bug_task = self.store.find(
                BugTask, product=product, status=org_status).any()
            bug_task.status = new_status
            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.status == org_status),
                count)
            self.assertEqual(
                self.getPublicCount(
                    BugSummary.product == product,
                    BugSummary.status == new_status),
                3 - count)

    def test_makePrivate(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        # Make the bug private. We have to use the Python API to ensure
        # BugSubscription records get created for implicit
        # subscriptions.
        bug.setPrivate(True, bug.owner)

        # Confirm counts.
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            0)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product == product),
            0)

    def test_makePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product, private=True)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        # Make the bug public. We have to use the Python API to ensure
        # BugSubscription records get created for implicit
        # subscriptions.
        bug.setPrivate(False, bug.owner)

        self.assertEqual(
            self.getPublicCount(BugSummary.product==product),
            1)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product==product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product==product),
            1)

    def test_subscribePrivate(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product, private=True)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            0)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product == product),
            0)

    def test_unsubscribePrivate(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product, private=True)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)
        bug.subscribe(person=person_b, subscribed_by=person_b)
        bug.unsubscribe(person=person_b, unsubscribed_by=person_b)

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            0)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product == product),
            0)

    def test_subscribePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product == product),
            1)

    def test_unsubscribePublic(self):
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(product=product)

        person_a = self.factory.makePerson()
        person_b = self.factory.makePerson()
        bug.subscribe(person=person_a, subscribed_by=person_a)
        bug.subscribe(person=person_b, subscribed_by=person_b)
        bug.unsubscribe(person=person_b, unsubscribed_by=person_b)

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_a, BugSummary.product == product),
            1)
        self.assertEqual(
            self.getCount(person_b, BugSummary.product == product),
            1)

    def test_addProduct(self):
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()
        bug = self.factory.makeBug(distribution=distribution)

        self.assertEqual(
            self.getPublicCount(BugSummary.distribution == distribution),
            1)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            0)

        self.factory.makeBugTask(bug=bug, target=product)

        self.assertEqual(
            self.getPublicCount(BugSummary.distribution == distribution),
            1)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            1)

    def test_changeProduct(self):
        product_a = self.factory.makeProduct()
        product_b = self.factory.makeProduct()
        bug_task = self.factory.makeBugTask(target=product_a)

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product_a),
            1)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product_b),
            0)

        bug_task.product = product_b

        self.assertEqual(
            self.getPublicCount(BugSummary.product == product_a),
            0)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product_b),
            1)

    def test_removeProduct(self):
        distribution = self.factory.makeDistribution()
        product = self.factory.makeProduct()

        product_bug_task = self.factory.makeBugTask(target=product)
        distribution_bug_task = self.factory.makeBugTask(
            bug=product_bug_task.bug, target=distribution)

        self.assertEqual(
            self.getPublicCount(BugSummary.distribution == distribution),
            1)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            1)

        self.store.remove(product_bug_task)

        self.assertEqual(
            self.getPublicCount(BugSummary.distribution == distribution),
            1)
        self.assertEqual(
            self.getPublicCount(BugSummary.product == product),
            0)

    def test_addProductSeries(self):
        raise NotImplementedError

    def test_changeProductSeries(self):
        raise NotImplementedError

    def test_removeProductSeries(self):
        raise NotImplementedError

    def test_addDistribution(self):
        raise NotImplementedError

    def test_changeDistribution(self):
        raise NotImplementedError

    def test_removeDistribution(self):
        raise NotImplementedError

    def test_addDistroSeries(self):
        raise NotImplementedError

    def test_changeDistroSeries(self):
        raise NotImplementedError

    def test_removeDistroSeries(self):
        raise NotImplementedError

    def test_addDistributionSourcePackageName(self):
        raise NotImplementedError

    def test_changeDistributionSourcePackageName(self):
        raise NotImplementedError

    def test_removeDistributionSourcePackageName(self):
        raise NotImplementedError

    def test_addDistroSeriesSourcePackageName(self):
        raise NotImplementedError

    def test_changeDistroSeriesSourcePackageName(self):
        raise NotImplementedError

    def test_removeDistroSeriesSourcePackageName(self):
        raise NotImplementedError

    def test_addMilestone(self):
        raise NotImplemetnedError

    def test_changeMilestone(self):
        raise NotImplementedError

    def test_removeMilestone(self):
        raise NotImplementedError



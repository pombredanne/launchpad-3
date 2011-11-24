# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bulk database functions."""

__metaclass__ = type

from storm.exceptions import ClassInfoError
from storm.info import get_obj_info
from storm.store import Store
import transaction
from zope.security import (
    checker,
    proxy,
    )

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    ISlaveStore,
    IStore,
    )
from canonical.testing.layers import DatabaseFunctionalLayer
from lp.bugs.model.bug import BugAffectsPerson
from lp.code.model.branchsubscription import BranchSubscription
from lp.registry.model.person import Person
from lp.services.database import bulk
from lp.soyuz.model.component import Component
from lp.testing import (
    TestCase,
    TestCaseWithFactory,
    )


object_is_key = lambda thing: thing


class TestBasicFunctions(TestCase):

    def test_collate_empty_list(self):
        self.failUnlessEqual([], list(bulk.collate([], object_is_key)))

    def test_collate_when_object_is_key(self):
        self.failUnlessEqual(
            [(1, [1])],
            list(bulk.collate([1], object_is_key)))
        self.failUnlessEqual(
            [(1, [1]), (2, [2, 2])],
            sorted(bulk.collate([1, 2, 2], object_is_key)))

    def test_collate_with_key_function(self):
        self.failUnlessEqual(
            [(4, ['fred', 'joss']), (6, ['barney'])],
            sorted(bulk.collate(['fred', 'barney', 'joss'], len)))

    def test_get_type(self):
        self.failUnlessEqual(object, bulk.get_type(object()))

    def test_get_type_with_proxied_object(self):
        proxied_object = proxy.Proxy('fred', checker.Checker({}))
        self.failUnlessEqual(str, bulk.get_type(proxied_object))


class TestLoaders(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_gen_reload_queries_with_empty_list(self):
        self.failUnlessEqual([], list(bulk.gen_reload_queries([])))

    def test_gen_reload_queries_with_single_object(self):
        # gen_reload_queries() should generate a single query for a
        # single object.
        db_objects = [self.factory.makeSourcePackageName()]
        db_queries = list(bulk.gen_reload_queries(db_objects))
        self.failUnlessEqual(1, len(db_queries))
        db_query = db_queries[0]
        self.failUnlessEqual(db_objects, list(db_query))

    def test_gen_reload_queries_with_multiple_similar_objects(self):
        # gen_reload_queries() should generate a single query to load
        # multiple objects of the same type.
        db_objects = set(
            self.factory.makeSourcePackageName() for i in range(5))
        db_queries = list(bulk.gen_reload_queries(db_objects))
        self.failUnlessEqual(1, len(db_queries))
        db_query = db_queries[0]
        self.failUnlessEqual(db_objects, set(db_query))

    def test_gen_reload_queries_with_mixed_objects(self):
        # gen_reload_queries() should return one query for each
        # distinct object type in the given objects.
        db_objects = set(
            self.factory.makeSourcePackageName() for i in range(5))
        db_objects.update(
            self.factory.makeComponent() for i in range(5))
        db_queries = list(bulk.gen_reload_queries(db_objects))
        self.failUnlessEqual(2, len(db_queries))
        db_objects_loaded = set()
        for db_query in db_queries:
            objects = set(db_query)
            # None of these objects should have been loaded before.
            self.failUnlessEqual(
                set(), objects.intersection(db_objects_loaded))
            db_objects_loaded.update(objects)
        self.failUnlessEqual(db_objects, db_objects_loaded)

    def test_gen_reload_queries_with_mixed_stores(self):
        # gen_reload_queries() returns one query for each distinct
        # store even for the same object type.
        db_object = self.factory.makeComponent()
        db_object_type = bulk.get_type(db_object)
        # Commit so the database object is available in both master
        # and slave stores.
        transaction.commit()
        db_objects = set(
            (IMasterStore(db_object).get(db_object_type, db_object.id),
             ISlaveStore(db_object).get(db_object_type, db_object.id)))
        db_queries = list(bulk.gen_reload_queries(db_objects))
        self.failUnlessEqual(2, len(db_queries))
        db_objects_loaded = set()
        for db_query in db_queries:
            objects = set(db_query)
            # None of these objects should have been loaded before.
            self.failUnlessEqual(
                set(), objects.intersection(db_objects_loaded))
            db_objects_loaded.update(objects)
        self.failUnlessEqual(db_objects, db_objects_loaded)

    def test_gen_reload_queries_with_non_Storm_objects(self):
        # gen_reload_queries() does not like non-Storm objects.
        self.assertRaises(
            ClassInfoError, list, bulk.gen_reload_queries(['bogus']))

    def test_gen_reload_queries_with_compound_primary_keys(self):
        # gen_reload_queries() does not like compound primary keys.
        db_queries = bulk.gen_reload_queries([BugAffectsPerson()])
        self.assertRaisesWithContent(
            AssertionError,
            'Compound primary keys are not supported: BugAffectsPerson.',
            list, db_queries)

    def test_reload(self):
        # reload() loads the given objects using queries generated by
        # gen_reload_queries().
        db_object = self.factory.makeComponent()
        db_object_naked = proxy.removeSecurityProxy(db_object)
        db_object_info = get_obj_info(db_object_naked)
        IStore(db_object).flush()
        self.failUnlessEqual(None, db_object_info.get('invalidated'))
        IStore(db_object).invalidate(db_object)
        self.failUnlessEqual(True, db_object_info.get('invalidated'))
        bulk.reload([db_object])
        self.failUnlessEqual(None, db_object_info.get('invalidated'))

    def test_load(self):
        # load() loads objects of the given type by their primary keys.
        db_objects = [
            self.factory.makeComponent(),
            self.factory.makeComponent(),
            ]
        db_object_ids = [db_object.id for db_object in db_objects]
        self.assertEqual(
            set(bulk.load(Component, db_object_ids)),
            set(db_objects))

    def test_load_with_non_Storm_objects(self):
        # load() does not like non-Storm objects.
        self.assertRaises(
            ClassInfoError, bulk.load, str, [])

    def test_load_with_compound_primary_keys(self):
        # load() does not like compound primary keys.
        self.assertRaisesWithContent(
            AssertionError,
            'Compound primary keys are not supported: BugAffectsPerson.',
            bulk.load, BugAffectsPerson, [])

    def test_load_with_store(self):
        # load() can use an alternative store.
        db_object = self.factory.makeComponent()
        # Commit so the database object is available in both master
        # and slave stores.
        transaction.commit()
        # Master store.
        master_store = IMasterStore(db_object)
        [db_object_from_master] = bulk.load(
            Component, [db_object.id], store=master_store)
        self.assertEqual(
            Store.of(db_object_from_master), master_store)
        # Slave store.
        slave_store = ISlaveStore(db_object)
        [db_object_from_slave] = bulk.load(
            Component, [db_object.id], store=slave_store)
        self.assertEqual(
            Store.of(db_object_from_slave), slave_store)

    def test_load_related(self):
        owning_objects = [
            self.factory.makeBug(),
            self.factory.makeBug(),
            ]
        expected = set(bug.owner for bug in owning_objects)
        self.assertEqual(expected,
            set(bulk.load_related(Person, owning_objects, ['ownerID'])))

    def test_load_referencing(self):
        owned_objects = [
            self.factory.makeBranch(),
            self.factory.makeBranch(),
            ]
        expected = set(list(owned_objects[0].subscriptions) + 
            list(owned_objects[1].subscriptions))
        self.assertNotEqual(0, len(expected))
        self.assertEqual(expected,
            set(bulk.load_referencing(BranchSubscription, owned_objects,
                ['branchID'])))

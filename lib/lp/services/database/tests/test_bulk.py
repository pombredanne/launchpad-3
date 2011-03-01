# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Test the bulk database functions."""

__metaclass__ = type

import unittest

from storm.info import get_obj_info
import transaction
import zope.security.checker
import zope.security.proxy

from canonical.launchpad.interfaces.lpstorm import (
    IMasterStore,
    ISlaveStore,
    IStore,
    )
from canonical.testing.layers import LaunchpadZopelessLayer
from lp.bugs.model.bug import BugAffectsPerson
from lp.services.database import bulk
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
        proxied_object = zope.security.proxy.Proxy(
            'fred', zope.security.checker.Checker({}))
        self.failUnlessEqual(str, bulk.get_type(proxied_object))


class TestLoaders(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

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
        self.assertRaisesWithContent(
            AssertionError,
            "Cannot load objects of type str: ['fred']",
            list, bulk.gen_reload_queries(['fred']))

    def test_gen_reload_queries_with_compound_primary_keys(self):
        # gen_reload_queries() does not like compound primary keys.
        db_queries = bulk.gen_reload_queries([BugAffectsPerson()])
        self.assertRaisesWithContent(
            AssertionError,
            'Compound primary keys are not supported: BugAffectsPerson.',
            list, db_queries)

    def test_load(self):
        # load() loads the given objects using queries generated by
        # gen_reload_queries().
        db_object = self.factory.makeComponent()
        db_object_naked = zope.security.proxy.removeSecurityProxy(db_object)
        db_object_info = get_obj_info(db_object_naked)
        IStore(db_object).flush()
        self.failUnlessEqual(None, db_object_info.get('invalidated'))
        IStore(db_object).invalidate(db_object)
        self.failUnlessEqual(True, db_object_info.get('invalidated'))
        bulk.reload([db_object])
        self.failUnlessEqual(None, db_object_info.get('invalidated'))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

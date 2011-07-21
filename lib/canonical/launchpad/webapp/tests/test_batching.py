# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type

from unittest import TestLoader

from lazr.batchnavigator.interfaces import IRangeFactory
from zope.security.proxy import isinstance as zope_isinstance
from canonical.launchpad.components.decoratedresultset import (
    DecoratedResultSet,
    )
from canonical.launchpad.database.librarian import LibraryFileAlias
from canonical.launchpad.webapp.batching import StormRangeFactory
from canonical.launchpad.webapp.interfaces import StormRangeFactoryError
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing.layers import LaunchpadFunctionalLayer
from lp.registry.model.person import Person
from lp.testing import (
    TestCaseWithFactory,
    person_logged_in,
    )


class TestStormRangeFactory(TestCaseWithFactory):
    """Tests for StormRangeFactory."""

    layer = LaunchpadFunctionalLayer

    def makeStormResultSet(self):
        bug = self.factory.makeBug()
        for count in range(5):
            person = self.factory.makePerson()
            with person_logged_in(person):
                bug.markUserAffected(person, True)
        return bug.users_affected

    def makeDecoratedStormResultSet(self):
        bug = self.factory.makeBug()
        with person_logged_in(bug.owner):
            for count in range(5):
                self.factory.makeBugAttachment(bug=bug, owner=bug.owner)
        result = bug.attachments
        self.assertTrue(zope_isinstance(result, DecoratedResultSet))
        return result

    def test_StormRangeFactory_implements_IRangeFactory(self):
        resultset = self.makeStormResultSet()
        range_factory = StormRangeFactory(resultset)
        self.assertTrue(verifyObject(IRangeFactory, range_factory))

    def test_getOrderValuesFor__one_sort_column(self):
        # StormRangeFactory.getOrderValuesFor() returns the values
        # of the fields used in order_by expresssions for a given
        # result row.
        resultset = self.makeStormResultSet()
        resultset.order_by(Person.id)
        range_factory = StormRangeFactory(resultset)
        order_values = range_factory.getOrderValuesFor(resultset[0])
        self.assertEqual([resultset[0].id], order_values)

    def test_getOrderValuesFor__two_sort_columns(self):
        # Sorting by more than one column is supported.
        resultset = self.makeStormResultSet()
        resultset.order_by(Person.displayname, Person.name)
        range_factory = StormRangeFactory(resultset)
        order_values = range_factory.getOrderValuesFor(resultset[0])
        self.assertEqual(
            [resultset[0].displayname, resultset[0].name], order_values)

    def test_getOrderValuesFor__string_as_sort_expression(self):
        # Sorting by a string expression is not supported.
        resultset = self.makeStormResultSet()
        resultset.order_by('Person.id')
        range_factory = StormRangeFactory(resultset)
        exception = self.assertRaises(
            StormRangeFactoryError, range_factory.getOrderValuesFor,
            resultset[0])
        self.assertEqual(
            "StormRangeFactory supports only sorting by PropertyColumn, "
            "not by 'Person.id'.",
            str(exception))

    def test_getOrderValuesFor__generic_storm_expression_as_sort_expr(self):
        # Sorting by a generic Strom expression is not supported.
        resultset = self.makeStormResultSet()
        range_factory = StormRangeFactory(resultset)
        exception = self.assertRaises(
            StormRangeFactoryError, range_factory.getOrderValuesFor,
            resultset[0])
        self.assertTrue(
            str(exception).startswith(
                'StormRangeFactory supports only sorting by PropertyColumn, '
                'not by <storm.expr.SQL object at'))

    def test_getOrderValuesFor__unordered_result_set(self):
        # If a result set is not ordered, it cannot be used with a
        # StormRangeFactory.
        resultset = self.makeStormResultSet()
        resultset.order_by()
        range_factory = StormRangeFactory(resultset)
        exception = self.assertRaises(
            StormRangeFactoryError, range_factory.getOrderValuesFor,
            resultset[0])
        self.assertEqual(
            "StormRangeFactory requires a sorted result set.",
            str(exception))

    def test_getOrderValuesFor__decorated_result_set(self):
        # getOrderValuesFor() knows how to retrieve SQL sort values
        # from DecoratedResultSets.
        resultset = self.makeDecoratedStormResultSet()
        range_factory = StormRangeFactory(resultset)
        self.assertEqual(
            [resultset[0].id], range_factory.getOrderValuesFor(resultset[0]))

    def test_getOrderValuesFor__value_from_second_element_of_result_row(self):
        # getOrderValuesFor() can retrieve values from attributes
        # of any Storm table class instance which appear in a result row.
        resultset = self.makeDecoratedStormResultSet()
        resultset = resultset.order_by(LibraryFileAlias.id)
        plain_resultset = resultset.getPlainResultSet()
        range_factory = StormRangeFactory(resultset)
        self.assertEqual(
            [plain_resultset[0][1].id],
            range_factory.getOrderValuesFor(plain_resultset[0]))

    def test_getOrderValuesFor__table_not_included_in_results(self):
        # Attempts to use a sort by a column which does not appear in the
        # data returned by the query raise a StormRangeFactoryError.
        resultset = self.makeStormResultSet()
        resultset.order_by(LibraryFileAlias.id)
        range_factory = StormRangeFactory(resultset)
        exception = self.assertRaises(
            StormRangeFactoryError, range_factory.getOrderValuesFor,
            resultset[0])
        self.assertEqual(
            "Instances of <class "
            "'canonical.launchpad.database.librarian.LibraryFileAlias'> are "
            "not contained in the result set, but are required to retrieve "
            "the value of LibraryFileAlias.id.",
            str(exception))


def test_suite():
    return TestLoader().loadTestsFromName(__name__)

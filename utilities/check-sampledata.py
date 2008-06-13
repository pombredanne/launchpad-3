#! /usr/bin/python2.4
# Copyright 2007 Canonical Ltd.  All rights reserved.

"""
check-sampledata.py - Perform various checks on Sample Data

= Launchpad Sample Data Consistency Checks =

XXX flacoste 2007/03/08 Once all problems exposed by this script are solved,
it should be integrated to our automated test suite.

This script verify that all objects in sample data provides the interfaces
they are supposed to. It also makes sure that the object pass its schema
validation.

Finally, it can also be used to report about sample data lacking in breadth.

"""

__metatype__ = type

import _pythonpath

import inspect
from optparse import OptionParser
import re
from textwrap import dedent

from psycopg2 import ProgrammingError

from zope.interface import providedBy
from zope.interface.exceptions import (
    BrokenImplementation, BrokenMethodImplementation)
from zope.interface.verify import verifyObject
from zope.schema.interfaces import IField, ValidationError

from canonical.database.sqlbase import SQLBase
import canonical.launchpad.database
from canonical.lp import initZopeless
from canonical.launchpad.scripts import execute_zcml_for_scripts


def get_class_name(cls):
    """Return the class name without its package prefix."""
    return cls.__name__.split('.')[-1]


def error_msg(error):
    """Convert an exception to a proper error.

    It make sure that the exception type is in the message and takes care
    of possible unicode conversion error.
    """
    try:
        return "%s: %s" % (get_class_name(error.__class__), str(error))
    except UnicodeEncodeError:
        return "UnicodeEncodeError in str(%s)" % error.__class__.__name__


class SampleDataVerification:
    """Runs various checks on sample data and report about them."""

    def __init__(self, dbname="launchpad_ftest_template", dbuser="launchpad",
                 table_filter=None, min_rows=10, only_summary=False):
        """Initialize the verification object.

        :param dbname: The database which contains the sample data to check.
        :param dbuser: The user to connect as.
        """
        self.txn = initZopeless(dbname=dbname, dbuser=dbuser)
        execute_zcml_for_scripts()
        self.classes_with_error = {}
        self.class_rows = {}
        self.table_filter = table_filter
        self.min_rows = min_rows
        self.only_summary = only_summary

    def findSQLBaseClasses(self):
        """Return an iterator over the classes in canonical.launchpad.database
        that extends SQLBase.
        """
        if self.table_filter:
            include_only_re = re.compile(self.table_filter)
        for class_name in dir(canonical.launchpad.database):
            if self.table_filter and not include_only_re.search(class_name):
                continue
            cls = getattr(canonical.launchpad.database, class_name)
            if inspect.isclass(cls) and issubclass(cls, SQLBase):
                yield cls

    def fetchTableRowsCount(self):
        """Fetch the number of rows of each tables.

        The count are stored in the table_rows_count attribute.
        """
        self.table_rows_count = {}
        for cls in self.findSQLBaseClasses():
            class_name = get_class_name(cls)
            try:
                self.table_rows_count[class_name] = cls.select().count()
            except ProgrammingError, error:
                self.classes_with_error[class_name] = str(error)
                # Transaction is borked, start another one.
                self.txn.begin()

    def checkSampleDataInterfaces(self):
        """Check that all sample data objects complies with the interfaces it
        declares.
        """
        self.validation_errors = {}
        self.broken_instances= {}
        for cls in self.findSQLBaseClasses():
            class_name = get_class_name(cls)
            if class_name in self.classes_with_error:
                continue
            try:
                for object in cls.select():
                    self.checkObjectInterfaces(object)
                    self.validateObjectSchemas(object)
            except ProgrammingError, error:
                self.classes_with_error[get_class_name(cls)] = str(error)
                # Transaction is borked, start another one.
                self.txn.begin()

    def checkObjectInterfaces(self, object):
        """Check that object provides every attributes in its declared interfaces.

        Collect errors in broken_instances dictionary attribute.
        """
        for interface in providedBy(object):
            interface_name = get_class_name(interface)
            try:
                result = verifyObject(interface, object)
            except BrokenImplementation, error:
                self.setInterfaceError(
                    interface, object, "missing attribute %s" % error.name)
            except BrokenMethodImplementation, error:
                self.setInterfaceError(
                     interface, object,
                    "invalid method %s: %s" % (error.method, error.mess))

    def setInterfaceError(self, interface, object, error_msg):
        """Store an error about an interface in the broken_instances dictionary

        The errors data structure looks like:

        {interface: {
            error_msg: {
                class_name: [instance_id...]}}}
        """
        interface_errors = self.broken_instances.setdefault(
            get_class_name(interface), {})
        classes_with_error = interface_errors.setdefault(error_msg, {})
        object_ids_with_error = classes_with_error.setdefault(
            get_class_name(object.__class__), [])
        object_ids_with_error.append(object.id)

    def validateObjectSchemas(self, object):
        """Check that object validates with the schemas it says it provides.

        Collect errors in validation_errors. Data structure format is
        {schema:
            [[class_name, object_id,
                [(field, error), ...]],
             ...]}
        """
        for schema in providedBy(object):
            field_errors = []
            for name in schema.names(all=True):
                description = schema[name]
                if not IField.providedBy(description):
                    continue
                try:
                    value = getattr(object, name)
                except AttributeError:
                    # This is an already reported verifyObject failures.
                    continue
                try:
                    description.validate(value)
                except ValidationError, error:
                    field_errors.append((name, error_msg(error)))
                except (KeyboardInterrupt, SystemExit):
                    # We should never catch KeyboardInterrupt or SystemExit.
                    raise
                except ProgrammingError, error:
                    field_errors.append((name, error_msg(error)))
                    # We need to restart the transaction after these errors.
                    self.txn.begin()
                except Exception, error:
                    # Exception usually indicates a deeper problem with
                    # the interface declaration or the validation code, than
                    # the expected ValidationError.
                    field_errors.append((name, error_msg(error)))
            if field_errors:
                schema_errors= self.validation_errors.setdefault(
                    get_class_name(schema), [])
                schema_errors.append([
                    get_class_name(object.__class__), object.id,
                    field_errors])

    def getShortTables(self):
        """Return a list of tables which have less rows than self.min_rows.

        :return: [(table, rows_count)...]
        """
        return [
            (table, rows_count)
            for table, rows_count in self.table_rows_count.items()
            if rows_count < self.min_rows]

    def reportShortTables(self):
        """Report about tables with less than self.min_rows."""
        short_tables = self.getShortTables()
        if not short_tables:
            print """All tables have more than %d rows!!!""" % self.min_rows
            return

        print dedent("""\
            %d Tables with less than %d rows
            --------------------------------""" % (
                len(short_tables), self.min_rows))
        for table, rows_count in sorted(short_tables):
            print "%-20s: %2d" % (table, rows_count)

    def reportErrors(self):
        """Report about classes with database error.

        This will usually be classes without a database table.
        """
        if not self.classes_with_error:
            return
        print dedent("""\
            Classes with database errors
            ----------------------------""")
        for class_name, error_msg in sorted(self.classes_with_error.items()):
            print "%-20s %s" % (class_name, error_msg)

    def reportInterfaceErrors(self):
        """Report objects failing the verifyObject and schema validation."""
        if not self.broken_instances:
            print "All sample data comply with its provided interfaces!!!"
            return
        print dedent("""\
            %d Interfaces with broken instances
            -----------------------------------""" % len(
                self.broken_instances))
        for interface, errors in sorted(
            self.broken_instances.items()):
            print "%-20s:" % interface
            for error_msg, classes_with_error in sorted(errors.items()):
                print "    %s:" % error_msg
                for class_name, object_ids in sorted(
                    classes_with_error.items()):
                    print "        %s: %s" % (
                        class_name, ", ".join([
                            str(id) for id in sorted(object_ids)]))

    def reportValidationErrors(self):
        """Report object that fails their validation."""
        if not self.validation_errors:
            print "All sample data pass validation!!!"
            return

        print dedent("""\
            %d Schemas with instances failing validation
            --------------------------------------------""" % len(
                self.validation_errors))
        for schema, instances in sorted(self.validation_errors.items()):
            print "%-20s (%d objects with errors):" % (schema, len(instances))
            for class_name, object_id, errors in sorted(instances):
                print "    <%s %s> (%d errors):" % (
                    class_name, object_id, len(errors))
                for field, error in sorted(errors):
                    print "        %s: %s" % (field, error)

    def reportSummary(self):
        """Only report the name of the classes with errors."""

        short_tables = dict(self.getShortTables())

        # Compute number of implementation error by classes.
        verify_errors_count = {}
        for interface_errors in self.broken_instances.values():
            for broken_classes in interface_errors.values():
                for class_name in broken_classes.keys():
                    verify_errors_count.setdefault(class_name, 0)
                    verify_errors_count[class_name] += 1

        # Compute number of instances with validation error.
        validation_errors_count = {}
        for instances in self.validation_errors.values():
            for class_name, object_id, errors in instances:
                validation_errors_count.setdefault(class_name, 0)
                validation_errors_count[class_name] += 1

        classes_with_errors = set(short_tables.keys())
        classes_with_errors.update(verify_errors_count.keys())
        classes_with_errors.update(validation_errors_count.keys())

        print dedent("""\
            %d Classes with errors:
            -----------------------""" % len(classes_with_errors))
        for class_name in sorted(classes_with_errors):
            errors = []
            if class_name in short_tables:
                errors.append('%d rows' % short_tables[class_name])
            if class_name in verify_errors_count:
                errors.append(
                    '%d verify errors' % verify_errors_count[class_name])
            if class_name in validation_errors_count:
                errors.append(
                    '%d validation errors' %
                        validation_errors_count[class_name])
            print "%s: %s" % (class_name, ", ".join(errors))

    def run(self):
        """Check and report on sample data."""
        self.fetchTableRowsCount()
        self.checkSampleDataInterfaces()
        print dedent("""\
            Verified %d content classes.
            ============================
            """ % len(self.table_rows_count))
        if self.only_summary:
            self.reportSummary()
        else:
            self.reportShortTables()
            print
            self.reportInterfaceErrors()
            print
            self.reportValidationErrors()
        print
        self.reportErrors()
        self.txn.abort()


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('-d', '--database', action="store", type="string",
                      default="launchpad_ftest_template",
                      help="Database to connect to for testing.")
    parser.add_option('-u', '--user', action="store", type="string",
                      default="launchpad",
                      help="Username to connect with.")
    parser.add_option('-i', '--table-filter', dest="table_filter",
                      action="store", type="string", default=None,
                      help="Limit classes to test using a regular expression.")
    parser.add_option('-m', '--min-rows', dest="min_rows",
                      action="store", type="int", default=10,
                      help="Minimum number of rows a table is expected to have.")
    parser.add_option('-s', '--summary',
                      action='store_true', dest="summary", default=False,
                      help=(
                        "Only report the name of the classes with "
                        "validation errors."))
    options, arguments = parser.parse_args()
    SampleDataVerification(
        dbname=options.database,
        dbuser=options.user,
        table_filter=options.table_filter,
        min_rows=options.min_rows,
        only_summary=options.summary).run()

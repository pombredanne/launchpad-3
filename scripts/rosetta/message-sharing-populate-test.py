#!/usr/bin/python -S
#
# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=W0403

"""Test Translation Message Sharing schema initializations.

This script verifies the results of the message-sharing-populate.py
one-off script.  It checks that all schema elements that were added for
translation message sharing were initialized correctly.

Run this after message-sharing-populate.py, but also occasionally
afterwards to ensure that the code that initializes the added schema
elements on new data is working correctly.

The new schema elements are not used yet.  Once they are, a next step is
to start unifying TranslationMessages that are common between
POTemplates.  When that happens, this script will start reporting errors
at points marked in the source below.  Change those points & run again!
"""

import _pythonpath

from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import execute_zcml_for_scripts


class SchemaElementsInitializationFailure(Exception):
    """Convenience exception class for errors found in our data."""
    pass


def check(query, error_message, expected_result=0):
    """Report error if `query` result does not match `expected_result`."""
    cur = cursor()
    cur.execute(query)
    result, = cur.fetchone()

    if result != expected_result:
        counts = "expected %s, found %s" % (expected_result, result)
        raise SchemaElementsInitializationFailure(
            "%s (%s)" % (error_message, counts))


def test_schema():
    """Test schema initializations."""
    cur = cursor()

    # Are all TranslationMessage.language fields initialized?
    query = """
        SELECT count(*)
        FROM TranslationMessage
        WHERE language IS NULL
       """
    check(query, "Found uninitialized TranslationMessage.language")

    # Are all TranslationMessages.potemplate fields initialized?
    # XXX JeroenVermeulen 2008-10-06 spec=message-sharing-migration:
    # potemplate will be allowed to be null later on, when we really
    # start sharing messages.  The field means "this message is specific
    # to this potemplate, rather than shared").  Remove this check then.
    query = """
        SELECT count(*)
        FROM TranslationMessage
        WHERE potemplate IS NULL OR language IS NULL
       """
    check(query, "Found uninitialized TranslationMessages.potemplate.")

    # Are all TranslationMessages linked to the right languages?
    query = """
        SELECT count(*)
        FROM TranslationMessage
        LEFT JOIN POFile ON POFile.id = TranslationMessage.pofile
        WHERE
            POFile.id IS NULL OR
            POFile.language <> TranslationMessage.language
        """
    check(query, "Found TranslationMessages with incorrect language.")

    # Do all POTMsgSets with nonzero sequence numbers have linking-table
    # entries linking them to their POTemplates?  (Zero sequence number
    # means "does not participate in this POTemplate," a wart that will
    # go away with this schema change)
    query = """
        SELECT count(*)
        FROM POTMsgSet
        LEFT JOIN TranslationTemplateItem AS i ON i.potmsgset = POTMsgSet.id
        WHERE POTMsgSet.sequence <> 0 AND i.id IS NULL
        """
    check(query, "Found unlinked POTMsgSets.")

    # Conversely, is the linking table free of unexpected rows?
    query = """
        SELECT count(*)
        FROM TranslationTemplateItem i
        LEFT JOIN POTMsgSet ON i.potmsgset = POTMsgSet.id
        WHERE POTMsgSet.id IS NULL or POTMsgSet.sequence = 0
        """
    check(query, "Found unexpected TranslationTemplateItem rows.")

    # Are all TranslationTemplateItems correct?
    query = """
        SELECT count(*)
        FROM POTMsgSet
        JOIN TranslationTemplateItem AS i ON i.potmsgset = POTMsgSet.id
        WHERE
            i.potemplate <> POTMsgSet.potemplate OR
            i.sequence <> POTMsgSet.sequence
        """
    check(query, "Found incorrect TranslationTemplateItem contents.")

    # Is each POTMsgSet linked to no more than one POTemplate?
    # XXX JeroenVermeulen 2008-10-06 spec=message-sharing-migration:
    # Once we start sharing messages across templates, this will become
    # a real m:n relationship between POTMsgSet and POTemplate.  At that
    # point, remove his check.
    query = """
        SELECT count(*)
        FROM (
            SELECT count(*)
            FROM TranslationTemplateItem
            GROUP BY potmsgset
            HAVING count(*) > 1
            ) AS shared_potmsgset
        """
    check(query, "Found shared POTMsgSets.")


if __name__ == '__main__':
    execute_zcml_for_scripts()
    test_schema()
    print "Done."

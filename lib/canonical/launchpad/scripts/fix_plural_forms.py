# Copyright 2007 Canonical Ltd. All rights reserved.

"""Functions for fixing mismatched plural form translations."""

__metaclass__ = type

__all__ = [
    'fix_plurals_in_all_pofiles',
    ]

import datetime
import os
import sys
import tempfile

from zope.component import getUtility

from sqlobject import SQLObjectNotFound

from canonical.launchpad.database.pofile import POFile
from canonical.launchpad.database.translationmessage import TranslationMessage
from canonical.database.sqlbase import sqlvalues, cursor
from canonical.launchpad.interfaces import (
    IDistributionSet, ILanguagePackSet, IVPOExportSet, LanguagePackType)
from canonical.launchpad.translationformat.gettext_po_parser import (
    POHeader, plural_form_mapper)

def get_mapping_for_pofile_plurals(pofile):
    """Check if POFile plural forms need fixing.

    Return a mapping if a plural form expression in PO file header doesn't
    match expected plural form expression for `pofile.language`, otherwise
    return False.
    """
    expected_plural_formula = pofile.language.pluralexpression
    used_plural_formula = POHeader(pofile.header).plural_form_expression
    if expected_plural_formula == used_plural_formula:
        return None
    else:
        forms_map = plural_form_mapper(expected_plural_formula,
                                       used_plural_formula)
        for key in forms_map:
            if forms_map[key] != key:
                return forms_map

        return None

def fix_pofile_plurals(pofile, logger, ztm):
    """Fix plural translations for PO files with mismatching headers."""
    plural_forms_mapping = get_mapping_for_pofile_plurals(pofile)
    logger.debug("Checking if PO file %d needs fixing" % pofile.id)
    if plural_forms_mapping is not None:
        logger.info("Fixing PO file %s" % pofile.title)
        pluralmessages = TranslationMessage.select("""
            POTMsgSet.id = TranslationMessage.potmsgset AND
            POTMsgSet.msgid_plural IS NOT NULL AND
            TranslationMessage.pofile = %s""" % sqlvalues(pofile),
            clauseTables=["POTMsgSet"])
        for message in pluralmessages:
            logger.debug("\tFixing translations for '%s'" % (
                message.potmsgset.singular_text))
            old_translations = [message.msgstr0, message.msgstr1,
                                message.msgstr2, message.msgstr3]
            message.msgstr0 = old_translations[plural_forms_mapping[0]]
            message.msgstr1 = old_translations[plural_forms_mapping[1]]
            message.msgstr2 = old_translations[plural_forms_mapping[2]]
            message.msgstr3 = old_translations[plural_forms_mapping[3]]

        # We also need to update the header so we don't try to re-do the
        # migration in the future.
        header = POHeader(pofile.header)
        header.plural_form_expression = pofile.language.pluralexpression
        header.has_plural_forms = True
        pofile.header = header.getRawContent()
        ztm.commit()

def fix_plurals_in_all_pofiles(ztm, logger):
    """Go through all PO files and fix plural forms if needed."""

    cur = cursor()
    cur.execute("""SELECT MAX(id) FROM POFile""")
    (max_pofile_id,) = cur.fetchall()[0]
    for pofile_id in range(1, max_pofile_id):
        try:
            pofile = POFile.get(pofile_id)
            fix_pofile_plurals(pofile, logger, ztm)
        except SQLObjectNotFound:
            pass


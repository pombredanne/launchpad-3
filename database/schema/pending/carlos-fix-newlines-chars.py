#!/usr/bin/env python
# Copyright 2006 Canonical Ltd. All rights reserved.

import _pythonpath

import sys
from optparse import OptionParser

from canonical.config import config
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.database import POMsgSet

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def fix_newlines(pomsgsets):
    """Fix the pomsgsets' translations newlines, if needed."""
    fixed_translations = []
    for pomsgset in pomsgsets:
        translations = {}
        owner = None
        if pomsgset.pofile.language.pluralforms is None:
            # We don't know the amount of plural forms this language has,
            # we assume there is just one of them.
            plural_forms = 1
        else:
            plural_forms = pomsgset.pofile.language.pluralforms

        for plural_form in range(plural_forms):
            # Get current translations.
            published = pomsgset.getActiveSubmission(plural_form)
            if published is None:
                # There is no published translation for this plural form.
                continue
            else:
                owner = published.person
                potranslation = published.potranslation
                translations[plural_form] = potranslation.translation
                fixed_translations.append(potranslation.id)
        # Submit the translation again so it's fixed if it's need.
        pomsgset.updateTranslationSet(owner, translations,
            pomsgset.isfuzzy, False, force_edition_rights=True)

        return fixed_translations


def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'rosetta-poimport')

    logger_object.debug('Starting the fixing process')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.rosetta.poimport.dbuser)

    # Get the list of IPOTranslation ids that have the '\r' char.
    cur = cursor()
    cur.execute("""
        SELECT id
        FROM POTranslation
        WHERE translation like '%\r%'
        """)
    translation_ids = cur.fetchall()
    translation_ids = [set[0] for set in translation_ids]
    logger_object.debug('There are %d translations to be checked' %
        len(translation_ids))

    # Get the list of IPOMsgIDs ids that have the '\r' char.
    cur = cursor()
    cur.execute("""
        SELECT id
        FROM POMsgID
        WHERE msgid LIKE '%\r%'
        """)
    msgid_ids = cur.fetchall()
    msgid_ids = [set[0] for set in msgid_ids]
    logger_object.debug('There are %d msgids to be checked' %
        len(msgid_ids))

    # Let's review first the entries that have the '\r' char as part of
    # the msgid. We are assuming here that the msgid_singular and
    # msgid_plural have the same kind of new lines so we only check the
    # singular ones.
    for id in msgid_ids:
        # Get all pomsgsets that use the given msgid.
        pomsgsets = POMsgSet.select("""
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgSet.primemsgid = %d
            """ % id, clauseTables=['POTMsgSet'])

        # Fix all translations associated with this msgid.
        fixed_translation_ids = fix_newlines(pomsgsets)

        for translation_id in fixed_translation_ids:
            if translation_id in translation_ids:
                # Remove this translation from the list of
                # translations to process as we are fixing it now atm.
                translation_ids.remove(translation_id)

    # Commit the transaction and store the changed entries.
    ztm.commit()

    logger_object.debug(
        'There are %d translations to be checked after msgids are done.' %
            len(translation_ids))

    for id in translation_ids:
        # Get all pomsgsets that use the given translations.
        pomsgsets = POMsgSet.select("""
            POSelection.activesubmission = POSubmission.id AND
            POSubmission.potranslation = %d AND
            POSubmission.pomsgset = POMsgSet.id
            """ % id, clauseTables=['POSelection', 'POSubmission'])

        # Fix all msgsets associated with this translation. Usually, the fix
        # is just leave it as '\n' because the msgid should not have the '\r'
        # char, we already processed all those.
        fix_newlines(pomsgsets)

    # Commit the transaction and store the changed entries.
    ztm.commit()

    logger_object.debug('Finished the fixing process')


if __name__ == '__main__':
    main(sys.argv)

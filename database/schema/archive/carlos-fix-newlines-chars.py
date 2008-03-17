#!/usr/bin/env python
# Copyright 2006 Canonical Ltd. All rights reserved.

import sys
from optparse import OptionParser

from canonical.config import config
from canonical.lp import initZopeless
from canonical.database.sqlbase import cursor, sqlvalues
from canonical.launchpad.scripts import (
    execute_zcml_for_scripts, logger, logger_options)
from canonical.launchpad.database import POMsgSet, POTMsgSet
from canonical.launchpad.interfaces import TranslationConstants

def parse_options(args):
    """Parse a set of command line options.

    Return an optparse.Values object.
    """
    parser = OptionParser()

    parser.add_option("-c", "--check", dest="check",
        default=False,
        action='store_true',
        help=("Whether the script should only check if there are broken"
            "entries.")
        )

    # Add the verbose/quiet options.
    logger_options(parser)

    (options, args) = parser.parse_args(args)

    return options

def normalize_new_lines(potmsgset, text, logger_object):
    """Stolen from IPOTMsgSet.normalize_new_lines we need extra code here for
    the migration."""

    msgid = potmsgset.primemsgid_.msgid
    # There are three different kinds of newlines:
    windows_style = '\r\n'
    mac_style = '\r'
    unix_style = '\n'
    # We need the stripped variables because a 'windows' style will be at
    # the same time a 'mac' and 'unix' style.
    stripped_text = text.replace(windows_style, '')
    stripped_msgid = msgid.replace(windows_style, '')

    # Get the style that uses the msgid.
    msgid_style = None
    if windows_style in msgid:
        msgid_style = windows_style

    if mac_style in stripped_msgid:
        if msgid_style is not None:
            logger_object.warn(
                "Broken msgid (%r), it's mixing different new line markers"
                    % msgid)
        msgid_style = mac_style

    if unix_style in stripped_msgid:
        if msgid_style is not None:
            logger_object.warn(
                "Broken msgid (%r), it's mixing different new line markers"
                    % msgid)
        msgid_style = unix_style

    # Get the style that uses the given text.
    text_style = None
    if windows_style in text:
        text_style = windows_style

    if mac_style in stripped_text:
        if text_style is not None:
            # Changed the style to the mac one so we only have one style.
            logger_object.warn(
                "Fixing text with multiple newline styles (%r)"
                    % text)
            text = text.replace(text_style, mac_style)
        text_style = mac_style

    if unix_style in stripped_text:
        if text_style is not None:
            # Changed the style to the unix one so we only have one style.
            logger_object.warn(
                "Fixing text with multiple newline styles (%r)"
                    % text)
            text = text.replace(text_style, unix_style)
        text_style = unix_style

    if msgid_style is None or text_style is None:
        # We don't need to do anything, the text is not changed.
        return text

    # Fix the newline chars.
    return text.replace(text_style, msgid_style)


def check_newlines(pomsgsets, logger_object):
    """Check the pomsgsets' translations newlines to match the msgid's ones.

    :arg pomsgsets: A set of IPOMsgSet to check.
    """
    processed_translations = []
    for pomsgset in pomsgsets:
        translations = {}
        if pomsgset.pofile.language.pluralforms is None:
            # We don't know the amount of plural forms this language has,
            # we assume there is just one of them.
            plural_forms = 1
        else:
            plural_forms = pomsgset.pofile.language.pluralforms

        for plural_form in range(plural_forms):
            # Get current translations.
            active = pomsgset.getActiveSubmission(plural_form)
            if active is None:
                # There is no active translation for this plural form.
                continue
            else:
                potranslation = active.potranslation
                translations[plural_form] = potranslation.translation
                processed_translations.append(potranslation.id)

        pomsgid = (
            pomsgset.potmsgset.getPOMsgIDs(
                )[TranslationConstants.SINGULAR_FORM])
        if u'\r' in pomsgid.msgid:
            # The msgid contains the u'\r' char.
            for translation in translations.itervalues():
                if u'\r' not in translation and u'\n' in translation:
                    # But the translation is ussing another style.
                    logger_object.warn(
                        "Newline styles doesn't match: msgid: %r, translation"
                        " %r" % (pomsgid.msgid, translation))
        elif u'\n' in pomsgid.msgid:
            # The msgid doesn't contain the u'\r' char but the u'\n'.
            for translation in translations.itervalues():
                if u'\n' not in translation and u'\r' in translation:
                    # But the translation is ussing another style.
                    logger_object.warn(
                        "Newline styles doesn't match: msgid: %r, translation"
                        " %r" % (pomsgid.msgid, translation))
        else:
            # The msgid doesn't have any style of newline char so we ignore
            # the check, the user is free to use whatever he wants.
            continue

    return processed_translations

def fix_newlines(pomsgsets, ztm, logger_object,
    assert_if_carriage_return_present=False):
    """Fix the pomsgsets' translations newlines, if needed.

    :arg pomsgsets: A set of IPOMsgSet to fix.
    :arg ztm: A transaction manager object.
    :arg assert_if_carriage_return_present: Check if there are u'\r' chars as
        part of the msgid.
    """
    fixed_translations = []
    for pomsgset in pomsgsets:
        # Check to be sure that the translations that we are checking don't
        # have a msgid with the u'\r' char.
        if assert_if_carriage_return_present:
            pomsgids = pomsgset.potmsgset.getPOMsgIDs()
            for pomsgid in pomsgids:
                assert u'\r' not in pomsgid.msgid, (
                    "The msgid (%r) has a u'\\r' char on it but it should not"
                    " be there!" % pomsgid.msgid)

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
            active = pomsgset.getActiveSubmission(plural_form)
            if active is None:
                # There is no active translation for this plural form.
                continue
            else:
                owner = active.person
                potranslation = active.potranslation
                translations[plural_form] = normalize_new_lines(
                    pomsgset.potmsgset, potranslation.translation,
                    logger_object)
                fixed_translations.append(potranslation.id)

        if translations:
            # Submit the translation again so it's fixed if it's need.
            pomsgset.updateTranslationSet(owner, translations,
                pomsgset.isfuzzy, False, force_edition_rights=True)

        # Commit the transaction and store the changed entries.
        ztm.commit()

    return fixed_translations


def main(argv):
    options = parse_options(argv[1:])

    # Get the global logger for this task.
    logger_object = logger(options, 'rosetta-poimport')

    logger_object.info('Starting the fixing process')

    # Setup zcml machinery to be able to use getUtility
    execute_zcml_for_scripts()
    ztm = initZopeless(dbuser=config.poimport.dbuser)

    # Get the list of IPOTranslation ids that have the u'\r' char.
    cur = cursor()
    cur.execute("""
        SELECT id
        FROM POTranslation
        WHERE translation like '%\r%'
        """)
    translation_ids = cur.fetchall()
    translation_ids = [set_entry[0] for set_entry in translation_ids]
    logger_object.info('There are %d translations to be checked' %
        len(translation_ids))

    # Get the list of IPOMsgIDs ids that have the u'\r' char.
    cur = cursor()
    cur.execute("""
        SELECT id
        FROM POMsgID
        WHERE msgid LIKE '%\r%'
        """)
    msgid_ids = cur.fetchall()
    msgid_ids = [set_entry[0] for set_entry in msgid_ids]
    logger_object.info('There are %d msgids to be checked' %
        len(msgid_ids))

    # Let's review first the entries that have the u'\r' char as part of
    # the msgid.
    for id in msgid_ids:
        # Get all potmsgsets that use the given msgid.
        potmsgsets = POTMsgSet.select("""
            POMsgIDSighting.pomsgid = %s AND
            POMsgIDSighting.inlastrevision = TRUE AND
            POMsgIDSighting.potmsgset = POTMsgSet.id
            """ % sqlvalues(id), clauseTables=['POMsgIDSighting'])

        for potmsgset in potmsgsets:
            # Sanity check for the input we got from the applications.
            pomsgids = potmsgset.getPOMsgIDs()
            singular = pomsgids[TranslationConstants.SINGULAR_FORM]
            if pomsgids.count() > 1:
                plural = pomsgids[TranslationConstants.PLURAL_FORM]
            else:
                # It doesn't have a plural form, ignore this check
                continue

            if (('\r' in singular.msgid and '\r' not in plural.msgid) or
                ('\r' not in singular.msgid and '\r' in plural.msgid)):
                logger_object.warning(
                    "The singular and plural forms don't have the same"
                    " newline style.\nsingular: %r\n plural: %r\nWe found"
                    " this on %s" % (singular.msgid, plural.msgid,
                        potmsgset.potemplate.title))

        # Get all pomsgsets that use the given msgid.
        pomsgsets = POMsgSet.select("""
            POMsgSet.potmsgset = POTMsgSet.id AND
            POTMsgset.primemsgid = %s
            """ % sqlvalues(id), clauseTables=['POTMsgSet'])

        if options.check:
            # Only check for broken entries
            processed_translation_ids = check_newlines(
                pomsgsets, logger_object)
        else:
            # Fix all translations associated with this msgid.
            processed_translation_ids = fix_newlines(
                pomsgsets, ztm, logger_object)

        for translation_id in processed_translation_ids:
            if translation_id in translation_ids:
                # Remove this translation from the list of
                # translations to process as we are fixing it now atm.
                translation_ids.remove(translation_id)

    logger_object.info(
        'There are %d translations to be checked after msgids are done.' %
            len(translation_ids))

    for id in translation_ids:
        # Get all pomsgsets that use the given translations.
        pomsgsets = POMsgSet.select("""
            POSelection.activesubmission = POSubmission.id AND
            POSubmission.potranslation = %d AND
            POSubmission.pomsgset = POMsgSet.id
            """ % id, clauseTables=['POSelection', 'POSubmission'])

        if options.check:
            # Only check for broken entries
            check_newlines(pomsgsets, logger_object)
        else:
            # Fix all msgsets associated with this translation. Usually, the
            # fix is just leave it as u'\n' because the msgid should not have
            # the u'\r' char, we already processed all those.
            fix_newlines(pomsgsets, ztm, logger_object,
                assert_if_carriage_return_present=True)

    logger_object.info('Finished the fixing process')


if __name__ == '__main__':
    main(sys.argv)

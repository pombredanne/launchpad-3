# Copyright 2008 Canonical Ltd. All rights reserved.

"""Migrate KDE POTemplates to native support for plural forms and context ."""

__metaclass__ = type

__all__ = [
    'migrate_potemplates',
    ]

from sqlobject import SQLObjectNotFound
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.potranslation import POTranslation
from canonical.launchpad.database.translationmessage import TranslationMessage

from canonical.launchpad.interfaces import (
    TranslationConstants, TranslationFileFormat)


def getOrCreatePOMsgID(msgid):
    try:
        pomsgid = POMsgID.byMsgid(msgid)
    except SQLObjectNotFound:
        pomsgid = POMsgID(msgid=msgid)
    return pomsgid

def get_potranslations(translations):
    potranslations = {}
    for index, translation in enumerate(translations):
        if translation != '':
            potranslations[index] = (
                POTranslation.getOrCreateTranslation(translation))
        else:
            potranslations[index] = None
    for index in range(len(potranslations),
                       TranslationConstants.MAX_PLURAL_FORMS):
        potranslations[index] = None
    return potranslations


def find_existing_translation(potmsgset, pofile, potranslations):
    unprotected_potmsgset = removeSecurityProxy(potmsgset)
    existing_message = (
        unprotected_potmsgset._findTranslationMessage(
            pofile, potranslations, TranslationConstants.MAX_PLURAL_FORMS))
    return existing_message


def migrate_translations_for_potmsgset(potmsgset, from_potmsgset,
                                       logger, ztm):
    """Migrate translations from `from_potmsgset` to `potmsgset`.

    `from_potmsgset` is an old, unmigrated POTMsgSet we are migrating
    translations from.  Translations are migrated to native context
    and plural forms support along the way.

    `from_potmsgset` and `potmsgset` might be the same, which happens when
    we are migrating templates as well.
    """
    messages = TranslationMessage.select(
        "potmsgset = %s" % sqlvalues(from_potmsgset))
    logger.debug("Migrating %d translations for '%s'..." % (
        messages.count(), potmsgset.singular_text))
    for message in messages:
        msgstrs = message.translations
        # Let's see if translations have only the first plural
        # form defined: if they do, then they need migration.
        single_string = False
        if len(msgstrs) > 0 and msgstrs[0] is not None:
            single_string = True
            for msgstr in msgstrs[1:]:
                if msgstr is not None:
                    single_string = False

        if single_string:
            translations = msgstrs[0].split('\n')

            # If there's only a single plural form, no need to change
            # anything.  If POTMsgSets are different, we still need
            # to move the translation from one to the other.
            if len(translations) == 1 and potmsgset == from_potmsgset:
                continue

            # If there is an existing TranslationMessage with
            # these translations, re-use that and remove this one,
            # otherwise modify this one in-place.
            potranslations = get_potranslations(translations)
            existing_message = find_existing_translation(
                potmsgset, message.pofile, potranslations)
            if existing_message:
                if existing_message.id != message.id:
                    # Only transfer is_current and is_imported
                    # properties to an existing translation.
                    if message.is_current:
                        existing_message.is_current = True
                    if message.is_imported:
                        existing_message.is_imported = True
                    # And remove the current message.
                    message.destroySelf()
            else:
                # Modify `message` in-place.
                message.msgstr0 = potranslations[0]
                message.msgstr1 = potranslations[1]
                message.msgstr2 = potranslations[2]
                message.msgstr3 = potranslations[3]
                message.msgstr4 = potranslations[4]
                message.msgstr5 = potranslations[5]
                if potmsgset.id != from_potmsgset.id:
                    # Point TranslationMessage to a new POTMsgSet.
                    # To avoid hitting constraints, first unset
                    # the is_current and is_imported flags, and
                    # restore them afterwards.
                    stored_is_current = message.is_current
                    stored_is_imported = message.is_imported
                    message.is_current = False
                    message.is_imported = False
                    message.potmsgset = potmsgset
                    message.sync()
                    message.is_current = stored_is_current
                    message.is_imported = stored_is_imported
                    message.sync()


def migrate_kde_potemplate_translations(potemplate, logger, ztm):
    assert potemplate.source_file_format == TranslationFileFormat.KDEPO, (
        "Trying to move translations for non-KDEPO template.")
    cur = cursor()
    cur.execute("""
      SELECT old_msg.id, new_msg.id
        FROM POTMsgSet AS old_msg, POMsgID AS old_msgid,
             POTMsgSet AS new_msg, POMsgID AS singular, POMsgID AS plural
        WHERE
          -- they are both from this template
          old_msg.potemplate=%s AND
          new_msg.potemplate=old_msg.potemplate AND
          -- old one is obsolete
          old_msg.sequence=0 AND
          -- old POTMsgSet has a singular form of the form '_n:...',
          -- and no plural form
          old_msg.msgid_singular=old_msgid.id AND
          old_msg.msgid_plural IS NULL AND
          old_msgid.msgid LIKE E'\\\\_n: %%' AND
          -- and new POTMsgSet has singular and plural which when joined
          -- give the old plural form
          new_msg.msgid_singular=singular.id AND
          new_msg.msgid_plural=plural.id AND
          '_n: ' || singular.msgid || E'\\n' || plural.msgid = old_msgid.msgid
          """ % sqlvalues(potemplate))
    plural_potmsgsets = cur.fetchall()

    logger.info("Migrating translations for %d plural POTMsgSets..." % (
        len(plural_potmsgsets)))
    for old_potmsgset_id, new_potmsgset_id in plural_potmsgsets:
        old_potmsgset = POTMsgSet.get(old_potmsgset_id)
        new_potmsgset = POTMsgSet.get(new_potmsgset_id)
        migrate_translations_for_potmsgset(new_potmsgset, old_potmsgset,
                                           logger, ztm)

    cur.execute("""
      SELECT old_msg.id, new_msg.id
        FROM POTMsgSet AS old_msg, POMsgID AS old_msgid,
             POTMsgSet AS new_msg, POMsgID AS new_msgid
        WHERE
          -- they are both from this template
          old_msg.potemplate=%s AND
          new_msg.potemplate=old_msg.potemplate AND
          -- old one is obsolete
          old_msg.sequence=0 AND
          -- old POTMsgSet has a singular form of the form '_:...',
          -- and no plural form
          old_msg.msgid_singular=old_msgid.id AND
          old_msg.msgid_plural IS NULL AND
          old_msgid.msgid LIKE E'\\\\_: %%' AND
          -- and new POTMsgSet has singular and context which when joined
          -- give the old contextual message
          new_msg.msgid_singular=new_msgid.id AND
          '_: ' || new_msg.context || E'\\n' || new_msgid.msgid = old_msgid.msgid
          """ % sqlvalues(potemplate))

    plural_potmsgsets = cur.fetchall()

    logger.info("Migrating translations for %d context POTMsgSets..." % (
        len(plural_potmsgsets)))
    for old_potmsgset_id, new_potmsgset_id in plural_potmsgsets:
        old_potmsgset = POTMsgSet.get(old_potmsgset_id)
        new_potmsgset = POTMsgSet.get(new_potmsgset_id)
        messages = TranslationMessage.select(
            "potmsgset=%s" % sqlvalues(old_potmsgset))
        logger.debug(
            "Moving %d context translations from POTMsgSet %d to %d..." % (
                messages.count(), old_potmsgset_id, new_potmsgset_id))
        migrate_translations_for_potmsgset(new_potmsgset, old_potmsgset,
                                           logger, ztm)

    ztm.commit()


def existing_potmsgset(potemplate, msgid_singular, context):
    clauses = ['potemplate=%s' % sqlvalues(potemplate),
               'msgid_singular=%s' % sqlvalues(msgid_singular)]
    if context is None:
        clauses.append("context IS NULL")
    else:
        clauses.append("context=%s" % sqlvalues(context))

    return POTMsgSet.selectOne(" AND ".join(clauses))


def migrate_potemplate(potemplate, logger, ztm):
    """Migrate PO templates to KDEPO format if needed."""

    plural_prefix = u'_n: '
    context_prefix = u'_: '

    assert(potemplate.source_file_format == TranslationFileFormat.PO)

    potmsgsets = POTMsgSet.select("""
      POTMsgSet.potemplate = %s AND
      POTMsgSet.msgid_singular=POMsgID.id AND
      POTMsgSet.msgid_plural IS NULL AND
      (POMsgID.msgid LIKE E'\\\\_n: %%' OR POMsgID.msgid LIKE E'\\\\_: %%')
      """ % sqlvalues(potemplate),
      clauseTables=['POMsgID'])

    logger.debug("Fixing %d POTMsgSets..." % potmsgsets.count())

    # We go potmsgset by potmsgset because it's easier to preserve
    # correctness.  It'd be faster to go through translation messages
    # but then we'd be fixing potmsgsets after fixing translation messages.
    for potmsgset in potmsgsets:
        msgid = potmsgset.singular_text
        fix_plurals = fix_context = False

        # Detect plural form and context messages: use the same
        # logic as in translationformat/kde_po_importer.py.
        if msgid.startswith(plural_prefix) and '\n' in msgid:
            # This is a KDE plural form.
            singular_text, plural_text = (
                msgid[len(plural_prefix):].split('\n', 1))

            msgid_singular = getOrCreatePOMsgID(singular_text)

            if existing_potmsgset(potemplate, msgid_singular, None):
                logger.warn("POTMsgSet %d conflicts with another one." % (
                    potmsgset.id))
            else:
                potmsgset.msgid_singular = msgid_singular
                potmsgset.msgid_plural = getOrCreatePOMsgID(plural_text)
                potmsgset.sync()
                fix_plurals = True
        elif msgid.startswith(context_prefix) and '\n' in msgid:
            # This is a KDE context message: it needs no fixing apart
            # from changing msgid_singular.
            context, singular_text = (
                msgid[len(context_prefix):].split('\n', 1))
            msgid_singular = getOrCreatePOMsgID(singular_text)

            if existing_potmsgset(potemplate, msgid_singular, context):
                logger.warn("POTMsgSet %d conflicts with another one." % (
                    potmsgset.id))
            else:
                potmsgset.context = context
                potmsgset.msgid_singular = msgid_singular
                potmsgset.sync()
                fix_context = True
        else:
            # Other messages here are the ones which begin like
            # context or plural form messages, but are actually neither.
            pass

        if fix_plurals:
            # Fix translations for this potmsgset.
            migrate_translations_for_potmsgset(potmsgset, potmsgset,
                                               logger, ztm)

    potemplate.source_file_format = TranslationFileFormat.KDEPO
    # Commit a PO template one by one.
    ztm.commit()


def migrate_translations_for_kdepo_templates(ztm, logger):
    """Migrate translations for already re-imported KDE PO templates."""
    potemplates = POTemplate.select("""
    source_file_format=%s AND
    POTemplate.id IN
        (SELECT DISTINCT potemplate
          FROM POTMsgSet
          WHERE POTMsgSet.potemplate = POTemplate.id AND
                (POTMsgSet.msgid_plural IS NOT NULL OR
                 POTMsgSet.context IS NOT NULL))
      """ % sqlvalues(TranslationFileFormat.KDEPO))

    count = potemplates.count()
    index = 0
    for potemplate in potemplates:
        index += 1
        logger.info("Migrating translations for KDE POTemplate %s [%d/%d]" % (
            potemplate.displayname, index, count))
        migrate_kde_potemplate_translations(potemplate, logger, ztm)


def migrate_unmigrated_templates_to_kdepo(ztm, logger):
    """Go through all non-KDE PO templates and migrate to KDEPO as needed."""

    potemplates = POTemplate.select("""
    source_file_format=%s AND
    POTemplate.id IN
        (SELECT DISTINCT potemplate
          FROM POTMsgSet
          JOIN POMsgID ON POMsgID.id = POTMsgSet.msgid_singular
          WHERE POTMsgSet.potemplate = POTemplate.id AND
                POTMsgSet.msgid_plural IS NULL AND
                (POMsgID.msgid LIKE E'\\\\_n: %%' OR
                 POMsgID.msgid LIKE E'\\\\_: %%'))
      """ % sqlvalues(TranslationFileFormat.PO))

    count = potemplates.count()
    index = 0
    for potemplate in potemplates:
        index += 1
        logger.info("Migrating POTemplate %s [%d/%d]" % (
            potemplate.displayname, index, count))
        migrate_potemplate(potemplate, logger, ztm)


def migrate_potemplates(ztm, logger):
    migrate_translations_for_kdepo_templates(ztm, logger)
    migrate_unmigrated_templates_to_kdepo(ztm, logger)

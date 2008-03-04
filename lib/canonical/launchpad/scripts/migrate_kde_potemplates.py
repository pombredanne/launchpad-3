# Copyright 2007 Canonical Ltd. All rights reserved.

"""Migrate KDE POTemplates to native support for plural forms and context ."""

__metaclass__ = type

__all__ = [
    'migrate_potemplates',
    ]

from sqlobject import SQLObjectNotFound
from zope.security.proxy import removeSecurityProxy

from canonical.database.sqlbase import sqlvalues

from canonical.launchpad.database.pomsgid import POMsgID
from canonical.launchpad.database.potemplate import POTemplate
from canonical.launchpad.database.potmsgset import POTMsgSet
from canonical.launchpad.database.potranslation import POTranslation
from canonical.launchpad.database.translationmessage import TranslationMessage

from canonical.launchpad.interfaces import TranslationFileFormat

def getOrCreatePOMsgID(msgid):
    try:
        pomsgid = POMsgID.byMsgid(msgid)
    except SQLObjectNotFound:
        pomsgid = POMsgID(msgid=msgid)
    return pomsgid

def migrate_potemplate(potemplate, logger, ztm):
    """Fix plural translations for PO files with mismatching headers."""

    plural_prefix = u'_n: '
    context_prefix = u'_: '

    assert(potemplate.source_file_format == TranslationFileFormat.PO)

    potmsgsets = POTMsgSet.select("""
      POTMsgSet.potemplate = %s AND
      POTMsgSet.msgid_singular=POMsgID.id AND
      (POMsgID.msgid LIKE '_n: %%' OR POMsgID.msgid LIKE '_: %%')
      """ % sqlvalues(potemplate),
      clauseTables=['POMsgID'])

    logger.info("Fixing %d POTMsgSets..." % potmsgsets.count())

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
            singular_text, plural_text = msgid[len(plural_prefix):].split(
                '\n')

            potmsgset.msgid_singular = getOrCreatePOMsgID(singular_text)
            potmsgset.msgid_plural = getOrCreatePOMsgID(plural_text)
            fix_plurals = True
        elif msgid.startswith(context_prefix) and '\n' in msgid:
            # This is a KDE context message: it needs no fixing apart
            # from changing msgid_singular.
            context, singular_text = (
                msgid[len(context_prefix):].split('\n', 1))
            potmsgset.msgid_singular = getOrCreatePOMsgID(singular_text)
            potmsgset.context = context
            fix_context = True
        else:
            # Other messages here are the ones which begin like
            # context or plural form messages, but are actually neither.
            pass

        if fix_plurals:
            # Fix translations for this potmsgset as well.
            messages = TranslationMessage.select(
                "potmsgset=%s" % sqlvalues(potmsgset))
            logger.info("Fixing %d TranslationMessages..." % messages.count())
            for message in messages:
                msgstrs = message.translations
                if len(msgstrs) > 0:
                    translations = msgstrs[0].split('\n')
                    # If there is an existing TranslationMessage with
                    # these translations, re-use that and remove this one,
                    # otherwise modify this one in-place.

                    unprotected_potmsgset = removeSecurityProxy(potmsgset)
                    potranslations = {}
                    for index in range(len(translations)):
                        if translations != '':
                            potranslations[index] = (
                                POTranslation.getOrCreateTranslation(
                                    translations[index]))
                        else:
                            potranslations[index] = None
                    if len(potranslations) < 4:
                        for index in range(len(potranslations), 4):
                            potranslations[index] = None
                    existing_message = (
                        unprotected_potmsgset._findTranslationMessage(
                            message.pofile, potranslations, 4))
                    if existing_message:
                        # Only transfer is_current and is_imported
                        # properties to an existing translation.
                        if existing_message != message:
                            if message.is_current:
                                existing_message.is_current = True
                            if message.is_imported:
                                existing_message.is_imported = True
                            # And remove the current message.
                            message.destroySelf()
                    else:
                        # Modify `message` in-place.
                        message.msgstr0 =  potranslations[0]
                        message.msgstr1 =  potranslations[1]
                        message.msgstr2 =  potranslations[2]
                        message.msgstr3 =  potranslations[3]


    potemplate.source_file_format = TranslationFileFormat.KDEPO
    # Commit a PO template one by one.
    ztm.commit()


def migrate_potemplates(ztm, logger):
    """Go through all non-KDE PO templates and migrate to KDEPO as needed."""

    potemplates = POTemplate.select("""source_file_format=%s AND
    POTemplate.id IN
        (SELECT potemplate
          FROM POTMsgSet
          JOIN POMsgID ON POMsgID.id = POTMsgSet.msgid_singular
          WHERE POTMsgSet.potemplate = POTemplate.id AND
                POTMsgSet.msgid_plural IS NULL AND
                (POMsgID.msgid LIKE '_n: %%' OR POMsgID.msgid LIKE '_: %%')
          LIMIT 1)
      """ % sqlvalues(TranslationFileFormat.PO),
      clauseTables=['POTMsgSet', 'POMsgID'],
      distinct=True)

    count = potemplates.count()
    index = 0
    for potemplate in potemplates:
        index += 1
        logger.info("Migrating POTemplate %s [%d/%d]" % (
            potemplate.displayname, index, count))
        migrate_potemplate(potemplate, logger, ztm)

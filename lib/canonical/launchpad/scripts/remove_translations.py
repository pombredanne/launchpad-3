# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Remove specific translation messages from the database."""

__metaclass__ = type
__all__ = [
    'check_constraints_safety',
    'remove_translations',
    ]

from canonical.database.sqlbase import cursor, sqlvalues


def is_nonempty_list(list_option):
    """Is list_option a non-empty a nonempty list of option values?"""
    return list_option is not None and len(list_option) > 0


def is_nonempty_string(string_option):
    """Is string_option a non-empty option value?"""
    return string_option is not None and string_option != ''


def check_constraints_safety(options):
    """Are these options to the deletion script sufficiently safe?
    
    :param options: an object encapsulating options to the deletion
        script.
    :return: Boolean approval and output message.  All disapprovals come
        with an explanation; some approvals come with an informational
        message.
    """
    if is_nonempty_list(options.ids):
        return (True, None)
    if is_nonempty_string(options.submitter):
        return (True, None)
    if is_nonempty_string(options.reviewer):
        return (True, None)

    forced = options.force
    if is_nonempty_string(options.potemplate) and forced:
        return (
            True,
            "Safety override in effect.  Deleting translations for template "
            "%s." % options.potemplate)

    return (
        False,
        "Refusing unsafe deletion.  Use matching options to constrain "
        "deletion to a safe subset.")


def compose_language_match(language_code):
    """Compose SQL condition for matching a language in the deletion query.

    :param: Language code to match.  May include a variant.
    :return: SQL condition in string form.
    """
    if '@' in language_code:
        language, variant = language_code.split('@')
    else:
        language = language_code
        variant = None

    language_conditions = ['Language.code = %s' % sqlvalues(language)]
    if variant is None:
        language_conditions.append('POFile.variant IS NULL')
    else:
        language_conditions.append('POFile.variant = %s' % sqlvalues(variant))
    return ' AND '.join(language_conditions)


def add_bool_match(conditions, expression, match_value):
    """Add match for tri-state Boolean to SQL conditions.

    :param conditions: Set of SQL condition clauses to add to.
    :param expression: Variable or other SQL expression to match on.
    :param match_value: If given, the Boolean value to match.  If left
        as None, no condition is added.
    """
    if match_value is None:
        return

    if match_value:
        match = expression
    else:
        match = 'NOT (%s)' % expression
    conditions.add(match)


def remove_translations(logger=None, submitter=None, reviewer=None, ids=None,
                        potemplate=None, language_code=None,
                        spare_language_code=False, is_current=None,
                        is_imported=None, msgid_singular=None, origin=None):
    """Remove specified translation messages.

    :param logger: Optional logger to write output to.
    :param submitter: Delete only messages submitted by this person.
    :param reviewer: Delete only messages reviewed by this person.
    :param ids: Delete only messages with these `TranslationMessage` ids.
    :param potemplate: Delete only messages in this template.
    :param language_code: Language code.  Depending on `spare_language`,
        either delete messages in this language or spare messages in this
        language that would otherwise be deleted.
    :param spare_language_code: Whether to spare (True) or delete (False)
        messages in this language.
    :param is_current: Delete only messages with this is_current value.
    :param is_imported: Delete only messages with this is_imported value.
    :param msgid_singular: Delete only messages with this singular msgid.
    :param origin: Delete only messages with this `TranslationOrigin` code.

    :return: Number of messages deleted.
    """
    joins = set()
    conditions = set()
    if submitter is not None:
        conditions.add(
            'TranslationMessage.submitter = %s' % sqlvalues(submitter))
    if reviewer is not None:
        conditions.add(
            'TranslationMessage.reviewer = %s' % sqlvalues(reviewer))
    if ids is not None:
        conditions.add('TranslationMessage.id IN %s' % sqlvalues(ids))
    if potemplate is not None:
        joins.add('POTMsgSet')
        conditions.add('POTMsgSet.id = TranslationMessage.potmsgset')
        conditions.add('POTMsgSet.potemplate = %s' % sqlvalues(potemplate))

    if language_code is not None:
        joins.add('POFile')
        conditions.add('POFile.id = TranslationMessage.pofile')
        joins.add('Language')
        conditions.add('Language.id = POFile.language')
        language_match = compose_language_match(language_code)
        if spare_language_code:
            conditions.add('NOT (%s)' % language_match)
        else:
            conditions.add(language_match)

    add_bool_match(conditions, 'TranslationMessage.is_current', is_current)
    add_bool_match(conditions, 'TranslationMessage.is_imported', is_imported)

    if msgid_singular is not None:
        joins.add('POTMsgSet')
        conditions.add('POTMsgSet.id = TranslationMessage.potmsgset')
        joins.add('POMsgID')
        conditions.add('POMsgID.id = POTMsgSet.msgid_singular')
        conditions.add('POMsgID.msgid = %s' % sqlvalues(msgid_singular))

    if origin is not None:
        conditions.add('TranslationMessage.origin = %s' % sqlvalues(origin))

    assert len(conditions) > 0, "That would delete ALL translations, maniac!"

    if len(joins) > 0:
        using_clause = 'USING %s' % ', '.join(joins)
    else:
        using_clause = ''

    deletion_query = """
        DELETE FROM TranslationMessage
        %s
        WHERE
            %s
        """ % (using_clause, ' AND\n    '.join(conditions))

    if logger is not None:
        logger.debug("Executing SQL: %s" % deletion_query)

    cur = cursor()
    cur.execute(deletion_query)
    rows_deleted = cur.rowcount
    if logger is not None:
        if rows_deleted > 0:
            logger.info("Deleting %d message(s)." % rows_deleted)
        else:
            logger.warn("No rows match; not deleting anything.")

    return rows_deleted

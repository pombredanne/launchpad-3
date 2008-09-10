# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Remove specific translation messages from the database."""

__metaclass__ = type
__all__ = [
    'check_constraints_safety',
    'check_removal_options',
    'normalize_removal_options',
    'remove_translations',
    ]

from zope.component import getUtility

from canonical.database.sqlbase import cursor, sqlvalues

from canonical.launchpad.interfaces import (
    IPersonSet, RosettaTranslationOrigin)


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


def get_person_id(name):
    """Look up person by name."""
    person = getUtility(IPersonSet).getByName(name)
    if person is None:
        return None
    return person.id


def get_origin(name):
    """Look up `RosettaTranslationOrigin` by name."""
    return getattr(RosettaTranslationOrigin, name).value


def get_id(identifier, lookup_function=None):
    """Look up id of object identified by a string.

    :param identifier: String identifying an object.  If entirely
        numeric, taken as id.  Otherwise, passed to lookup_function.
    :param lookup_function: Callback that will take `identifier` as
        its argument and return a numeric object id.  If no object
        has the given identifier, may raise an exception or return
        None.
    :return: Numeric object id, or None if no identifier is given.
    """
    if identifier is None or identifier == '':
        return None
    if isinstance(identifier, int):
        return identifier
    if identifier.isdigit():
        return int(identifier)
    if lookup_function is None:
        raise ValueError("Expected numeric id, got '%s'." % identifier)
    else:
        result = lookup_function(identifier)
    if result is None:
        raise LookupError("'%s' not found." % identifier)
    return result


def get_bool(string_value):
    """Convert option value string_value to bool representation."""
    if string_value is None:
        return None
    string_value = string_value.lower()
    bool_representations = {
        'true': True,
        '1': True,
        'false': False,
        '0': False,
        }

    if string_value not in bool_representations:
        raise ValueError("Invalid boolean value: %s" % string_value)

    return bool_representations[string_value]


def normalize_removal_options(options):
    """Normalize bundle of options for remove-translations-by.

    Makes sure numeric or boolean options are converted from the string
    representation that `LaunchpadScript` will pass us.
    """
    options.submitter = get_id(options.submitter, get_person_id)
    options.reviewer = get_id(options.reviewer, get_person_id)
    if options.ids is not None:
        options.ids = [get_id(message) for message in options.ids]
    options.potemplate = get_id(options.potemplate)
    options.origin = get_id(options.origin, get_origin)
    options.is_current = get_bool(options.is_current)
    options.is_imported = get_bool(options.is_imported)


def check_option_type(options, option_name, option_type):
    """Check that option value is of given type, or None."""
    option = getattr(options, option_name)
    if option is not None and not isinstance(option, option_type):
        raise ValueError(
            "Wrong argument type for %s: expected %s, got %s." % (
                option_name, option_type.__name__, option.__class__.__name__))


def check_removal_options(options):
    """Check options to remove-translations-by, after normalization."""
    option_types = {
        'submitter': int,
        'reviewer': int,
        'ids': list,
        'potemplate': int,
        'language': basestring,
        'not_language': bool,
        'is_current': bool,
        'is_imported': bool,
        'msgid': basestring,
        'origin': int,
        'force': bool,
        }
    for option, expected_type in option_types.items():
        check_option_type(options, option, expected_type)


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
                        not_language=False, is_current=None, is_imported=None,
                        msgid_singular=None, origin=None):
    """Remove specified translation messages.

    :param logger: Optional logger to write output to.
    :param submitter: Delete only messages submitted by this person.
    :param reviewer: Delete only messages reviewed by this person.
    :param ids: Delete only messages with these `TranslationMessage` ids.
    :param potemplate: Delete only messages in this template.
    :param language_code: Language code.  Depending on `not_language`,
        either delete messages in this language or spare messages in this
        language that would otherwise be deleted.
    :param not_language: Whether to spare (True) or delete (False)
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
        if not_language:
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

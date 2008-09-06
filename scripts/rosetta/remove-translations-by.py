#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import logging

import _pythonpath

from zope.component import getUtility

from canonical.launchpad.interfaces import (
    IPersonSet, RosettaTranslationOrigin)
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.launchpad.scripts.remove_translations import (
    check_constraints_safety, remove_translations)


def get_person(name):
    """Look up person by name."""
    person = getUtility(IPersonSet).getByName(name)
    if person is None:
        return None
    return person.id


def get_origin(name):
    """Look up `RosettaTranslationOrigin` by name."""
    return getattr(RosettaTranslationOrigin, name).value


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


class RemoveTranslations(LaunchpadScript):
    """Remove specific `TranslationMessage`s from the database.

    The script accepts a wide range of options to specify exactly which
    messages need deleting.  It will refuse to run if the options are so
    non-specific that the command is more likely to be a mistake than a
    valid use case.  In borderline cases, it may be persuaded to run
    using a "force" option.
    """

    description = "Delete matching translation messages from the database."
    loglevel = logging.INFO

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            '-s', '--submitter', action='store', dest='submitter',
            help="Submitter match: delete only messages with this submitter.")
        self.parser.add_option(
            '-r', '--reviewer', action='store', dest='reviewer',
            help="Reviewer match: delete only messages with this reviewer.")
        self.parser.add_option(
            '-i', '--id', action='append', dest='ids',
            help="ID of message to delete.  May be specified multiple times.")
        self.parser.add_option(
            '-p', '--potemplate', action='store', dest='potemplate',
            help="Template id match.  Delete only messages in this template.")
        self.parser.add_option(
            '-l', '--language', action='store', dest='language',
            help="Language match.  Deletes (default) or spares (with -L) "
                 "messages in this language.")
        self.parser.add_option(
            '-L', '--not-language', action='store_const', const=True,
            dest='not_language',
            help="Invert language match: spare messages in given language.")
        self.parser.add_option(
            '-C', '--is-current', action='store', dest='is_current',
            help="Match on is_current value (True or False).")
        self.parser.add_option(
            '-I', '--is-imported', action='store', dest='is_imported',
            help="Match on is_imported value (True or False).")
        self.parser.add_option(
            '-m', '--msgid', action='store', dest='msgid',
            help="Match on (singular) msgid text.")
        self.parser.add_option(
            '-o', '--origin', action='store', dest='origin',
            help="Origin match: delete only messages with this origin code.")
        self.parser.add_option(
            '-f', '--force', action='store_const', const=True, dest='force',
            help="Override safety check on moderately unsafe action.")

    def get_id(self, identifier, lookup_function=None):
        """Look up id of object identified by a string.

        :param identifier: String identifying an object.  If entirely
            numeric, taken as id.  Otherwise, passed to lookup_function.
        :param lookup_function: Callback that will take `identifier` as its
            argument and return a numeric object id, or raise an error if no
            object has the given identifier.
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
            self.logger.info("'%s' not found." % identifier)
        else:
            self.logger.debug("'%s' has id %d." % (identifier, result))
        return result

    def _check_option_type(self, option_name, option_type):
        """Check that argument is of given type, or None."""
        option = getattr(self.options, option_name)
        assert option is None or isinstance(option, option_type), (
            "Wrong argument type for %s: expected %s, got %s." % (
                option_name, option_type.__name__, option.__class__.__name__))

    def _check_options(self):
        """Check our options' types after processing."""
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
        for option, expected_type in option_types.iteritems():
            self._check_option_type(option, expected_type)

    def _normalize_options(self):
        """Normalize options to expected types."""
        self.options.submitter = self.get_id(
            self.options.submitter, get_person)
        self.options.reviewer = self.get_id(
            self.options.reviewer, get_person)
        self.options.ids = [
            self.get_id(message) for message in self.options.ids]
        self.options.potemplate = self.get_id(self.options.potemplate)
        self.options.origin = self.get_id(self.options.origin, get_origin)

        self.options.is_current = get_bool(self.options.is_current)
        self.options.is_imported = get_bool(self.options.is_imported)

    def main(self):
        """See `LaunchpadScript`."""
        (result, message) = check_constraints_safety(self.options)
        if not result:
            raise LaunchpadScriptFailure(message)
        if message is not None:
            self.logger.warn(message)

        self._normalize_options()
        self._check_options()

        remove_translations(logger=self.logger,
            submitter=self.options.submitter, reviewer=self.options.reviewer,
            ids=self.options.ids, potemplate=self.options.potemplate,
            language_code=self.options.language,
            spare_language_code=self.options.not_language,
            is_current=self.options.is_current,
            is_imported=self.options.is_imported,
            msgid_singular=self.options.msgid, origin=self.options.origin)
        self.txn.commit()


if __name__ == '__main__':
    script = RemoveTranslations(
        'canonical.launchpad.scripts.remove-translations',
        dbuser='rosettaadmin')
    script.run()

#!/usr/bin/python2.4
# Copyright 2008 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=W0403

# (Suppressing pylint "relative import" warning 0403 for _pythonpath)

__metaclass__ = type

import logging

import _pythonpath

from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)
from canonical.launchpad.scripts.remove_translations import (
    check_constraints_safety, check_removal_options,
    normalize_removal_options, remove_translations)


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

    def main(self):
        """See `LaunchpadScript`."""
        (result, message) = check_constraints_safety(self.options)
        if not result:
            raise LaunchpadScriptFailure(message)
        if message is not None:
            self.logger.warn(message)

        normalize_removal_options(self.options)
        check_removal_options(self.options)

        remove_translations(logger=self.logger,
            submitter=self.options.submitter, reviewer=self.options.reviewer,
            ids=self.options.ids, potemplate=self.options.potemplate,
            language_code=self.options.language,
            not_language=self.options.not_language,
            is_current=self.options.is_current,
            is_imported=self.options.is_imported,
            msgid_singular=self.options.msgid, origin=self.options.origin)
        self.txn.commit()


if __name__ == '__main__':
    script = RemoveTranslations(
        'canonical.launchpad.scripts.remove-translations',
        dbuser='rosettaadmin')
    script.run()

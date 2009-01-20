#! /usr/bin/python2.4
# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Run gettext consistency checks on messages in the database.

Incoming translations are always run through gettext to check for
errors, mainly with conversion specifiers in format strings.  But under
certain circumstances (bug 317578) it's possible to have messages in
the database that would fail that check in their present form.  Or a
check may be added in later versions of gettext.

This script checks messages against gettext again.  Ones that fail are
disabled; if there is an imported alternative that does pass, it is
enabled instead.
"""

__metaclass__ = type
__all__ = ['GettextCheckMessages']

from datetime import timedelta, datetime

import _pythonpath
import gettextpo
import logging

from canonical.launchpad.database.translationmessage import TranslationMessage
from canonical.launchpad.helpers import validate_translation
from canonical.launchpad.scripts.base import LaunchpadScript


class GettextCheckMessages(LaunchpadScript):

    _check_count = 0
    _error_count = 0
    _disable_count = 0
    _unmask_count = 0
    _commit_count = 0

    _commit_interval = timedelta(0, 3)

    def add_my_options(self):
        self.parser.add_option(
            '-d', '--dry-run', action="store_true", dest='dry_run',
            default=False, help="Don't really make any database changes.")
        self.parser.add_option(
            '-o', '--order-by', dest='order_by', default=None,
            help="""SQL "order by" clause for messages to check.""")
        self.parser.add_option(
            '-w', '--where', dest="where", default=None,
            help="""SQL "where" clause specifying which messages to check.""")

    def main(self):
        if self.options.dry_run:
            self.logger.info("Dry run.  Not making any changes.")

        self.logger.debug(
            "Checking messages matching: %s" % self.options.where)

        messages = TranslationMessage.select(
            self.options.where, orderBy=self.options.order_by)
        self._iterate(messages)

        self.logger.info("Done.")
        self.logger.info("Messages checked: %d" % self._check_count)
        self.logger.info("Validation errors: %d" % self._error_count)
        self.logger.info("Messages disabled: %d" % self._disable_count)
        self.logger.info("Messages unmasked: %d" % self._unmask_count)
        self.logger.info("Transactions: %d" % self._commit_count)

    def _log_bad_message(self, bad_message, unmasked_message, error):
        """Report gettext validation error for active message."""
        currency_markers = []
        if bad_message.is_current:
            currency_markers.append('current')
        if bad_message.is_imported:
            currency_markers.append('imported')
        if currency_markers == []:
            currency_markers.append('unused')
        currency = ', '.join(currency_markers)
        self.logger.info("%d (%s): %s" % (bad_message.id, currency, error))
        if unmasked_message is not None:
            self.logger.info(
                "%s: unmasked %s" % (bad_message.id, unmasked_message.id))

    def _check_message_for_error(self, translationmessage):
        """Return error message for `translationmessage`, if any.

        :return: Error message string if there is an error, or None otherwise.
        """
        self._check_count += 1
        potmsgset = translationmessage.potmsgset
        msgids = potmsgset._list_of_msgids()
        msgstrs = translationmessage.translations

        try:
            validate_translation(msgids, msgstrs, potmsgset.flags)
        except gettextpo.error, error:
            self._error_count += 1
            return str(error)

        return None

    def _get_imported_alternative(self, translationmessage):
        """Look for a valid, imported alternative for this message."""
        if translationmessage.is_imported:
            return None

        potmsgset = translationmessage.potmsgset
        pofile = translationmessage.pofile
        return potmsgset.getImportedTranslationMessage(
            pofile.language, pofile.variant)

    def _check_and_fix(self, translationmessage):
        """Check message against gettext, and fix it if necessary."""
        error = self._check_message_for_error(translationmessage)
        if error is None:
            return

        imported = self._get_imported_alternative(translationmessage)
        if imported is not None:
            # There is also an imported message that the current message
            # was previously masking.  If that one passes checks, we can
            # activate it instead.  Disabling the current message
            # "unmasks" the imported one.
            error = self._check_message_for_error(imported)
            if error is not None:
                imported = None

        self._log_bad_message(translationmessage, imported, error)
        translationmessage.is_current = False
        self._disable_count += 1
        if imported is not None:
            imported.is_current = True
            self._unmask_count += 1

    def _do_commit(self):
        """Commit ongoing transaction, start a new one."""
        self.logger.debug("Finishing transaction.")

        if self.options.dry_run:
            self.txn.abort()
        else:
            self.txn.commit()

        self.txn.begin()
        self._commit_count += 1

    def _check_transaction_timer(self, next_commit):
        """Do intermediate commit if needed.  Return next commit time."""
        if next_commit is None or self._get_time() >= next_commit:
            self._do_commit()
            return self._get_time() + self._commit_interval
        else:
            return next_commit

    def _get_time(self):
        """Read the clock.  Tests can replace this with mock clocks."""
        return datetime.utcnow()

    def _iterate(self, messages):
        """Go over `messages`; check and fix them, committing regularly,"""
        next_commit = None
        for message in messages:
            self.logger.debug("Checking message %s" % message.id)
            self._check_and_fix(message)
            next_commit = self._check_transaction_timer(next_commit)

        self._do_commit()


if __name__ == '__main__':
    GettextCheckMessages('gettext-check-messages').lock_and_run()

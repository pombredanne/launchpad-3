# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Functions used with the Rosetta PO import script."""

__metaclass__ = type


__all__ = [
    'ImportProcess',
    ]

import time

from zope.component import getUtility

from canonical.config import config
from canonical.database.sqlbase import flush_database_updates
from canonical.launchpad import helpers
from canonical.launchpad.interfaces.launchpad import ILaunchpadCelebrities
from lp.translations.interfaces.translationimportqueue import (
    ITranslationImportQueue, RosettaImportStatus)
from canonical.launchpad.mail import simple_sendmail
from canonical.launchpad.mailnotification import MailWrapper


class ImportProcess:
    """Import .po and .pot files attached to Rosetta."""

    def __init__(self, ztm, logger, max_seconds=3600):
        """Initialize the ImportProcess object.

        Arguments:

        :param ztm: transaction manager to commit our individual imports.

        :param logger: logging object to log informational messages and errors
        to.

        :param max_seconds: "alarm clock": after this many seconds, the job
        should finish up even if there is more work for it to do.  This is a
        mere guideline; actual processing time may be longer.
        """
        self.ztm = ztm
        self.logger = logger
        self.deadline = time.time() + max_seconds

    def run(self):
        """Execute the import of entries from the queue."""
        # Get the queue.
        translation_import_queue = getUtility(ITranslationImportQueue)

        # Get the list of each product or distroseries with pending imports.
        # We'll serve these queues in turn, one request each, until either the
        # queue is drained or our time is up.
        importqueues = translation_import_queue.getRequestTargets(
            RosettaImportStatus.APPROVED)

        if not importqueues:
            self.logger.info("No requests pending.")
            return

        # XXX: JeroenVermeulen 2007-06-20: How on Earth do we test that the
        # deadline code works?  It's only a small thing, and of course we'll
        # notice that it works when we stop getting errors about this script
        # not finishing.  Meanwhile, SteveA has suggested a more general
        # solution.
        while importqueues and time.time() < self.deadline:
            # For fairness, service all queues at least once; don't check for
            # deadline.  If we stopped halfway through the list of queues, we
            # would accidentally favour queues that happened to come out at
            # the front of the list.
            for queue in importqueues:
                # Make sure our previous state changes hit the database.
                # Otherwise, getFirstEntryToImport() might pick up an entry
                # we've already processed but haven't flushed yet.
                # XXX: JeroenVermeulen 2007-11-29 bug=3989: should become
                # unnecessary once Zopeless commit() improves.
                flush_database_updates()

                entry_to_import = queue.getFirstEntryToImport()
                if entry_to_import is None:
                    continue

                if entry_to_import.import_into is None:
                    if entry_to_import.sourcepackagename is not None:
                        package = entry_to_import.sourcepackagename.name
                    elif entry_to_import.productseries is not None:
                        package = (
                            entry_to_import.productseries.product.displayname)
                    else:
                        raise AssertionError(
                            "Import queue entry %d has neither a "
                            "source package name nor a product series."
                            % entry_to_import.id)
                    raise AssertionError(
                        "Broken translation import queue entry %d (for %s): "
                        "it's Approved but lacks the place where it should "
                        "be imported!  A DBA will need to fix this by hand."
                        % (entry_to_import.id, package))

                # Do the import.
                title = '[Unknown Title]'
                try:
                    title = entry_to_import.import_into.title
                    self.logger.info('Importing: %s' % title)

                    (mail_subject, mail_body) = (
                        entry_to_import.import_into.importFromQueue(
                            entry_to_import, self.logger))

                    if mail_subject is not None:
                        # A `mail_subject` of None indicates that there
                        # is no notification worth sending out.
                        from_email = config.rosetta.admin_email
                        katie = getUtility(ILaunchpadCelebrities).katie
                        if entry_to_import.importer == katie:
                            # Email import state to Debian imports email.
                            to_email = config.rosetta.debian_import_email
                        else:
                            to_email = helpers.get_contact_email_addresses(
                                entry_to_import.importer)

                        if to_email:
                            text = MailWrapper().format(mail_body)

                            # XXX: JeroenVermeulen 2007-11-29 bug=29744: email
                            # isn't transactional in zopeless mode.  That
                            # means that our current transaction can fail
                            # after we already sent out a success
                            # notification.  To prevent that, we commit the
                            # import (attempt) before sending out the email.
                            # That way the worst that can happen is that an
                            # email goes missing.
                            # Once bug 29744 is fixed, this commit must die so
                            # the email and the import will be in a single
                            # atomic operation.
                            self.ztm.commit()
                            self.ztm.begin()

                            simple_sendmail(
                                from_email, to_email, mail_subject, text)

                except KeyboardInterrupt:
                    self.ztm.abort()
                    raise
                except AssertionError:
                    raise
                except:
                    # If we have any exception, log it, abort the transaction
                    # and set the status to FAILED.
                    self.logger.error('Got an unexpected exception while'
                                      ' importing %s' % title, exc_info=1)
                    # We are going to abort the transaction, need to save the
                    # id of this entry to update its status.
                    failed_entry_id = entry_to_import.id
                    self.ztm.abort()
                    # Get the needed objects to set the failed entry status as
                    # FAILED.
                    self.ztm.begin()
                    translation_import_queue = getUtility(
                        ITranslationImportQueue)
                    entry_to_import = translation_import_queue[
                        failed_entry_id]
                    entry_to_import.setStatus(RosettaImportStatus.FAILED)
                    self.ztm.commit()
                    self.ztm.begin()
                    # Go to process next entry.
                    continue

                # As soon as the import is done, we commit the transaction
                # so it's not lost.
                try:
                    self.ztm.commit()
                    self.ztm.begin()
                except KeyboardInterrupt:
                    self.ztm.abort()
                    raise
                except:
                    # If we have any exception, we log it and abort the
                    # transaction.
                    self.logger.error(
                        'We got an unexpected exception while committing the '
                        'transaction',
                        exc_info=1)
                    self.ztm.abort()
                    self.ztm.begin()

            # Refresh the list of objects with pending imports.
            importqueues = (
                translation_import_queue.getRequestTargets(
                    RosettaImportStatus.APPROVED))

        if not importqueues:
            self.logger.info("Import requests completed.")
        else:
            self.logger.info("Used up available time.")

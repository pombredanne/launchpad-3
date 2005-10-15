# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Functions used with the Rosetta PO import script."""

__metaclass__ = type

import pytz
import cPickle as pickle
import time

from zope.component import getUtility

from canonical.launchpad.interfaces import (IPOTemplateSet, IPOFileSet,
    IPOFile, IPOTemplate)


class ImportProcess:
    """Import .po and .pot files attached to Rosetta."""

    # We cache files we have attempted to import
    POIMPORT_RECENTLY_SEEN_PICKLE = '/var/tmp/rosetta-poimport-seen.pickle'

    def __init__(self, ztm, logger):
        """Initialize the ImportProcess object.

        Get two arguments, the Zope Transaction Manager and a logger for the
        warning/errors messages.
        """
        self.ztm = ztm
        self.logger = logger
        self.potemplateset = getUtility(IPOTemplateSet)
        self.pofileset = getUtility(IPOFileSet)

    def recentlySeen(self, obj):
        """We store a cache on local disk of imports we have recently
        seen. This allows our code to not retry imports that recently
        failed. This method may be replaced one day with something
        more intelligent, or a method that stores this information in the
        PostgreSQL database.
        """
        try:
            seen = pickle.load(open(self.POIMPORT_RECENTLY_SEEN_PICKLE, 'rb'))
            self.logger.debug(
                    'Loaded recent import cache %s',
                    self.POIMPORT_RECENTLY_SEEN_PICKLE
                    )
        except (IOError, pickle.PickleError):
            seen = {}

        if IPOFile.providedBy(obj):
            key = '%df' % obj.id
        elif IPOTemplate.providedBy(obj):
            key = '%dt' % obj.id
        else:
            raise TypeError('Unknown object %r' % (obj,))

        self.logger.debug('Key is %s', key)

        try:
            # Clean out all entries in seen older than 1 day
            for cache_key, cache_value in list(seen.items()):
                if cache_value < time.time() - 24*60*60:
                    self.logger.debug('Garbage collecting %s', cache_key)
                    del seen[cache_key]

            # If we have seen this key recently, return True
            if seen.has_key(key):
                return True
            else:
                return False
        finally:
            now = time.time()
            self.logger.debug('Seen %s at %d', key, now)
            seen[key] = now
            self.logger.debug(
                    'Saving recent import cache %s',
                    self.POIMPORT_RECENTLY_SEEN_PICKLE
                    )
            pickle.dump(
                    seen, open(self.POIMPORT_RECENTLY_SEEN_PICKLE, 'wb'),
                    pickle.HIGHEST_PROTOCOL
                    )

    def getPendingImports(self):
        """Iterate over all templates and PO files which are waiting to be
        imported.
        """
        for template in self.potemplateset.getTemplatesPendingImport():
            yield template

        for pofile in self.pofileset.getPOFilesPendingImport():
            yield pofile

    def run(self):
        UTC = pytz.timezone('UTC')
        while True:

            # Note we invoke getPendingImports each loop, as this avoids
            # needing to cache the objects in RAM (and we can't rely on
            # the cursor remaining valid since we will be committing and
            # aborting the transaction
            object = None
            for object in self.getPendingImports():
                # Skip objects that we have attempted to import in the
                # last 24 hours.
                if self.recentlySeen(object):
                    self.logger.debug(
                            'Recently seen %s. Skipping', object.title
                            )
                    object = None
                else:
                    # We have an object to import.
                    break

            if object is None:
                # There are no objects to import. Exit the script.
                break

            # object could be a POTemplate or a POFile but both
            # objects implement the doRawImport method so we don't
            # need to care about it here.
            title = '[Unknown Title]'
            try:
                title = object.title
                self.logger.info('Importing: %s' % title)
                object.doRawImport(self.logger)
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('Got an unexpected exception while'
                                  ' importing %s' % title, exc_info=1)
                self.ztm.abort()
                continue

            # As soon as the import is done, we commit the transaction
            # so it's not lost.
            try:
                self.ztm.commit()
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('We got an unexpected exception while'
                                  ' committing the transaction', exc_info=1)
                self.ztm.abort()

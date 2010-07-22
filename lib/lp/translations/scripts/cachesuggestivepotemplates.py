# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Update the SuggestivePOTemplate cache.

The SuggestivePOTemplate cache is a narrow, lightweight database table
containing only the ids of `POTemplate`s that can provide external
translation suggestions.
"""

__metaclass__ = type
__all__ = [
    'CacheSuggestivePOTemplates',
    ]

import transaction

from zope.component import getUtility

from lp.services.scripts.base import LaunchpadCronScript
from lp.translations.interfaces.potemplate import IPOTemplateSet


class CacheSuggestivePOTemplates(LaunchpadCronScript):
    """Refresh the SuggestivePOTemplate cache."""

    def add_my_options(self):
        """See `LaunchpadScript`."""
        self.parser.add_option(
            '-n', '--dry-run', action='store_true', dest='dry_run',
            help="Only pretend; do not commit changes to the database.")

    def main(self):
        utility = getUtility(IPOTemplateSet)
        self.logger.debug("Wiping cache.")
        old_rows = utility.wipeSuggestivePOTemplatesCache()
        self.logger.debug("Repopulating cache.")
        new_rows = utility.populateSuggestivePOTemplatesCache()
        if self.options.dry_run:
            self.logger.info("Dry run; not committing.")
            transaction.abort()
        else:
            transaction.commit()
        self.logger.info("Cache size was %d; is now %d." % (
            old_rows, new_rows))

# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Set 'is_current_upstream' flag from 'is_current_ubuntu' for upstream
projects.

This script and its tests lives in two worlds because it migrates
data from the old model to the new. Since the naming and meaning of the flags
have changed, the code and comments may sometimes be confusing. Here a
little guide:

Old model                            New Model
---------                            ---------
The is_current flag marks a          The is_current_ubuntu flag marks a
translation as being currently in    translation as being currently used in
use int the project or package       the Ubuntu source package that the
that the POFile of this translation  translation is linked to.
belongs to.

The is_imported flag marks a         The is_current_upstream flag marks a 
translation as having been imported  translation as being currently used in
from an external source into this    the upstream project that this
project or source package.           translation is linked to.

Translations from projects and       Translations are shared between upstream      
source packages are not shared.      projects and source packages.

Ubuntu source packages can live quite happily int the new world because the
meaning of the flag "is_current_ubuntu", which used to be called "is_current",
remains the same for them.

Projects on the other hand could loose all their translations because their
former "current" translation would then be "current in the source package"
but not in the project itself. For this reason, all current messages in
source packages need to get their "is_current_upstream" flag set. This may
currently not be the case because it used to be called "is_imported" and
the messages may not have been imported from an external source.
"""

__metaclass__ = type
__all__ = ['MigrateCurrentFlagProcess']

import logging

from zope.component import getUtility
from zope.interface import implements

from storm.info import ClassAlias
from storm.expr import And, Count, Or, Select

from canonical.launchpad.interfaces.looptuner import ITunableLoop
from canonical.launchpad.utilities.looptuner import DBLoopTuner
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector,
    MAIN_STORE,
    MASTER_FLAVOR,
    )
from lp.registry.model.product import Product
from lp.registry.model.productseries import ProductSeries
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationmessage import TranslationMessage
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


class TranslationMessageUpstreamFlagUpdater:
    implements(ITunableLoop)
    """Populates is_current_upstream flag from is_current_ubuntu flag."""

    def __init__(self, transaction, logger, tm_ids):
        self.transaction = transaction
        self.logger = logger
        self.start_at = 0

        self.tm_ids = list(tm_ids)
        self.total = len(self.tm_ids)
        self.logger.info(
            "Fixing up a total of %d TranslationMessages." % (self.total))
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def isDone(self):
        """See `ITunableLoop`."""
        # When the main loop hits the end of the list of objects,
        # it sets start_at to None.
        return self.start_at is None

    def getNextBatch(self, chunk_size):
        """Return a batch of objects to work with."""
        end_at = self.start_at + int(chunk_size)
        self.logger.debug(
            "Getting translations[%d:%d]..." % (self.start_at, end_at))
        return self.tm_ids[self.start_at: end_at]

    def _updateTranslationMessages(self, tm_ids):
        # Unset upstream messages that might be in the way.
        PreviousUpstream = ClassAlias(
            TranslationMessage, 'PreviousUpstream')
        CurrentTranslation = ClassAlias(
            TranslationMessage, 'CurrentTranslation')
        previous_upstream_select = Select(
            PreviousUpstream.id,
            tables=[PreviousUpstream, CurrentTranslation],
            where=And(
                PreviousUpstream.is_current_upstream == True,
                (PreviousUpstream.potmsgsetID ==
                 CurrentTranslation.potmsgsetID),
                Or(And(PreviousUpstream.potemplate == None,
                       CurrentTranslation.potemplate == None),
                   (PreviousUpstream.potemplateID ==
                    CurrentTranslation.potemplateID)),
                PreviousUpstream.languageID == CurrentTranslation.languageID,
                CurrentTranslation.id.is_in(tm_ids)))

        previous_upstream = self.store.find(
            TranslationMessage,
            TranslationMessage.id.is_in(previous_upstream_select))
        previous_upstream.set(is_current_upstream=False)
        translations = self.store.find(
            TranslationMessage,
            TranslationMessage.id.is_in(tm_ids))
        translations.set(is_current_upstream=True)

    def __call__(self, chunk_size):
        """See `ITunableLoop`.

        Retrieve a batch of TranslationMessages in ascending id order,
        and set is_current_upstream flag to True on all of them.
        """
        tm_ids = self.getNextBatch(chunk_size)

        if len(tm_ids) == 0:
            self.start_at = None
        else:
            self._updateTranslationMessages(tm_ids)
            self.transaction.commit()
            self.transaction.begin()

            self.start_at += len(tm_ids)
            self.logger.info("Processed %d/%d TranslationMessages." % (
                self.start_at, self.total))


class MigrateCurrentFlagProcess:
    """Mark translations as is_current_upstream if they are is_current_ubuntu.

    Processes only translations for upstream projects, since Ubuntu
    source packages need no migration.
    """

    def __init__(self, transaction, logger=None):
        self.transaction = transaction
        self.logger = logger
        if logger is None:
            self.logger = logging.getLogger("migrate-current-flag")
        self.store = getUtility(IStoreSelector).get(MAIN_STORE, MASTER_FLAVOR)

    def getProductsWithTemplates(self):
        """Get Product.ids for projects with any translations templates."""
        return self.store.find(
            Product,
            POTemplate.productseriesID == ProductSeries.id,
            ProductSeries.productID == Product.id,
            ).group_by(Product).having(Count(POTemplate.id) > 0)

    def getCurrentNonUpstreamTranslations(self, product):
        """Get TranslationMessage.ids that need migration for a `product`."""
        return self.store.find(
            TranslationMessage.id,
            TranslationMessage.is_current_ubuntu == True,
            TranslationMessage.is_current_upstream == False,
            (TranslationMessage.potmsgsetID ==
             TranslationTemplateItem.potmsgsetID),
            TranslationTemplateItem.potemplateID == POTemplate.id,
            POTemplate.productseriesID == ProductSeries.id,
            ProductSeries.productID == product.id).config(distinct=True)

    def run(self):
        products_with_templates = list(self.getProductsWithTemplates())
        total_products = len(products_with_templates)
        if total_products == 0:
            self.logger.info("Nothing to do.")
        current_product = 0
        for product in products_with_templates:
            current_product += 1
            self.logger.info(
                "Migrating %s translations (%d of %d)..." % (
                    product.name, current_product, total_products))

            tm_ids = self.getCurrentNonUpstreamTranslations(product)
            tm_loop = TranslationMessageUpstreamFlagUpdater(
                self.transaction, self.logger, tm_ids)
            DBLoopTuner(tm_loop, 5, minimum_chunk_size=100).run()

        self.logger.info("Done.")

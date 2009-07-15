# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Export translation snapshots to bzr branches where requested."""

__metaclass__ = type
__all__ = ['ExportTranslationsToBranch']


import os.path
from zope.component import getUtility

from storm.expr import Join, SQL

from lp.translations.interfaces.potemplate import IPOTemplateSet
from canonical.launchpad.webapp.interfaces import (
    IStoreSelector, MAIN_STORE, SLAVE_FLAVOR)

from lp.code.interfaces.branchjob import IRosettaUploadJobSource
from lp.code.model.directbranchcommit import (
    ConcurrentUpdateError, DirectBranchCommit)
from lp.services.scripts.base import LaunchpadCronScript


class ExportTranslationsToBranch(LaunchpadCronScript):
    """Commit translations to translations_branches where requested."""

    def _checkForObjections(self, source):
        """Check for reasons why we can't commit to this branch.

        Raises `ConcurrentUpdateError` if there is such a reason.

        :param source: the series being exported to its
            translations_branch.
        """
        if source.translations_branch is None:
            raise ConcurrentUpdateError(
                "Translations export for %s was just disabled." % (
                    source.title))

        jobsource = getUtility(IRosettaUploadJobSource)
        if jobsource.findUnfinishedJobs(source.translations_branch).any():
            raise ConcurrentUpdateError(
                "Translations branch for %s has pending translations "
                "changes.  Not committing." % source.title)

    def _makeDirectBranchCommit(self, bzrbranch):
        """Create a `DirectBranchCommit`.

        This factory is a mock-injection point for tests.
        """
        return DirectBranchCommit(bzrbranch)

    def _commit(self, source, committer):
        """Commit changes to branch.  Check for race conditions."""
        self._checkForObjections(source)
        committer.commit("Launchpad automatic translations update.")

    def _exportToBranch(self, source):
        """Export translations for source into source.translations_branch.

        :param source: a `ProductSeries`.
        """
        self.logger.info("Exporting %s." % source.title)
        self._checkForObjections(source)

        committer = self._makeDirectBranchCommit(source.translations_branch)

        try:
            subset = getUtility(IPOTemplateSet).getSubset(
                productseries=source, iscurrent=True)
            for template in subset:
                base_path = os.path.dirname(template.path)

                for pofile in template.pofiles:
                    pofile_path = os.path.join(
                        base_path, pofile.getFullLanguageCode() + '.po')
                    pofile_contents = pofile.export()

                    committer.writeFile(pofile_path, pofile_contents)

            self._commit(source, committer)
        finally:
            committer.unlock()

    def _exportToBranches(self, productserieses):
        """Loop over `productserieses` and export their translations."""
        items_done = 0
        items_failed = 0
        for source in productserieses:
            try:
                self._exportToBranch(source)

                # We're not actually writing any changes to the
                # database, but it's not polite to stay in one
                # transaction for too long.
                if self.txn:
                    self.txn.commit()
            except (KeyboardInterrupt, SystemExit):
                raise
            except Exception, e:
                items_failed += 1
                self.logger.warn("Failure: %s" % e)
                if self.txn:
                    self.txn.abort()

            items_done += 1
            if self.txn:
                self.txn.begin()

        self.logger.info("Processed %d item(s); %d failure(s)." % (
            items_done, items_failed))

    def main(self):
        """See `LaunchpadScript`."""
        # Avoid circular imports.
        from lp.registry.model.product import Product
        from lp.registry.model.productseries import ProductSeries

        self.logger.info("Exporting to translations branches.")

        self.store = getUtility(IStoreSelector).get(MAIN_STORE, SLAVE_FLAVOR)

        product_join = Join(
            ProductSeries, Product, ProductSeries.product == Product.id)
        productseries = self.store.using(product_join).find(
            ProductSeries, SQL(
                "official_rosetta AND translations_branch IS NOT NULL"))

        # Anything deterministic will do, and even that is only for
        # testing.
        productseries = productseries.order_by(ProductSeries.id)

        bzrserver = DirectBranchCommit.makeBzrServer()
        try:
            self._exportToBranches(productseries)
        finally:
            bzrserver.tearDown()

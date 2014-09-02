# Copyright 2011-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import logging

from storm.expr import Not
from storm.locals import (
    ClassAlias,
    Store,
    )
import transaction
from zope.component import getUtility

from lp.translations.interfaces.potemplate import IPOTemplateSet
from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


# XXX wgrant 2014-08-27: This whole module is terribly misguided and
# horrifyingly broken. It's probably unsalvageable and should be
# rewritten and integrated with TranslationMerger into a
# TranslationSharingReconciler. See XXXs below for some examples.


class TranslationSplitterBase:
    """Base class for translation splitting jobs."""

    @staticmethod
    def splitPOTMsgSet(ubuntu_item):
        """Split the POTMsgSet for TranslationTemplateItem.

        The specified `TranslationTemplateItem` will have a new `POTMsgSet`
        that is a clone of the old one.  All other TranslationTemplateItems
        will continue to use the old POTMsgSet.

        :param ubuntu_item: The `TranslationTemplateItem` to use.
        """
        new_potmsgset = ubuntu_item.potmsgset.clone()
        ubuntu_item.potmsgset = new_potmsgset
        return new_potmsgset

    @staticmethod
    def migrateTranslations(upstream_msgset, ubuntu_item):
        """Migrate the translations between potemplates.

        :param upstream_msgset: The `POTMsgSet` to copy or move translations
            from.
        :param ubuntu_item: The target `TranslationTemplateItem`.
            ubuntu_item.potmsgset is the msgset to attach translations to and
            ubuntu_item.potemplate is used to determine whether to move a
            diverged translation.
        """
        for message in upstream_msgset.getAllTranslationMessages():
            if message.potemplate == ubuntu_item.potemplate:
                message.potmsgset = ubuntu_item.potmsgset
            elif not message.is_diverged:
                message.clone(ubuntu_item.potmsgset)

    def split(self):
        """Split the translations for the ProductSeries and SourcePackage."""
        logger = logging.getLogger()
        shared = enumerate(self.findShared(), 1)
        total = 0
        for num, (upstream_item, ubuntu_item) in shared:
            self.splitPOTMsgSet(ubuntu_item)
            self.migrateTranslations(upstream_item.potmsgset, ubuntu_item)
            if num % 100 == 0:
                logger.info('%d entries split.  Committing...', num)
                transaction.commit()
            total = num

        if total % 100 != 0 or total == 0:
            transaction.commit()
            logger.info('%d entries split.', total)


class TranslationSplitter(TranslationSplitterBase):
    """Split translations for a productseries, sourcepackage pair.

    If a productseries and sourcepackage were linked in error, and then
    unlinked, they may still share some translations.  This class breaks those
    associations.
    """

    def __init__(self, productseries, sourcepackage):
        """Constructor.

        :param productseries: The `ProductSeries` to split from.
        :param sourcepackage: The `SourcePackage` to split from.
        """
        self.productseries = productseries
        self.sourcepackage = sourcepackage

    def findShared(self):
        """Provide tuples of upstream, ubuntu for each shared POTMsgSet."""
        # XXX wgrant 2014-08-27: This has always been fundamentally
        # broken. It only splits between exactly that ProductSeries
        # and that SourcePackage, leaving other templates in the same
        # Product or DistributionSourcePackage sharing with the other
        # side but not some of the templates on their own side!
        store = Store.of(self.productseries)
        UpstreamItem = ClassAlias(TranslationTemplateItem, 'UpstreamItem')
        UpstreamTemplate = ClassAlias(POTemplate, 'UpstreamTemplate')
        UbuntuItem = ClassAlias(TranslationTemplateItem, 'UbuntuItem')
        UbuntuTemplate = ClassAlias(POTemplate, 'UbuntuTemplate')
        return store.find(
            (UpstreamItem, UbuntuItem),
            UpstreamItem.potmsgsetID == UbuntuItem.potmsgsetID,
            UbuntuItem.potemplateID == UbuntuTemplate.id,
            UbuntuTemplate.sourcepackagenameID ==
                self.sourcepackage.sourcepackagename.id,
            UbuntuTemplate.distroseriesID ==
                self.sourcepackage.distroseries.id,
            UpstreamItem.potemplateID == UpstreamTemplate.id,
            UpstreamTemplate.productseriesID == self.productseries.id,
        )


class TranslationTemplateSplitter(TranslationSplitterBase):
    """Split translations for an extracted potemplate.

    When a POTemplate is removed from a set of sharing templates,
    it keeps sharing POTMsgSets with other templates.  This class
    removes those associations.
    """

    def __init__(self, potemplate):
        """Constructor.

        :param potemplate: The `POTemplate` to sanitize.
        """
        self.potemplate = potemplate

    def findShared(self):
        """Provide tuples of (other, this) items for each shared POTMsgSet.

        Only return those that are shared but shouldn't be because they
        are now in non-sharing templates.
        """
        # XXX wgrant 2014-08-27: This has always been pretty broken.
        # If a sharing subset has been split, templates in the other
        # subset will end up being split from each other as well!
        sharing_subset = getUtility(IPOTemplateSet).getSharingSubset(
            product=self.potemplate.product,
            distribution=self.potemplate.distribution,
            sourcepackagename=self.potemplate.sourcepackagename)
        sharing_ids = list(
            sharing_subset.getSharingPOTemplateIDs(self.potemplate.name))

        ThisItem = ClassAlias(TranslationTemplateItem, 'ThisItem')
        OtherItem = ClassAlias(TranslationTemplateItem, 'OtherItem')
        return Store.of(self.potemplate).find(
            (OtherItem, ThisItem),
            ThisItem.potemplateID == self.potemplate.id,
            OtherItem.potmsgsetID == ThisItem.potmsgsetID,
            Not(OtherItem.potemplateID.is_in(sharing_ids)),
            )

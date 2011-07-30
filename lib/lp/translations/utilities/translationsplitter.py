# Copyright 2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type


import logging

from storm.locals import ClassAlias, Store
import transaction

from lp.translations.model.potemplate import POTemplate
from lp.translations.model.translationtemplateitem import (
    TranslationTemplateItem,
    )


class TranslationSplitterBase:

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

    def split(self):
        """Split the translations for the ProductSeries and SourcePackage."""
        logger = logging.getLogger()
        shared = enumerate(self.findShared(), 1)
        total = 0
        for num, (other_item, this_item) in shared:
            self.splitPOTMsgSet(this_item)
            self.migrateTranslations(other_item.potmsgset, this_item)
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


class TranslationTemplateMover(TranslationSplitterBase):
    """Split translations for a productseries, sourcepackage pair.

    If a productseries and sourcepackage were linked in error, and then
    unlinked, they may still share some translations.  This class breaks those
    associations.
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
        store = Store.of(self.potemplate)
        ThisItem = ClassAlias(TranslationTemplateItem, 'ThisItem')
        OtherItem = ClassAlias(TranslationTemplateItem, 'OtherItem')
        OtherTemplate = ClassAlias(POTemplate, 'OtherTemplate')
        return store.find(
            (OtherItem, ThisItem),
            ThisItem.potemplateID == self.potemplate.id,
            ThisItem.potmsgsetID == OtherItem.potmsgsetID,
            OtherTemplate.id == OtherItem.potemplateID,
            OtherTemplate.id != self.potemplate.id,
            # And they are not sharing.
            OtherTemplate.name != self.potemplate.name,
            #Or(And(OtherTemplate.productseries is not None,
            #       self.potemplate.productseries is not None,
        )

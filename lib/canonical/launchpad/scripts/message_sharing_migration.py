# Copyright 2009 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = [
    'find_potemplate_equivalence_classes_for',
    'MergePOTMsgSets',
    'merge_potmsgsets',
    'template_precedence',
    ]


import re

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.interfaces.potemplate import IPOTemplateSet
from lp.registry.interfaces.product import IProductSet
from lp.registry.interfaces.sourcepackagename import ISourcePackageNameSet
from canonical.launchpad.scripts.base import (
    LaunchpadScript, LaunchpadScriptFailure)


def get_potmsgset_key(potmsgset):
    """Get the tuple of identifying properties of a POTMsgSet.

    A POTMsgSet is identified by its msgid, optional plural msgid, and
    optional context identifier.
    """
    return (
        potmsgset.msgid_singular, potmsgset.msgid_plural, potmsgset.context)


def template_precedence(left, right):
    """Sort comparison: order sharing templates by precedence.

    Sort using this function to order sharing templates from most
    representative to least representative, as per the message-sharing
    migration spec.
    """
    if left == right:
        return 0

    # Current templates always have precedence over non-current ones.
    if left.iscurrent != right.iscurrent:
        if left.iscurrent:
            return -1
        else:
            return 1

    if left.productseries:
        left_series = left.productseries
        right_series = right.productseries
        assert left_series.product == right_series.product
        focus = left_series.product.primary_translatable
    else:
        left_series = left.distroseries
        right_series = right.distroseries
        assert left_series.distribution == right_series.distribution
        focus = left_series.distribution.translation_focus

    # Translation focus has precedence.  In case of a tie, newest
    # template wins.
    if left_series == focus:
        return -1
    elif right_series == focus:
        return 1
    elif left.id > right.id:
        return -1
    else:
        assert left.id < right.id, "Got unordered ids."
        return 1


def merge_translationtemplateitems(subordinate, representative):
    """Merge subordinate POTMsgSet into its representative POTMsgSet.

    This adds all of the subordinate's TranslationTemplateItems to the
    representative's set of TranslationTemplateItems.
    
    Any duplicates are deleted, so after this, the subordinate will no
    longer have any TranslationTemplateItems.
    """
    source = subordinate.getAllTranslationTemplateItems()
    targets = representative.getAllTranslationTemplateItems()
    templates = set(item.potemplate for item in targets)

    for item in source:
        item = removeSecurityProxy(item)
        if item.potemplate in templates:
            # The representative POTMsgSet is already in this template.
            item.destroySelf()
        else:
            # Transfer linking-table entry to representative POTMsgSet.
            item.potmsgset = representative
            templates.add(item.potemplate)


def merge_potmsgsets(potemplates):
    """Merge POTMsgSets for given sequence of sharing templates."""

    # Map each POTMsgSet key (context, msgid, plural) to its
    # representative POTMsgSet.
    representatives = {}

    # Map each representative POTMsgSet to a list of subordinate
    # POTMsgSets it represents.
    subordinates = {}

    # Figure out representative potmsgsets and their subordinates.  Go
    # through the templates, starting at the most representative and
    # moving towards the least representative.  For any unique potmsgset
    # key we find, the first POTMsgSet is the representative one.
    for template in potemplates:
        for potmsgset in template.getPOTMsgSets(False):
            key = get_potmsgset_key(potmsgset)
            if key not in representatives:
                representatives[key] = potmsgset
            representative = representatives[key]
            if representative in subordinates:
                subordinates[representative].append(potmsgset)
            else:
                subordinates[representative] = []

    for representative, potmsgsets in subordinates.iteritems():
        # Merge each subordinate POTMsgSet into its representative.
        for subordinate in potmsgsets:
            assert subordinate != representative, (
                "A POTMsgSet was found subordinate to itself.")

            original_template = None

            for message in subordinate.getAllTranslationMessages():
                message = removeSecurityProxy(message)
                if message.potemplate is None:
                    # Guard against multiple shared current or imported
                    # messages.
                    if message.is_current:
                        clashing_shared_current = (
                            representative.getCurrentTranslationMessage(
                                potemplate=None, language=message.language,
                                variant=message.variant))
                    else:
                        clashing_shared_current = None

                    if message.is_imported:
                        clashing_shared_imported = (
                            representative.getImportedTranslationMessage(
                                potemplate=None, language=message.language,
                                variant=message.variant))
                    else:
                        clashing_shared_imported = None

                    if clashing_shared_current or clashing_shared_imported:
                        # This shared message can't cohabitate with one
                        # that was more representative.  Make it diverged.
                        if original_template is None:
                            # Look up subordinate's original template if
                            # we haven't already.  We can't just get its
                            # potemplate field because that field is
                            # being phased out and might not be set.
                            links = (
                                subordinate.getAllTranslationTemplateItems())
                            original_template = links[0].potemplate

                        message.potemplate = original_template

                message.potmsgset = representative

            merge_translationtemplateitems(subordinate, representative)
            removeSecurityProxy(subordinate).destroySelf()


def get_equivalence_class(template):
    """Return whatever we group `POTemplate`s by for sharing purposes."""
    if template.sourcepackagename is None:
        package = None
    else:
        package = template.sourcepackagename.name
    return (template.name, package)


def iterate_templates(product=None, distribution=None, name_pattern=None,
                      sourcepackagename=None):
    """Yield all templates matching the provided arguments.

    This is much like a `IPOTemplateSubset`, except it operates on
    `Product`s and `Distribution`s rather than `ProductSeries` and
    `DistroSeries`.
    """
    templateset = getUtility(IPOTemplateSet)
    if product:
        subsets = [
            templateset.getSubset(productseries=series)
            for series in product.serieses
            ]
    else:
        subsets = [
            templateset.getSubset(
                distroseries=series, sourcepackagename=sourcepackagename)
            for series in distribution.serieses
            ]
    for subset in subsets:
        for template in subset:
            if name_pattern is None or re.match(name_pattern, template.name):
                yield template


def find_potemplate_equivalence_classes_for(product=None, distribution=None,
                                            name_pattern=None,
                                            sourcepackagename=None):
    """Within given `Product` or `Distribution`, find equivalent templates.

    Partitions all templates in the given context into equivalence
    classes.

    :param product: an optional `Product` to operate on.  The
        alternative is to pass `distribution`.
    :param distribution: an optional `Distribution` to operate on.  The
        alternative is to pass `product`.  If you're going to operate on
        a distribution, you may want to pass a `name_pattern` as well to
        avoid doing too much in one go.
    :param name_pattern: an optional regex pattern indicating which
        template names are to be merged.
    :param sourcepackagename: an optional source package name to operate
        on.  Leaving this out means "all packages in the distribution."
        This option only makes sense when combined with `distribution`.
    :return: a dict mapping each equivalence class to a list of
        `POTemplate`s in that class, each sorted from most to least
        representative.
    """
    assert product or distribution, "Pick a product or distribution!"
    assert not (product and distribution), (
        "Pick a product or distribution, not both!")
    assert distribution or not sourcepackagename, (
        "Picking a source package only makes sense with a distribution.")

    equivalents = {}

    templates = iterate_templates(
        product=product, distribution=distribution, name_pattern=name_pattern,
        sourcepackagename=sourcepackagename)

    for template in templates:
        key = get_equivalence_class(template)
        if key not in equivalents:
            equivalents[key] = []
        equivalents[key].append(template)

    for equivalence_list in equivalents.itervalues():
        # Sort potemplates from "most representative" to "least
        # representative."
        equivalence_list.sort(cmp=template_precedence)

    return equivalents


class MergePOTMsgSets(LaunchpadScript):

    def add_my_options(self):
        self.parser.add_option('-d', '--distribution', dest='distribution',
            help="Distribution to merge messages for.")
        self.parser.add_option('-p', '--product', dest='product',
            help="Product to merge messages for.")
        self.parser.add_option('-s', '--source-package', dest='sourcepackage',
            help="Source package name within a distribution.")
        self.parser.add_option('-t', '--template-names',
            dest='template_names',
            help="Merge for templates with name matching this regex pattern.")
        self.parser.add_option('-x', '--dry-run', dest='dry_run',
            action='store_true',
            help="Dry run, don't really make any changes.")

    def main(self):
        if self.options.product and self.options.distribution:
            raise LaunchpadScriptFailure(
                "Merge a product or a distribution, but not both.")

        if not (self.options.product or self.options.distribution):
            raise LaunchpadScriptFailure(
                "Specify a product or distribution to merge.")

        if self.options.sourcepackage and not self.options.distribution:
            raise LaunchpadScriptFailure(
                "Selecting a package only makes sense for distributions.")

        if self.options.product:
            product = getUtility(IProductSet).getByName(self.options.product)
            distribution = None
            if product is None:
                raise LaunchpadScriptFailure(
                    "Unknown product: '%s'" % self.options.product)
        else:
            product = None
            # import here to avoid circular import.
            from lp.registry.interfaces.distribution import IDistributionSet
            distribution = getUtility(IDistributionSet).getByName(
                self.options.distribution)
            if distribution is None:
                raise LaunchpadScriptFailure(
                    "Unknown distribution: '%s'" % self.options.distribution)

        sourcepackagename = getUtility(ISourcePackageNameSet).queryByName(
            self.options.sourcepackage)
        if sourcepackagename is None:
            raise LaunchpadScriptFailure(
                "Unknown source package name: '%s'" %
                    self.options.sourcepackage)

        equivalence_classes = find_potemplate_equivalence_classes_for(
            product=product, distribution=distribution,
            name_pattern=self.options.template_names,
            sourcepackagename=sourcepackagename)

        class_count = len(equivalence_classes)
        self.logger.info(
            "Merging %d template equivalence classes." % class_count)

        for number, name in enumerate(sorted(equivalence_classes.iterkeys())):
            templates = equivalence_classes[name]
            self.logger.info(
                "Merging equivalence class '%s': %d template(s) (%d / %d)" % (
                    name, len(templates) + 1, number, class_count))
            self.logger.debug("Templates: %s" % str(templates))
            merge_potmsgsets(templates)
            if self.options.dry_run:
                self.txn.abort()
            else:
                self.txn.commit()
            self.txn.begin()

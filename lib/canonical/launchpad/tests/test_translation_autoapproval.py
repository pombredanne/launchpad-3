# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

"""Unit tests for translation import queue auto-approval.

This test overlaps with the one in doc/translationimportqueue.txt.
Documentation-style tests go in there, ones that go systematically
through the possibilities should go here.
"""

import unittest

from canonical.launchpad.database import (
    CustomLanguageCode, Distribution, Language, POTemplateSet,
    POTemplateSubset, SourcePackageName, SourcePackageNameSet,
    TranslationImportQueue)
from canonical.launchpad.interfaces import (
    ICustomLanguageCode, RosettaImportStatus)
from canonical.launchpad.testing import LaunchpadObjectFactory
from canonical.launchpad.webapp.testing import verifyObject
from canonical.testing import LaunchpadZopelessLayer


class TestCustomLanguageCode(unittest.TestCase):
    """Unit tests for `CustomLanguageCode`."""

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.product_codes = {}
        self.package_codes = {}

        self.product = self.factory.makeProduct()

        # Map "es_ES" to "no language."
        self.product_codes['es_ES'] = CustomLanguageCode(
            product=self.product, language_code='es_ES')

        # Map "pt_PT" to "pt."
        self.product_codes['pt_PT'] = CustomLanguageCode(
            product=self.product, language_code='pt_PT',
            language=Language.byCode('pt'))

        self.distro = Distribution.byName('ubuntu')
        self.sourcepackagename = SourcePackageName.byName('evolution')
        self.package_codes['Brazilian'] = CustomLanguageCode(
            distribution=self.distro,
            sourcepackagename=self.sourcepackagename,
            language_code='Brazilian',
            language=Language.byCode('pt_BR'))

    def test_ICustomLanguageCode(self):
        # Does CustomLanguageCode conform to ICustomLanguageCode?
        custom_language_code = CustomLanguageCode(
            language_code='sux', product=self.product)
        verifyObject(ICustomLanguageCode, custom_language_code)

    def test_NoCustomLanguageCode(self):
        # Look up custom language code for context that has none.
        # The "fresh" items here are ones that have no custom language codes
        # associated with them.
        fresh_product = self.factory.makeProduct()
        self.assertEqual(fresh_product.getCustomLanguageCode('nocode'), None)
        self.assertEqual(fresh_product.getCustomLanguageCode('pt_PT'), None)

        fresh_distro = Distribution.byName('gentoo')
        nocode = fresh_distro.getCustomLanguageCode(
            self.sourcepackagename, 'nocode')
        self.assertEqual(nocode, None)
        brazilian = fresh_distro.getCustomLanguageCode(
            self.sourcepackagename, 'Brazilian')
        self.assertEqual(brazilian, None)

        fresh_package = SourcePackageName.byName('cnews')
        self.assertEqual(self.distro.getCustomLanguageCode(
            fresh_package, 'nocode'), None)
        self.assertEqual(self.distro.getCustomLanguageCode(
            fresh_package, 'Brazilian'), None)

    def test_UnsuccessfulCustomLanguageCodeLookup(self):
        # Look up nonexistent custom language code for product.
        self.assertEqual(self.product.getCustomLanguageCode('nocode'), None)
        self.assertEqual(
            self.distro.getCustomLanguageCode(
                self.sourcepackagename, 'nocode'),
            None)

    def test_SuccessfulProductCustomLanguageCodeLookup(self):
        # Look up custom language code.
        es_ES_code = self.product.getCustomLanguageCode('es_ES')
        self.assertEqual(es_ES_code, self.product_codes['es_ES'])
        self.assertEqual(es_ES_code.product, self.product)
        self.assertEqual(es_ES_code.distribution, None)
        self.assertEqual(es_ES_code.sourcepackagename, None)
        self.assertEqual(es_ES_code.language_code, 'es_ES')
        self.assertEqual(es_ES_code.language, None)

    def test_SuccessfulPackageCustomLanguageCodeLookup(self):
        # Look up custom language code.
        Brazilian_code = self.distro.getCustomLanguageCode(
            self.sourcepackagename, 'Brazilian')
        self.assertEqual(Brazilian_code, self.package_codes['Brazilian'])
        self.assertEqual(Brazilian_code.product, None)
        self.assertEqual(Brazilian_code.distribution, self.distro)
        self.assertEqual(
            Brazilian_code.sourcepackagename, self.sourcepackagename)
        self.assertEqual(Brazilian_code.language_code, 'Brazilian')
        self.assertEqual(Brazilian_code.language, Language.byCode('pt_BR'))


class TestGuessPOFileCustomLanguageCode(unittest.TestCase):
    """Test interaction with `TranslationImportQueueEntry.getGuessedPOFile`.

    Auto-approval of translation files, i.e. figuring out which existing
    translation file a new upload might match, is a complex process.
    One of the factors that influence it is the existence of custom
    language codes that may redirect translations from a wrong language
    code to a right one, or to none at all.
    """

    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.product = self.factory.makeProduct()
        self.series = self.factory.makeSeries(product=self.product)
        self.queue = TranslationImportQueue()
        self.template = POTemplateSubset(productseries=self.series).new(
            'test', 'test', 'test.pot', self.product.owner)

    def _makePOFile(self, language_code):
        """Create a translation file."""
        file = self.template.newPOFile(
            language_code, requester=self.product.owner)
        file.syncUpdate()
        return file

    def _makeQueueEntry(self, language_code):
        """Create translation import queue entry."""
        return self.queue.addOrUpdateEntry(
            "%s.po" % language_code, 'contents', True, self.product.owner,
            productseries=self.series)

    def _setCustomLanguageCode(self, language_code, target_language_code):
        """Create custom language code."""
        if target_language_code is None:
            language = None
        else:
            language = Language.byCode(target_language_code)
        customcode = CustomLanguageCode(
            product=self.product, language_code=language_code,
            language=language)
        customcode.syncUpdate()

    def test_MatchWithoutCustomLanguageCode(self):
        # Of course matching will work without custom language codes.
        tr_file = self._makePOFile('tr')
        entry = self._makeQueueEntry('tr')
        self.assertEqual(entry.getGuessedPOFile(), tr_file)

    def test_CustomLanguageCodeEnablesMatch(self):
        # Custom language codes may enable matches that wouldn't have been
        # found otherwise.
        fy_file = self._makePOFile('fy')
        entry = self._makeQueueEntry('fy_NL')
        self.assertEqual(entry.getGuessedPOFile(), None)

        self._setCustomLanguageCode('fy_NL', 'fy')

        self.assertEqual(entry.getGuessedPOFile(), fy_file)

    def test_CustomLanguageCodeParsesBogusLanguage(self):
        # A custom language code can tell the importer how to deal with a
        # completely nonstandard language code.
        entry = self._makeQueueEntry('flemish')
        self.assertEqual(entry.getGuessedPOFile(), None)

        self._setCustomLanguageCode('flemish', 'nl')

        nl_file = entry.getGuessedPOFile()
        self.assertEqual(nl_file.language.code, 'nl')

    def test_CustomLanguageCodePreventsMatch(self):
        # A custom language code that disables a language code may hide an
        # existing translation file from the matching process.
        sv_file = self._makePOFile('sv')
        entry = self._makeQueueEntry('sv')
        self.assertEqual(entry.getGuessedPOFile(), sv_file)

        self._setCustomLanguageCode('sv', None)

        self.assertEqual(entry.getGuessedPOFile(), None)
        self.assertEqual(entry.status, RosettaImportStatus.DELETED)

    def test_CustomLanguageCodeHidesPOFile(self):
        # A custom language code may redirect the search away from an existing
        # translation file, even if it points to an existing language.
        elx_file = self._makePOFile('elx')
        entry = self._makeQueueEntry('elx')
        self.assertEqual(entry.getGuessedPOFile(), elx_file)

        self._setCustomLanguageCode('elx', 'el')

        el_file = entry.getGuessedPOFile()
        self.failIfEqual(el_file, elx_file)
        self.assertEqual(el_file.language.code, 'el')

    def test_CustomLanguageCodeRedirectsMatch(self):
        # A custom language code may cause one match to be replaced by another
        # one.
        nn_file = self._makePOFile('nn')
        nb_file = self._makePOFile('nb')
        entry = self._makeQueueEntry('nb')
        self.assertEqual(entry.getGuessedPOFile(), nb_file)

        self._setCustomLanguageCode('nb', 'nn')

        self.assertEqual(entry.getGuessedPOFile(), nn_file)

    def test_CustomLanguageCodeReplacesMatch(self):
        # One custom language code can block uploads for language code pt
        # while another redirects the uploads for pt_PT into their place.
        pt_file = self._makePOFile('pt')
        pt_entry = self._makeQueueEntry('pt')
        pt_PT_entry = self._makeQueueEntry('pt_PT')

        self._setCustomLanguageCode('pt', None)
        self._setCustomLanguageCode('pt_PT', 'pt')

        self.assertEqual(pt_entry.getGuessedPOFile(), None)
        self.assertEqual(pt_PT_entry.getGuessedPOFile(), pt_file)

    def test_CustomLanguageCodesSwitchLanguages(self):
        # Two CustomLanguageCodes may switch two languages around.
        zh_CN_file = self._makePOFile('zh_CN')
        zh_TW_file = self._makePOFile('zh_TW')
        zh_CN_entry = self._makeQueueEntry('zh_CN')
        zh_TW_entry = self._makeQueueEntry('zh_TW')

        self._setCustomLanguageCode('zh_CN', 'zh_TW')
        self._setCustomLanguageCode('zh_TW', 'zh_CN')

        self.assertEqual(zh_CN_entry.getGuessedPOFile(), zh_TW_file)
        self.assertEqual(zh_TW_entry.getGuessedPOFile(), zh_CN_file)


class TestTemplateGuess(unittest.TestCase):
    """Test auto-approval's attempts to find the right template."""
    layer = LaunchpadZopelessLayer

    def setUp(self):
        self.factory = LaunchpadObjectFactory()
        self.templateset = POTemplateSet()

        self.product = self.factory.makeProduct()
        self.productseries = self.factory.makeSeries(product=self.product)
        product_subset = POTemplateSubset(productseries=self.productseries)
        self.producttemplate1 = product_subset.new(
            'test1', 'test1', 'test.pot', self.product.owner)
        self.producttemplate2 = product_subset.new(
            'test2', 'test2', 'test.pot', self.product.owner)

        self.distro = self.factory.makeDistribution()
        self.distroseries = self.factory.makeDistroRelease(
            distribution=self.distro)
        self.packagename = SourcePackageNameSet().new('package')
        self.from_packagename = SourcePackageNameSet().new('from')
        distro_subset = POTemplateSubset(
            distroseries=self.distroseries,
            sourcepackagename=self.packagename)
        self.distrotemplate1 = distro_subset.new(
            'test1', 'test1', 'test.pot', self.distro.owner)
        self.distrotemplate2 = distro_subset.new(
            'test2', 'test2', 'test.pot', self.distro.owner)

    def test_ByPathAndOriginProductNonCurrentDuplicate(self):
        # If two templates for the same product series have the same
        # path, but only one is current, that one is returned.
        self.producttemplate1.iscurrent = False
        self.producttemplate2.iscurrent = True
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', productseries=self.productseries)
        self.assertEqual(guessed_template, self.producttemplate2)

    def test_ByPathAndOriginProductNoCurrentTemplate(self):
        # Non-current templates in product series are ignored.
        self.producttemplate1.iscurrent = False
        self.producttemplate2.iscurrent = False
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', productseries=self.productseries)
        self.assertEqual(guessed_template, None)

    def test_ByPathAndOriginDistroNonCurrentDuplicate(self):
        # If two templates for the same distroseries and source package
        # have the same  path, but only one is current, the current one
        # is returned.
        self.distrotemplate1.iscurrent = False
        self.distrotemplate2.iscurrent = True
        self.distrotemplate1.from_sourcepackagename = None
        self.distrotemplate2.from_sourcepackagename = None
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', distroseries=self.distroseries,
            sourcepackagename=self.packagename)
        self.assertEqual(guessed_template, self.distrotemplate2)

    def test_ByPathAndOriginDistroNoCurrentTemplate(self):
        # Non-current templates in distroseries are ignored.
        self.distrotemplate1.iscurrent = False
        self.distrotemplate2.iscurrent = False
        self.distrotemplate1.from_sourcepackagename = None
        self.distrotemplate2.from_sourcepackagename = None
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', distroseries=self.distroseries,
            sourcepackagename=self.packagename)
        self.assertEqual(guessed_template, None)

    def test_ByPathAndOriginDistroFromSourcePackageNonCurrentDuplicate(self):
        # If two templates for the same distroseries and original source
        # package have the same path, but only one is current, that one is
        # returned.
        self.distrotemplate1.iscurrent = False
        self.distrotemplate2.iscurrent = True
        self.distrotemplate1.from_sourcepackagename = self.from_packagename
        self.distrotemplate2.from_sourcepackagename = self.from_packagename
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', distroseries=self.distroseries,
            sourcepackagename=self.from_packagename)
        self.assertEqual(guessed_template, self.distrotemplate2)

    def test_ByPathAndOriginDistroFromSourcePackageNoCurrentTemplate(self):
        # Non-current templates in distroseries are ignored by the
        # "from_sourcepackagename" match.
        self.distrotemplate1.iscurrent = False
        self.distrotemplate2.iscurrent = False
        self.distrotemplate1.from_sourcepackagename = self.from_packagename
        self.distrotemplate2.from_sourcepackagename = self.from_packagename
        guessed_template = self.templateset.getPOTemplateByPathAndOrigin(
            'test.pot', distroseries=self.distroseries,
            sourcepackagename=self.from_packagename)
        self.assertEqual(guessed_template, None)

    def test_ByTranslationDomain(self):
        # getPOTemplateByTranslationDomain looks up a template by
        # translation domain.
        subset = POTemplateSubset(distroseries=self.distroseries)
        potemplate = subset.getPOTemplateByTranslationDomain('test1')
        self.assertEqual(potemplate, self.distrotemplate1)

    def test_ByTranslationDomain_none(self):
        # Test getPOTemplateByTranslationDomain for the zero-match case.
        subset = POTemplateSubset(distroseries=self.distroseries)
        potemplate = subset.getPOTemplateByTranslationDomain('notesthere')
        self.assertEqual(potemplate, None)

    def test_ByTranslationDomain_duplicate(self):
        # getPOTemplateByTranslationDomain returns no template if there
        # is more than one match.
        self.distrotemplate1.iscurrent = True
        other_package = SourcePackageNameSet().new('other-package')
        other_subset = POTemplateSubset(
            distroseries=self.distroseries, sourcepackagename=other_package)
        clashing_template = other_subset.new(
            'test3', 'test1', 'test3.pot', self.distro.owner)
        distro_subset = POTemplateSubset(distroseries=self.distroseries)
        potemplate = distro_subset.getPOTemplateByTranslationDomain('test1')
        self.assertEqual(potemplate, None)

        clashing_template.destroySelf()

    def test_ClashingEntries(self):
        # Very rarely two entries may have the same uploader, path, and
        # target package/productseries.  They would be approved for the
        # same template, except there's a uniqueness condition on that
        # set of properties.
        # To tickle this condition, the user first has to upload a file
        # that's not attached to a template; then upload another one
        # that is, before the first one goes into auto-approval.
        queue = TranslationImportQueue()
        template = self.producttemplate1

        template.path = 'program/program.pot'
        self.producttemplate2.path = 'errors/errors.pot'
        entry1 = queue.addOrUpdateEntry(
            'program/nl.po', 'contents', False, template.owner,
            productseries=template.productseries)

        # The clashing entry goes through approval unsuccessfully, but
        # without causing breakage.
        entry2 = queue.addOrUpdateEntry(
            'program/nl.po', 'other contents', False, template.owner,
            productseries=template.productseries, potemplate=template)

        entry1.getGuessedPOFile()

        self.assertEqual(entry1.potemplate, None)


class TestKdePOFileGuess(unittest.TestCase):
    """Test auto-approval's `POFile` guessing for KDE uploads.

    KDE has an unusual setup that the approver recognizes as a special
    case: translation uploads are done in a package that represents a
    KDE language pack, following a naming convention that differs
    between KDE3 and KDE4.  The approver then attaches entries to the
    real software packages they belong to, which it finds by looking
    for a matching translation domain.
    """
    layer = LaunchpadZopelessLayer

    def setUp(self):
        factory = LaunchpadObjectFactory()
        self.queue = TranslationImportQueue()

        self.distroseries = factory.makeDistroRelease()

        # For each of KDE3 and KDE4, set up:
        #  a translation package following that KDE's naming pattern,
        #  another package that the translations really belong in,
        #  a template for that other package, and
        #  a translation file into a language we'll test in.
        self.kde_i18n_ca = SourcePackageNameSet().new('kde-i18n-ca')
        kde3_package = SourcePackageNameSet().new('kde3')
        ca_template = factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=kde3_package, name='kde3',
            translation_domain='kde3')
        self.pofile_ca = ca_template.newPOFile('ca')

        self.kde_l10n_nl = SourcePackageNameSet().new('kde-l10n-nl')
        kde4_package = SourcePackageNameSet().new('kde4')
        nl_template = factory.makePOTemplate(
            distroseries=self.distroseries,
            sourcepackagename=kde4_package, name='kde4',
            translation_domain='kde4')
        self.pofile_nl = nl_template.newPOFile('nl')

        self.pocontents = """
            msgid "foo"
            msgstr ""
            """

    def test_kde3(self):
        # KDE3 translations are in packages named kde-i10n-** (where **
        # is the language code).
        poname = self.pofile_ca.potemplate.name + '.po'
        entry = self.queue.addOrUpdateEntry(
            poname, self.pocontents, False, self.distroseries.owner,
            sourcepackagename=self.kde_i18n_ca,
            distroseries=self.distroseries)
        pofile = entry.getGuessedPOFile()
        self.assertEqual(pofile, self.pofile_ca)

    def test_kde4(self):
        # KDE4 translations are in packages named kde-l10n-** (where **
        # is the language code).
        poname = self.pofile_nl.potemplate.name + '.po'
        entry = self.queue.addOrUpdateEntry(
            poname, self.pocontents, False, self.distroseries.owner,
            sourcepackagename=self.kde_l10n_nl,
            distroseries=self.distroseries)
        pofile = entry.getGuessedPOFile()
        self.assertEqual(pofile, self.pofile_nl)

def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)


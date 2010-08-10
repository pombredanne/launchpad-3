# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Launchpad object factory."""

__metaclass__ = type

from datetime import datetime
import pytz
import unittest

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import (
    DatabaseFunctionalLayer, LaunchpadZopelessLayer)
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.enums import CodeImportReviewStatus
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage
from lp.services.worlddata.interfaces.language import ILanguage
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.binarypackagerelease import (
    BinaryPackageFileType, IBinaryPackageRelease)
from lp.soyuz.interfaces.files import (
    IBinaryPackageFile, ISourcePackageReleaseFile)
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory, ISourcePackagePublishingHistory,
    PackagePublishingPriority, PackagePublishingStatus)
from lp.testing import TestCaseWithFactory
from lp.testing.factory import is_security_proxied_or_harmless
from lp.testing.matchers import IsProxied, Provides, ProvidesAndIsProxied


class TestFactory(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    # loginAsAnyone
    def test_loginAsAnyone(self):
        # Login as anyone logs you in as any user.
        person = self.factory.loginAsAnyone()
        current_person = getUtility(ILaunchBag).user
        self.assertIsNot(None, person)
        self.assertEqual(person, current_person)

    # makeBinaryPackageBuild
    def test_makeBinaryPackageBuild_returns_IBinaryPackageBuild(self):
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertThat(
            removeSecurityProxy(bpb), Provides(IBinaryPackageBuild))

    def test_makeBinaryPackageBuild_returns_proxy(self):
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertThat(bpb, IsProxied())

    def test_makeBinaryPackageBuild_created_SPR_is_published(self):
        # It is expected that every build references an SPR that is
        # published in the target archive. Check that a created
        # SPR is also published.
        bpb = self.factory.makeBinaryPackageBuild()
        self.assertIn(
            bpb.archive, bpb.source_package_release.published_archives)

    def test_makeBinaryPackageBuild_uses_status(self):
        bpb = self.factory.makeBinaryPackageBuild(
            status=BuildStatus.NEEDSBUILD)
        self.assertEqual(BuildStatus.NEEDSBUILD, bpb.status)
        bpb = self.factory.makeBinaryPackageBuild(
            status=BuildStatus.FULLYBUILT)
        self.assertEqual(BuildStatus.FULLYBUILT, bpb.status)

    # makeBinaryPackagePublishingHistory
    def test_makeBinaryPackagePublishingHistory_returns_IBPPH(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        self.assertThat(
            removeSecurityProxy(bpph),
            Provides(IBinaryPackagePublishingHistory))

    def test_makeBinaryPackagePublishingHistory_returns_proxied(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        self.assertThat(bpph, IsProxied())

    def test_makeBinaryPackagePublishingHistory_uses_status(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            status=PackagePublishingStatus.PENDING)
        self.assertEquals(PackagePublishingStatus.PENDING, bpph.status)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        self.assertEquals(PackagePublishingStatus.PUBLISHED, bpph.status)

    def test_makeBinaryPackagePublishingHistory_uses_dateremoved(self):
        dateremoved = datetime.now(pytz.UTC)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            dateremoved=dateremoved)
        self.assertEquals(dateremoved, bpph.dateremoved)

    def test_makeBinaryPackagePublishingHistory_scheduleddeletiondate(self):
        scheduleddeletiondate = datetime.now(pytz.UTC)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            scheduleddeletiondate=scheduleddeletiondate)
        self.assertEquals(scheduleddeletiondate, bpph.scheduleddeletiondate)

    def test_makeBinaryPackagePublishingHistory_uses_priority(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            priority=PackagePublishingPriority.OPTIONAL)
        self.assertEquals(PackagePublishingPriority.OPTIONAL, bpph.priority)
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            priority=PackagePublishingPriority.EXTRA)
        self.assertEquals(PackagePublishingPriority.EXTRA, bpph.priority)

    # makeBinaryPackageRelease
    def test_makeBinaryPackageRelease_returns_IBinaryPackageRelease(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.assertThat(bpr, ProvidesAndIsProxied(IBinaryPackageRelease))

    # makeCodeImport
    def test_makeCodeImportNoStatus(self):
        # If makeCodeImport is not given a review status, it defaults to NEW.
        code_import = self.factory.makeCodeImport()
        self.assertEqual(
            CodeImportReviewStatus.NEW, code_import.review_status)

    def test_makeCodeImportReviewStatus(self):
        # If makeCodeImport is given a review status, then that is the status
        # of the created import.
        status = CodeImportReviewStatus.REVIEWED
        code_import = self.factory.makeCodeImport(review_status=status)
        self.assertEqual(status, code_import.review_status)

    # makeLanguage
    def test_makeLanguage(self):
        # Without parameters, makeLanguage creates a language with code
        # starting with 'lang'.
        language = self.factory.makeLanguage()
        self.assertTrue(ILanguage.providedBy(language))
        self.assertTrue(language.code.startswith('lang'))
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Language %s' % language.code,
                          language.englishname)

    def test_makeLanguage_with_code(self):
        # With language code passed in, that's used for the language.
        language = self.factory.makeLanguage('sr@test')
        self.assertEquals('sr@test', language.code)
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Language sr@test', language.englishname)

    def test_makeLanguage_with_name(self):
        # Language name can be passed in to makeLanguage (useful for
        # use in page tests).
        language = self.factory.makeLanguage(name='Test language')
        self.assertTrue(ILanguage.providedBy(language))
        self.assertTrue(language.code.startswith('lang'))
        # And name is constructed from code as 'Language %(code)s'.
        self.assertEquals('Test language', language.englishname)

    def test_makeLanguage_with_pluralforms(self):
        # makeLanguage takes a number of plural forms for the language.
        for number_of_forms in [None, 1, 3]:
            language = self.factory.makeLanguage(pluralforms=number_of_forms)
            self.assertEqual(number_of_forms, language.pluralforms)

    # makeSourcePackagePublishingHistory
    def test_makeSourcePackagePublishingHistory_returns_ISPPH(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertThat(
            removeSecurityProxy(spph),
            Provides(ISourcePackagePublishingHistory))

    def test_makeSourcePackagePublishingHistory_returns_proxied(self):
        spph = self.factory.makeSourcePackagePublishingHistory()
        self.assertThat(spph, IsProxied())

    def test_makeSourcePackagePublishingHistory_uses_spr(self):
        spr = self.factory.makeSourcePackageRelease()
        spph = self.factory.makeSourcePackagePublishingHistory(
            sourcepackagerelease=spr)
        self.assertEquals(spr, spph.sourcepackagerelease)

    def test_makeSourcePackagePublishingHistory_uses_status(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PENDING)
        self.assertEquals(PackagePublishingStatus.PENDING, spph.status)
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        self.assertEquals(PackagePublishingStatus.PUBLISHED, spph.status)

    def test_makeSourcePackagePublishingHistory_uses_date_uploaded(self):
        date_uploaded = datetime.now(pytz.UTC)
        spph = self.factory.makeSourcePackagePublishingHistory(
            date_uploaded=date_uploaded)
        self.assertEquals(date_uploaded, spph.datecreated)

    def test_makeSourcePackagePublishingHistory_uses_dateremoved(self):
        dateremoved = datetime.now(pytz.UTC)
        spph = self.factory.makeSourcePackagePublishingHistory(
            dateremoved=dateremoved)
        self.assertEquals(dateremoved, spph.dateremoved)

    def test_makeSourcePackagePublishingHistory_scheduleddeletiondate(self):
        scheduleddeletiondate = datetime.now(pytz.UTC)
        spph = self.factory.makeSourcePackagePublishingHistory(
            scheduleddeletiondate=scheduleddeletiondate)
        self.assertEquals(scheduleddeletiondate, spph.scheduleddeletiondate)

    # makeSuiteSourcePackage
    def test_makeSuiteSourcePackage_returns_ISuiteSourcePackage(self):
        ssp = self.factory.makeSuiteSourcePackage()
        self.assertThat(ssp, ProvidesAndIsProxied(ISuiteSourcePackage))


class TestFactoryWithLibrarian(TestCaseWithFactory):

    layer = LaunchpadZopelessLayer

    # makeBinaryPackageFile
    def test_makeBinaryPackageFile_returns_IBinaryPackageFile(self):
        bpf = self.factory.makeBinaryPackageFile()
        self.assertThat(bpf, ProvidesAndIsProxied(IBinaryPackageFile))

    def test_makeBinaryPackageFile_uses_binarypackagerelease(self):
        binarypackagerelease = self.factory.makeBinaryPackageRelease()
        bpf = self.factory.makeBinaryPackageFile(
            binarypackagerelease=binarypackagerelease)
        self.assertEqual(binarypackagerelease, bpf.binarypackagerelease)

    def test_makeBinaryPackageFile_uses_library_file(self):
        library_file = self.factory.makeLibraryFileAlias()
        bpf = self.factory.makeBinaryPackageFile(
            library_file=library_file)
        self.assertEqual(library_file, bpf.libraryfile)

    def test_makeBinaryPackageFile_uses_filetype(self):
        bpf = self.factory.makeBinaryPackageFile(
            filetype=BinaryPackageFileType.DEB)
        self.assertEqual(BinaryPackageFileType.DEB, bpf.filetype)
        bpf = self.factory.makeBinaryPackageFile(
            filetype=BinaryPackageFileType.DDEB)
        self.assertEqual(BinaryPackageFileType.DDEB, bpf.filetype)

    # makeSourcePackageReleaseFile
    def test_makeSourcePackageReleaseFile_returns_ISPRF(self):
        spr_file = self.factory.makeSourcePackageReleaseFile()
        self.assertThat(
            spr_file, ProvidesAndIsProxied(ISourcePackageReleaseFile))

    def test_makeSourcePackageReleaseFile_uses_sourcepackagerelease(self):
        spr = self.factory.makeSourcePackageRelease()
        spr_file = self.factory.makeSourcePackageReleaseFile(
            sourcepackagerelease=spr)
        self.assertEqual(spr, spr_file.sourcepackagerelease)

    def test_makeSourcePackageReleaseFile_uses_library_file(self):
        library_file = self.factory.makeLibraryFileAlias()
        spr_file = self.factory.makeSourcePackageReleaseFile(
            library_file=library_file)
        self.assertEqual(library_file, spr_file.libraryfile)

    def test_makeSourcePackageReleaseFile_uses_filetype(self):
        spr_file = self.factory.makeSourcePackageReleaseFile(
            filetype=SourcePackageFileType.DIFF)
        self.assertEqual(SourcePackageFileType.DIFF, spr_file.filetype)
        spr_file = self.factory.makeSourcePackageReleaseFile(
            filetype=SourcePackageFileType.DSC)
        self.assertEqual(SourcePackageFileType.DSC, spr_file.filetype)


class IsSecurityProxiedOrHarmlessTests(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    def test_is_security_proxied_or_harmless__none(self):
        # is_security_proxied_or_harmless() considers the None object
        # to be a harmless object.
        self.assertTrue(is_security_proxied_or_harmless(None))

    def test_is_security_proxied_or_harmless__int(self):
        # is_security_proxied_or_harmless() considers integers
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless(1))

    def test_is_security_proxied_or_harmless__string(self):
        # is_security_proxied_or_harmless() considers strings
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless('abc'))

    def test_is_security_proxied_or_harmless__unicode(self):
        # is_security_proxied_or_harmless() considers unicode objects
        # to be harmless.
        self.assertTrue(is_security_proxied_or_harmless(u'abc'))

    def test_is_security_proxied_or_harmless__proxied_object(self):
        # is_security_proxied_or_harmless() treats security proxied
        # objects as harmless.
        proxied_person = self.factory.makePerson()
        self.assertTrue(is_security_proxied_or_harmless(proxied_person))

    def test_is_security_proxied_or_harmless__unproxied_object(self):
        # is_security_proxied_or_harmless() treats security proxied
        # objects as harmless.
        unproxied_person = removeSecurityProxy(self.factory.makePerson())
        self.assertFalse(is_security_proxied_or_harmless(unproxied_person))

    def test_is_security_proxied_or_harmless__sequence_harmless_content(self):
        # is_security_proxied_or_harmless() checks all elements
        # of a sequence. If all elements are harmless, so is the
        # sequence.
        proxied_person = self.factory.makePerson()
        self.assertTrue(
            is_security_proxied_or_harmless([1, '2', proxied_person]))

    def test_is_security_proxied_or_harmless__sequence_harmful_content(self):
        # is_security_proxied_or_harmless() checks all elements
        # of a sequence. If at least one element is harmful, so is the
        # sequence.
        unproxied_person = removeSecurityProxy(self.factory.makePerson())
        self.assertFalse(
            is_security_proxied_or_harmless([1, '2', unproxied_person]))


def test_suite():
    return unittest.TestLoader().loadTestsFromName(__name__)

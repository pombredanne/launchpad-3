# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Tests for the Launchpad object factory."""

__metaclass__ = type

from datetime import datetime
import pytz

from zope.component import getUtility
from zope.security.proxy import removeSecurityProxy

from canonical.launchpad.webapp.interfaces import ILaunchBag
from canonical.testing.layers import (
    DatabaseFunctionalLayer, LaunchpadZopelessLayer)
from lp.buildmaster.interfaces.buildbase import BuildStatus
from lp.code.enums import BranchType, CodeImportReviewStatus
from lp.registry.interfaces.distribution import IDistribution
from lp.registry.interfaces.distroseries import IDistroSeries
from lp.registry.interfaces.sourcepackage import SourcePackageFileType
from lp.registry.interfaces.suitesourcepackage import ISuiteSourcePackage
from lp.services.worlddata.interfaces.language import ILanguage
from lp.soyuz.interfaces.binarypackagebuild import IBinaryPackageBuild
from lp.soyuz.interfaces.binarypackagename import IBinaryPackageName
from lp.soyuz.interfaces.binarypackagerelease import (
    BinaryPackageFileType, BinaryPackageFormat, IBinaryPackageRelease)
from lp.soyuz.interfaces.files import (
    IBinaryPackageFile, ISourcePackageReleaseFile)
from lp.soyuz.interfaces.publishing import (
    IBinaryPackagePublishingHistory, ISourcePackagePublishingHistory,
    PackagePublishingPriority, PackagePublishingPocket,
    PackagePublishingStatus)
from lp.soyuz.interfaces.queue import IPackageUpload, PackageUploadStatus
from lp.soyuz.interfaces.sourcepackagerelease import ISourcePackageRelease
from lp.testing import TestCaseWithFactory
from lp.testing.factory import is_security_proxied_or_harmless
from lp.testing.matchers import (
    IsProxied, Provides, ProvidesAndIsProxied, StartsWith)


class TestFactory(TestCaseWithFactory):

    layer = DatabaseFunctionalLayer

    # getOrMakeBinaryPackageName
    def test_getOrMakeBinaryPackageName_returns_proxied_IBPN(self):
        binarypackagename = self.factory.getOrMakeBinaryPackageName()
        self.assertThat(
            binarypackagename, ProvidesAndIsProxied(IBinaryPackageName))

    def test_getOrMakeBinaryPackageName_returns_existing_name(self):
        binarypackagename1 = self.factory.getOrMakeBinaryPackageName(
            name="foo")
        binarypackagename2 = self.factory.getOrMakeBinaryPackageName(
            name="foo")
        self.assertEqual(binarypackagename1, binarypackagename2)

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

    # makeBinaryPackageName
    def test_makeBinaryPackageName_returns_proxied_IBinaryPackageName(self):
        binarypackagename = self.factory.makeBinaryPackageName()
        self.assertThat(
            binarypackagename, ProvidesAndIsProxied(IBinaryPackageName))

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

    def test_makeBinaryPackagePublishingHistory_sets_datecreated(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory()
        self.assertNotEqual(None, bpph.datecreated)

    def test_makeBinaryPackagePublishingHistory_sets_datepub_PENDING(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            status=PackagePublishingStatus.PENDING)
        self.assertEqual(None, bpph.datepublished)

    def test_makeBinaryPackagePublishingHistory_sets_datepub_PUBLISHED(self):
        bpph = self.factory.makeBinaryPackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        self.assertNotEqual(None, bpph.datepublished)

    # makeBinaryPackageRelease
    def test_makeBinaryPackageRelease_returns_IBinaryPackageRelease(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.assertThat(bpr, ProvidesAndIsProxied(IBinaryPackageRelease))

    def test_makeBinaryPackageRelease_uses_build(self):
        build = self.factory.makeBinaryPackageBuild()
        bpr = self.factory.makeBinaryPackageRelease(build=build)
        self.assertEqual(build, bpr.build)

    def test_makeBinaryPackageRelease_uses_build_version(self):
        build = self.factory.makeBinaryPackageBuild()
        bpr = self.factory.makeBinaryPackageRelease(build=build)
        self.assertEqual(
            build.source_package_release.version, bpr.version)

    def test_makeBinaryPackageRelease_uses_build_component(self):
        build = self.factory.makeBinaryPackageBuild()
        bpr = self.factory.makeBinaryPackageRelease(build=build)
        self.assertEqual(
            build.source_package_release.component, bpr.component)

    def test_makeBinaryPackageRelease_uses_build_section(self):
        build = self.factory.makeBinaryPackageBuild()
        bpr = self.factory.makeBinaryPackageRelease(build=build)
        self.assertEqual(
            build.source_package_release.section, bpr.section)

    def test_makeBinaryPackageRelease_matches_build_version(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.assertEqual(
            bpr.build.source_package_release.version, bpr.version)

    def test_makeBinaryPackageRelease_matches_build_component(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.assertEqual(
            bpr.build.source_package_release.component, bpr.component)

    def test_makeBinaryPackageRelease_matches_build_section(self):
        bpr = self.factory.makeBinaryPackageRelease()
        self.assertEqual(
            bpr.build.source_package_release.section, bpr.section)

    def test_makeBinaryPackageRelease_uses_shlibdeps(self):
        bpr = self.factory.makeBinaryPackageRelease(shlibdeps="foo bar")
        self.assertEqual("foo bar", bpr.shlibdeps)

    def test_makeBinaryPackageRelease_allows_None_shlibdeps(self):
        bpr = self.factory.makeBinaryPackageRelease(shlibdeps=None)
        self.assertEqual(None, bpr.shlibdeps)

    def test_makeBinaryPackageRelease_uses_depends(self):
        bpr = self.factory.makeBinaryPackageRelease(depends="apt | bzr")
        self.assertEqual("apt | bzr", bpr.depends)

    def test_makeBinaryPackageRelease_allows_None_depends(self):
        bpr = self.factory.makeBinaryPackageRelease(depends=None)
        self.assertEqual(None, bpr.depends)

    def test_makeBinaryPackageRelease_uses_recommends(self):
        bpr = self.factory.makeBinaryPackageRelease(recommends="ssss")
        self.assertEqual("ssss", bpr.recommends)

    def test_makeBinaryPackageRelease_allows_None_recommends(self):
        bpr = self.factory.makeBinaryPackageRelease(recommends=None)
        self.assertEqual(None, bpr.recommends)

    def test_makeBinaryPackageRelease_uses_suggests(self):
        bpr = self.factory.makeBinaryPackageRelease(suggests="ssss")
        self.assertEqual("ssss", bpr.suggests)

    def test_makeBinaryPackageRelease_allows_None_suggests(self):
        bpr = self.factory.makeBinaryPackageRelease(suggests=None)
        self.assertEqual(None, bpr.suggests)

    def test_makeBinaryPackageRelease_uses_conflicts(self):
        bpr = self.factory.makeBinaryPackageRelease(conflicts="ssss")
        self.assertEqual("ssss", bpr.conflicts)

    def test_makeBinaryPackageRelease_allows_None_conflicts(self):
        bpr = self.factory.makeBinaryPackageRelease(conflicts=None)
        self.assertEqual(None, bpr.conflicts)

    def test_makeBinaryPackageRelease_uses_replaces(self):
        bpr = self.factory.makeBinaryPackageRelease(replaces="ssss")
        self.assertEqual("ssss", bpr.replaces)

    def test_makeBinaryPackageRelease_allows_None_replaces(self):
        bpr = self.factory.makeBinaryPackageRelease(replaces=None)
        self.assertEqual(None, bpr.replaces)

    def test_makeBinaryPackageRelease_uses_provides(self):
        bpr = self.factory.makeBinaryPackageRelease(provides="ssss")
        self.assertEqual("ssss", bpr.provides)

    def test_makeBinaryPackageRelease_allows_None_provides(self):
        bpr = self.factory.makeBinaryPackageRelease(provides=None)
        self.assertEqual(None, bpr.provides)

    def test_makeBinaryPackageRelease_uses_pre_depends(self):
        bpr = self.factory.makeBinaryPackageRelease(pre_depends="ssss")
        self.assertEqual("ssss", bpr.pre_depends)

    def test_makeBinaryPackageRelease_allows_None_pre_depends(self):
        bpr = self.factory.makeBinaryPackageRelease(pre_depends=None)
        self.assertEqual(None, bpr.pre_depends)

    def test_makeBinaryPackageRelease_uses_enhances(self):
        bpr = self.factory.makeBinaryPackageRelease(enhances="ssss")
        self.assertEqual("ssss", bpr.enhances)

    def test_makeBinaryPackageRelease_allows_None_enhances(self):
        bpr = self.factory.makeBinaryPackageRelease(enhances=None)
        self.assertEqual(None, bpr.enhances)

    def test_makeBinaryPackageRelease_uses_breaks(self):
        bpr = self.factory.makeBinaryPackageRelease(breaks="ssss")
        self.assertEqual("ssss", bpr.breaks)

    def test_makeBinaryPackageRelease_allows_None_breaks(self):
        bpr = self.factory.makeBinaryPackageRelease(breaks=None)
        self.assertEqual(None, bpr.breaks)

    def test_makeBinaryPackageRelease_uses_essential(self):
        bpr = self.factory.makeBinaryPackageRelease(essential=True)
        self.assertEqual(True, bpr.essential)
        bpr = self.factory.makeBinaryPackageRelease(essential=False)
        self.assertEqual(False, bpr.essential)

    def test_makeBinaryPackageRelease_uses_installed_size(self):
        bpr = self.factory.makeBinaryPackageRelease(installed_size=110)
        self.assertEqual(110, bpr.installedsize)

    def test_makeBinaryPackageName_uses_date_created(self):
        date_created = datetime(2000, 01, 01, tzinfo=pytz.UTC)
        bpr = self.factory.makeBinaryPackageRelease(
            date_created=date_created)
        self.assertEqual(date_created, bpr.datecreated)

    def test_makeBinaryPackageName_uses_debug_package(self):
        debug_package = self.factory.makeBinaryPackageRelease(
            binpackageformat=BinaryPackageFormat.DDEB)
        bpr = self.factory.makeBinaryPackageRelease(
            debug_package=debug_package)
        self.assertEqual(debug_package, bpr.debug_package)

    def test_makeBinaryPackageName_allows_None_debug_package(self):
        bpr = self.factory.makeBinaryPackageRelease(debug_package=None)
        self.assertEqual(None, bpr.debug_package)

    # makeBranch
    def test_makeBranch_initialMirrorRequest(self):
        # The default 'next_mirror_time' for a newly created hosted branch
        # should be None.
        branch = self.factory.makeAnyBranch(branch_type=BranchType.HOSTED)
        self.assertIs(None, branch.next_mirror_time)

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

    # makeDistribution
    def test_makeDistribution_returns_IDistribution(self):
        distribution = self.factory.makeDistribution()
        self.assertThat(
            removeSecurityProxy(distribution), Provides(IDistribution))

    def test_makeDistribution_returns_proxy(self):
        distribution = self.factory.makeDistribution()
        self.assertThat(distribution, IsProxied())

    def test_makeDistribution_created_name_starts_with_distribution(self):
        distribution = self.factory.makeDistribution()
        self.assertThat(distribution.name, StartsWith("distribution"))

    def test_makeDistribution_created_display_name_starts_Distribution(self):
        distribution = self.factory.makeDistribution()
        self.assertThat(distribution.displayname, StartsWith("Distribution"))

    # makeDistroRelease
    def test_makeDistroRelease_returns_IDistroSeries(self):
        distroseries = self.factory.makeDistroRelease()
        self.assertThat(
            removeSecurityProxy(distroseries), Provides(IDistroSeries))

    def test_makeDistroRelease_returns_proxy(self):
        distroseries = self.factory.makeDistroRelease()
        self.assertThat(distroseries, IsProxied())

    # makeDistroSeries
    def test_makeDistroSeries_returns_IDistroSeries(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertThat(
            removeSecurityProxy(distroseries), Provides(IDistroSeries))

    def test_makeDistroSeries_returns_proxy(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertThat(distroseries, IsProxied())

    def test_makeDistroSeries_created_name_starts_with_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertThat(distroseries.name, StartsWith("distroseries"))

    def test_makeDistroSeries_created_display_name_starts_Distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        self.assertThat(distroseries.displayname, StartsWith("Distroseries"))

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

    def test_makeSourcePackagePublishingHistory_datepublished_PENDING(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PENDING)
        self.assertEquals(None, spph.datepublished)

    def test_makeSourcePackagePublishingHistory_datepublished_PUBLISHED(self):
        spph = self.factory.makeSourcePackagePublishingHistory(
            status=PackagePublishingStatus.PUBLISHED)
        self.assertNotEqual(None, spph.datepublished)

    # makeSourcePackageRelease
    def test_makeSourcePackageRelease_returns_proxied_ISPR(self):
        spr = self.factory.makeSourcePackageRelease()
        self.assertThat(spr, ProvidesAndIsProxied(ISourcePackageRelease))

    def test_makeSourcePackageRelease_uses_dsc_maintainer_rfc822(self):
        maintainer = "James Westby <james.westby@canonical.com>"
        spr = self.factory.makeSourcePackageRelease(
            dsc_maintainer_rfc822=maintainer)
        self.assertEqual(maintainer, spr.dsc_maintainer_rfc822)

    # makeSuiteSourcePackage
    def test_makeSuiteSourcePackage_returns_ISuiteSourcePackage(self):
        ssp = self.factory.makeSuiteSourcePackage()
        self.assertThat(ssp, ProvidesAndIsProxied(ISuiteSourcePackage))

    def test_makeCurrentTranslationMessage_makes_shared_message(self):
        tm = self.factory.makeCurrentTranslationMessage()
        self.assertFalse(tm.is_diverged)

    def test_makeCurrentTranslationMessage_makes_diverged_message(self):
        tm = self.factory.makeCurrentTranslationMessage(diverged=True)
        self.assertTrue(tm.is_diverged)

    def test_makeCurrentTranslationMessage_makes_current_upstream(self):
        pofile = self.factory.makePOFile(
            'ka', potemplate=self.factory.makePOTemplate(
                productseries=self.factory.makeProductSeries()))

        tm = self.factory.makeCurrentTranslationMessage(pofile=pofile)

        self.assertTrue(tm.is_current_upstream)
        self.assertFalse(tm.is_current_ubuntu)

    def test_makeCurrentTranslationMessage_makes_current_ubuntu(self):
        package = self.factory.makeSourcePackage()
        pofile = self.factory.makePOFile(
            'kk', self.factory.makePOTemplate(
                sourcepackagename=package.sourcepackagename,
                distroseries=package.distroseries))

        tm = self.factory.makeCurrentTranslationMessage(pofile=pofile)

        self.assertFalse(tm.is_current_upstream)
        self.assertTrue(tm.is_current_ubuntu)

    def test_makeCurrentTranslationMessage_makes_current_tracking(self):
        tm = self.factory.makeCurrentTranslationMessage(current_other=True)

        self.assertTrue(tm.is_current_upstream)
        self.assertTrue(tm.is_current_ubuntu)

    def test_makeCurrentTranslationMessage_uses_given_translation(self):
        translations = [
            self.factory.getUniqueString(),
            self.factory.getUniqueString(),
            ]

        tm = self.factory.makeCurrentTranslationMessage(
            translations=translations)

        self.assertEqual(
            translations, [tm.msgstr0.translation, tm.msgstr1.translation])
        self.assertIs(None, tm.msgstr2)

    def test_makeCurrentTranslationMessage_sets_reviewer(self):
        reviewer = self.factory.makePerson()

        tm = self.factory.makeCurrentTranslationMessage(reviewer=reviewer)

        self.assertEqual(reviewer, tm.reviewer)

    def test_makeCurrentTranslationMessage_creates_reviewer(self):
        tm = self.factory.makeCurrentTranslationMessage(reviewer=None)

        self.assertNotEqual(None, tm.reviewer)

    def test_makeDivergedTranslationMessage_upstream(self):
        pofile = self.factory.makePOFile('ca')

        tm = self.factory.makeDivergedTranslationMessage(pofile=pofile)

        self.assertTrue(tm.is_current_upstream)
        self.assertFalse(tm.is_current_ubuntu)
        self.assertTrue(tm.is_diverged)
        self.assertEqual(pofile.potemplate, tm.potemplate)

    def test_makeDivergedTranslationMessage_ubuntu(self):
        potemplate = self.factory.makePOTemplate(
            distroseries=self.factory.makeDistroSeries(),
            sourcepackagename=self.factory.makeSourcePackageName())
        pofile = self.factory.makePOFile('eu', potemplate=potemplate)

        tm = self.factory.makeDivergedTranslationMessage(pofile=pofile)

        self.assertTrue(tm.is_current_ubuntu)
        self.assertFalse(tm.is_current_upstream)
        self.assertTrue(tm.is_diverged)
        self.assertEqual(pofile.potemplate, tm.potemplate)


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

    # makePackageUpload
    def test_makePackageUpload_returns_proxied_IPackageUpload(self):
        pu = self.factory.makePackageUpload()
        self.assertThat(pu, ProvidesAndIsProxied(IPackageUpload))

    def test_makePackageUpload_uses_distroseries(self):
        distroseries = self.factory.makeDistroSeries()
        pu = self.factory.makePackageUpload(distroseries=distroseries)
        self.assertEqual(distroseries, pu.distroseries)

    def test_makePackageUpload_uses_archive(self):
        archive = self.factory.makeArchive()
        pu = self.factory.makePackageUpload(archive=archive)
        self.assertEqual(archive, pu.archive)

    def test_makePackageUpload_uses_distribution_of_archive(self):
        archive = self.factory.makeArchive()
        pu = self.factory.makePackageUpload(archive=archive)
        self.assertEqual(archive.distribution, pu.distroseries.distribution)

    def test_makePackageUpload_uses_changes_filename(self):
        changes_filename = "foo"
        pu = self.factory.makePackageUpload(changes_filename=changes_filename)
        self.assertEqual(
            changes_filename, removeSecurityProxy(pu).changesfile.filename)

    def test_makePackageUpload_uses_pocket(self):
        pu = self.factory.makePackageUpload(
            pocket=PackagePublishingPocket.RELEASE)
        self.assertEqual(PackagePublishingPocket.RELEASE, pu.pocket)
        pu = self.factory.makePackageUpload(
            pocket=PackagePublishingPocket.PROPOSED)
        self.assertEqual(PackagePublishingPocket.PROPOSED, pu.pocket)

    def test_makePackageUpload_uses_signing_key(self):
        person = self.factory.makePerson()
        signing_key = self.factory.makeGPGKey(person)
        pu = self.factory.makePackageUpload(signing_key=signing_key)
        self.assertEqual(signing_key, pu.signing_key)

    def test_makePackageUpload_allows_None_signing_key(self):
        pu = self.factory.makePackageUpload(signing_key=None)
        self.assertEqual(None, pu.signing_key)

    def test_makePackageUpload_sets_status_DONE(self):
        pu = self.factory.makePackageUpload(status=PackageUploadStatus.DONE)
        self.assertEqual(PackageUploadStatus.DONE, pu.status)

    def test_makePackageUpload_sets_status_ACCEPTED(self):
        pu = self.factory.makePackageUpload(
            status=PackageUploadStatus.ACCEPTED)
        self.assertEqual(PackageUploadStatus.ACCEPTED, pu.status)

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

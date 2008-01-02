"""Tests for canonical.launchpad.hctapi."""

from hct.scaffold import Scaffold, register
from canonical.launchpad.ftests.harness import LaunchpadZopelessTestSetup


class DatabaseScaffold(Scaffold):
    def setUp(self):
        Scaffold.setUp(self)
        self.lzts = LaunchpadZopelessTestSetup()
        self.lzts.setUp()

    def tearDown(self):
        self.lzts.tearDown()
        Scaffold.tearDown(self)


class Registration(Scaffold):
    def testLpScheme(self):
        """lp backend registered for lp:// scheme."""
        import hct.url
        import canonical.launchpad.hctapi
        self.assertEquals(hct.url.backends["lp"], canonical.launchpad.hctapi)

    def testLaunchpadScheme(self):
        """lp backend registered for launchpad:// scheme."""
        import hct.url
        import canonical.launchpad.hctapi
        self.assertEquals(hct.url.backends["launchpad"],
                          canonical.launchpad.hctapi)

    def testDefaultScheme(self):
        """lp:// scheme is the default when active."""
        import hct.url
        self.assertEquals(hct.url.default_scheme, "lp")


class SplitPath(Scaffold):
    def testSinglePart(self):
        """split_path returns a single part."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("test"), [ "test" ])

    def testMultipleParts(self):
        """split_path returns multiple parts."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("foo/bar"), [ "foo", "bar" ])

    def testAbsolute(self):
        """split_path ignores leading slash."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("/test"), [ "test" ])

    def testDirectory(self):
        """split_path ignores trailing slash."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("test/"), [ "test" ])

    def testEmpty(self):
        """split_path ignores empty parts."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("foo//bar"), [ "foo", "bar" ])

    def testLocal(self):
        """split_path ignores initial local part."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("./test"), [ "test" ])

    def testIntermediateLocal(self):
        """split_path ignores local part anywhere in the path."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("foo/./bar"), [ "foo", "bar" ])

    def testParent(self):
        """split_path obeys parent relative parts."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("foo/../bar"), [ "bar" ])

    def testInitialParent(self):
        """split_path ignores initial parent relative part."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("../test"), [ "test" ])

    def testTooManyParent(self):
        """split_path ignores too many parent relative parts."""
        from canonical.launchpad.hctapi import split_path
        self.assertEquals(split_path("foo/../../bar"), [ "bar" ])


class GetZtm(Scaffold):
    def tearDown(self):
        from canonical.lp import ZopelessTransactionManager
        ZopelessTransactionManager._installed.uninstall()

        Scaffold.tearDown(self)

    def testAlreadyInstalled(self):
        """get_ztm returns already installed ztm."""
        from canonical.lp import initZopeless, ZopelessTransactionManager
        from canonical.launchpad.hctapi import get_ztm
        ztm_id = id(initZopeless())
        self.assertEquals(id(get_ztm()), ztm_id)

    def testCallsInitZopeless(self):
        """get_ztm calls initZopeless if no transaction managed installed."""
        from canonical.lp import ZopelessTransactionManager
        from canonical.launchpad.hctapi import get_ztm
        self.failUnless(isinstance(get_ztm(), ZopelessTransactionManager))


class GetObject(DatabaseScaffold):
    def testEmptyPath(self):
        """get_object raises LaunchpadError if path is empty."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///")

    def testCanonicalPath(self):
        """get_object canonicalises the path first."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///distros/../products/./firefox")
        self.assertEquals(obj.name, "firefox")

    def testExplicitProduct(self):
        """get_object returns an explicit Product."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///products/firefox")
        self.assertEquals(obj.name, "firefox")

    def testExplicitProductWithUpstream(self):
        """get_object returns an explicit Product with upstream base."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///upstream/firefox")
        self.assertEquals(obj.name, "firefox")

    def testExplicitProductNotFound(self):
        """get_object raises LaunchpadError if explicit product not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///products/icebadger")

    def testExplicitProductWithNoProduct(self):
        """get_object raises LaunchpadError if explicit product is missing."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///products")

    def testProduct(self):
        """get_object returns a non-explicit Product."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///firefox")
        self.assertEquals(obj.name, "firefox")

    def testIsProduct(self):
        """get_object returns a Product when asked."""
        from canonical.launchpad.database import Product
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///firefox")
        self.failUnless(isinstance(obj, Product))

    def testExplicitDistribution(self):
        """get_object returns an explicit distribution."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///distros/ubuntu")
        self.assertEquals(obj.name, "ubuntu")

    def testExplicitDistributionNotFound(self):
        """get_object raises LaunchpadError if explicit distro not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///distros/naibed")

    def testExplicitProductWithNoProduct(self):
        """get_object raises LaunchpadError if explicit product is missing."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///distros")

    def testDistribution(self):
        """get_object returns a non-explicit Distribution."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu")
        self.assertEquals(obj.name, "ubuntu")

    def testNonExplicitDistroSeriesByName(self):
        """get_object returns a non-explicit distro release by name."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///hoary")
        self.assertEquals(obj.name, "hoary")

    def testNonExplicitDistroSeriesByVersion(self):
        """get_object returns a non-explicit distro release by version."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///5.04")
        self.assertEquals(obj.name, "hoary")

    def testFirstPartNotFound(self):
        """get_object raises LaunchpadError if first part not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///wibble")

    def testProductSeries(self):
        """get_object returns a product with a series."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///products/firefox/milestones")
        self.assertEquals(obj.name, "milestones")

    def testProductReleaseWithoutSeries(self):
        """get_object returns a series product release without specified."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///products/firefox/0.9")
        self.assertEquals(obj.version, "0.9")

    def testProductSeriesOrReleaseNotFound(self):
        """get_object raises LaunchpadError if series or release not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///products/firefox/smackdown")

    def testProductReleaseInSeries(self):
        """get_object returns a product release with series specified."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///products/firefox/milestones/0.9")
        self.assertEquals(obj.version, "0.9")

    def testProductReleaseInSeriesNotFound(self):
        """get_object raises LaunchpadError if release with series not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///products/firefox/milestones/0.1.2")

    def testProductReleaseTrailing(self):
        """get_object raises LaunchpadError if anything after release."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///products/firefox/milestones/0.9/foo")

    def testDistroSeriesByName(self):
        """get_object returns a distro release by name."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/hoary")
        self.assertEquals(obj.name, "hoary")

    def testNonExplicitDistroSeriesByVersion(self):
        """get_object returns a distro release by version."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/5.04")
        self.assertEquals(obj.name, "hoary")

    def testDistroSeriesNotFound(self):
        """get_object raises LaunchpadError if distro release not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object, "lp:///ubuntu/horny")

    def testSourcesAfterDistroSeries(self):
        """get_object eats +sources after distro release."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/hoary/+sources")
        self.assertEquals(obj.name, "hoary")

    def testSourcePackage(self):
        """get_object returns a non-explicit SourcePackage."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///evolution")
        self.assertEquals(obj.name, "evolution")

    def testSourcePackageInDefaultDistro(self):
        """get_object returns a non-explicit package in the ubuntu distro."""
        from canonical.launchpad.database import Distribution
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///netapplet")
        self.assertEquals(obj.distribution, Distribution.byName("ubuntu"))

    def testSourcePackageTrumpsProduct(self):
        """get_object returns a SourcePackage not a Product."""
        from canonical.launchpad.database import DistributionSourcePackage
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///netapplet")
        self.failUnless(isinstance(obj, DistributionSourcePackage))

    def testDistroSourcePackage(self):
        """get_object returns a source package in a distro."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/netapplet")
        self.assertEquals(obj.currentrelease.version, "1.0-1")

    def testSourcePackageRelease(self):
        """get_object returns a source package release in distro."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/netapplet/1.0-1")
        self.assertEquals(obj.sourcepackagerelease.version, "1.0-1")

    def testSourcePackageReleaseInDistroSeries(self):
        """get_object returns current SourcePackageRelease in distro rel."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/warty/netapplet")
        self.assertEquals(obj.sourcepackagerelease.version, "0.99.6-1")

    def testSourcePackageReleaseInDistroSeriesNotFound(self):
        """get_object raises LaunchpadError on spr in dr not found."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///ubuntu/warty/evolution")

    def testSourcePackageReleaseDoesNotAllowRelease(self):
        """get_object raises LaunchpadError if release follows spr in dr."""
        from canonical.launchpad.hctapi import get_object, LaunchpadError
        self.assertRaises(LaunchpadError, get_object,
                          "lp:///ubuntu/hoary/netapplet/1.0-1")

    def testSourcesBetweenDistroSeriesAndSourcePackage(self):
        """get_object eats +sources between distro release and source."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///ubuntu/hoary/+sources/netapplet")
        self.assertEquals(obj.sourcepackagerelease.version, "1.0-1")

    def testResolves(self):
        """get_object resolves to a manifest holder if True."""
        from canonical.launchpad.hctapi import get_object
        obj = get_object("lp:///products/firefox", resolve=True)
        self.assertEquals(obj.version, "1.0.0")


class WhereAmI(DatabaseScaffold):
    def testProduct(self):
        """where_am_i returns URL for a Product."""
        from canonical.launchpad.database import Product
        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(Product.byName("firefox")),
                          "lp:///products/firefox")

    def testProductSeries(self):
        """where_am_i returns URL for a ProductSeries."""
        from canonical.launchpad.database import ProductSeries
        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(ProductSeries.get(1)),
                          "lp:///products/firefox/milestones")

    def testProductReleaseOnSeries(self):
        """where_am_i returns URL for a ProductRelease on a series."""
        from canonical.launchpad.database import ProductRelease
        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(ProductRelease.get(3)),
                          "lp:///products/firefox/milestones/0.9")

    def testDistribution(self):
        """where_am_i returns URL for a Distribution."""
        from canonical.launchpad.database import Distribution
        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(Distribution.byName("ubuntu")),
                          "lp:///distros/ubuntu")

    def testDistroSeries(self):
        """where_am_i returns URL for a DistroSeries."""
        from canonical.launchpad.database import DistroSeries
        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(DistroSeries.selectOneBy(name="hoary")),
                          "lp:///distros/ubuntu/hoary")

    def testSourcePackage(self):
        """where_am_i returns URL for a SourcePackage."""
        from canonical.launchpad.database import SourcePackageName
        from canonical.launchpad.database import Distribution
        name = SourcePackageName.byName("netapplet")
        distro = Distribution.byName("ubuntu")
        package = distro.getSourcePackage(name)

        from canonical.launchpad.hctapi import where_am_i
        self.assertEquals(where_am_i(package),
                          "lp:///distros/ubuntu/netapplet")

    def testSourcePackageRelease(self):
        """where_am_i returns URL for a SourcePackageRelease."""
        from canonical.launchpad.hctapi import where_am_i, get_object
        obj = get_object("lp:///distros/ubuntu/netapplet/1.0-1")
        self.assertEquals(where_am_i(obj),
                          "lp:///distros/ubuntu/netapplet/1.0-1")

    def testManifest(self):
        """where_am_i raises LaunchpadError if given Manifest."""
        from canonical.launchpad.database import Manifest
        from canonical.launchpad.hctapi import where_am_i, LaunchpadError
        self.assertRaises(LaunchpadError, where_am_i, Manifest.get(1))

    def testRandomTable(self):
        """where_am_i raises LaunchpadError if given a random table."""
        from canonical.launchpad.database import Language
        from canonical.launchpad.hctapi import where_am_i, LaunchpadError
        self.assertRaises(LaunchpadError, where_am_i, Language.get(1))

    def testNotObject(self):
        """where_am_i raises LaunchpadError if given non-SQLobject."""
        from canonical.launchpad.hctapi import where_am_i, LaunchpadError
        self.assertRaises(LaunchpadError, where_am_i, "test")

    def testNone(self):
        """where_am_i raises LaunchpadError if given None."""
        from canonical.launchpad.hctapi import where_am_i, LaunchpadError
        self.assertRaises(LaunchpadError, where_am_i, None)


class ResolveObject(DatabaseScaffold):
    def testProductRelease(self):
        """resolve_object returns the ProductRelease given."""
        from canonical.launchpad.database import ProductRelease
        from canonical.launchpad.hctapi import resolve_object
        release = ProductRelease.get(3)
        self.assertEquals(resolve_object(release), release)

    def testProductSeries(self):
        """resolve_object returns the latest release in a series."""
        from canonical.launchpad.database import ProductSeries
        from canonical.launchpad.hctapi import resolve_object
        series = ProductSeries.get(1)
        release = series.releases[-1]
        self.assertEquals(resolve_object(series), release)

    def testProduct(self):
        """resolve_object returns the latest release in a product."""
        from canonical.launchpad.database import Product
        from canonical.launchpad.hctapi import resolve_object
        product = Product.byName("firefox")
        release = product.releases[-1]
        self.assertEquals(resolve_object(product), release)

    def testProductNoReleases(self):
        """resolve_object raises LaunchpadError if product has no releases."""
        from canonical.launchpad.database import Product
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object,
                          Product.byName("gnome-terminal"))

    def testSourcePackageRelease(self):
        """resolve_object returns the SourcePackageRelease given."""
        from canonical.launchpad.hctapi import resolve_object, get_object
        release = get_object("lp:///distros/ubuntu/netapplet/1.0-1")
        self.assertEquals(resolve_object(release),
                          release.sourcepackagerelease)

    def testSourcePackage(self):
        """resolve_object returns the current development release of sp."""
        from canonical.launchpad.database import SourcePackageName
        from canonical.launchpad.database import Distribution
        name = SourcePackageName.byName("netapplet")
        distro = Distribution.byName("ubuntu")
        package = distro.getSourcePackage(name)

        from canonical.launchpad.hctapi import resolve_object, get_object
        release = get_object("lp:///ubuntu/netapplet/1.0-1")
        self.assertEquals(resolve_object(package),
                          release.sourcepackagerelease)

    def testDistroSeries(self):
        """resolve_object raises LaunchpadError if given DistroSeries."""
        from canonical.launchpad.database import DistroSeries
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, DistroSeries.get(3))

    def testDistribution(self):
        """resolve_object raises LaunchpadError if given Distribution."""
        from canonical.launchpad.database import Distribution
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, Distribution.get(1))

    def testManifest(self):
        """resolve_object raises LaunchpadError if given Manifest."""
        from canonical.launchpad.database import Manifest
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, Manifest.get(1))

    def testRandomTable(self):
        """resolve_object raises LaunchpadError if given a random table."""
        from canonical.launchpad.database import Language
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, Language.get(1))

    def testNotObject(self):
        """resolve_object raises LaunchpadError if given non-SQLobject."""
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, "test")

    def testNone(self):
        """resolve_object raises LaunchpadError if given None."""
        from canonical.launchpad.hctapi import resolve_object, LaunchpadError
        self.assertRaises(LaunchpadError, resolve_object, None)


class GetBranchFrom(DatabaseScaffold):
    def testNone(self):
        """get_branch_from returns None if given None."""
        from canonical.launchpad.hctapi import get_branch_from
        self.assertEquals(get_branch_from(None), None)

    def testReturnsHCTBranch(self):
        """get_branch_from returns an HCT branch object."""
        from canonical.launchpad.database import Branch as db_Branch
        from canonical.launchpad.hctapi import get_branch_from
        from hct.branch import Branch
        self.failUnless(isinstance(get_branch_from(db_Branch.get(10)), Branch))

    def testReturnsRightBranch(self):
        """get_branch_from returns the right branch name."""
        from canonical.launchpad.database import Branch as db_Branch
        from canonical.launchpad.hctapi import get_branch_from
        from hct.branch import Branch
        self.assertEquals(get_branch_from(db_Branch.get(10)),
                          "mozilla@arch.ubuntu.com/mozilla--release--0.9.2")


class GetChangesetFrom(DatabaseScaffold):
    def testNone(self):
        """get_changeset_from returns None if given None."""
        from canonical.launchpad.hctapi import get_changeset_from
        self.assertEquals(get_changeset_from(None), None)

    def testReturnsHCTChangeset(self):
        """get_changeset_from returns an HCT changeset object."""
        from canonical.launchpad.database import Changeset as db_Changeset
        from canonical.launchpad.hctapi import get_changeset_from
        from hct.branch import Changeset
        self.failUnless(isinstance(get_changeset_from(db_Changeset.get(1)),
                                   Changeset))

    def testReturnsRightChangeset(self):
        """get_changeset_from returns the right changeset name."""
        from canonical.launchpad.database import Changeset as db_Changeset
        from canonical.launchpad.hctapi import get_changeset_from
        from hct.branch import Changeset
        cset = "mozilla@arch.ubuntu.com/mozilla--release--0.9.2--base-0"
        self.assertEquals(get_changeset_from(db_Changeset.get(1)), cset)


class GetManifestFrom(DatabaseScaffold):
    def testNone(self):
        """get_manifest_from returns None if given None."""
        from canonical.launchpad.hctapi import get_manifest_from
        self.assertEquals(get_manifest_from(None), None)

    def testReturnsHCTManifest(self):
        """get_manifest_from returns an HCT manifest object."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import Manifest
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        self.failUnless(isinstance(get_manifest_from(db_Manifest.byUuid(uuid)),
                                   Manifest))

    def testManifestHasUuidAsAncestor(self):
        """get_manifest_from returns manifest with record uuid as ancestor."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest.ancestor, uuid)

    def testSingleManifestEntry(self):
        """get_manifest_from returns a manifest with a single entry."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(len(manifest), 1)

    def testMultipleManifestEntries(self):
        """get_manifest_from returns a manifest with multiple entries."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "bf819b15-10b3-4d1e-9963-b787753e8fb2"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(len(manifest), 2)

    def testIsManifestEntry(self):
        """get_manifest_from adds entries of ManifestEntry type to manifest."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestEntry
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0], ManifestEntry))

    def testIsManifestTarEntry(self):
        """get_manifest_from adds tar entry for tar file."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestTarEntry
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0], ManifestTarEntry))

    def testIsManifestZipEntry(self):
        """get_manifest_from adds zip entry for zip file."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestZipEntry
        uuid = "2a18a3f1-eec5-4b72-b23c-fb46c8c12a88"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0], ManifestZipEntry))

    def testIsManifestDirEntry(self):
        """get_manifest_from adds dir entry for directory."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestDirEntry
        uuid = "bf819b15-10b3-4d1e-9963-b787753e8fb2"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[1], ManifestDirEntry))

    def testIsManifestFileEntry(self):
        """get_manifest_from adds file entry for binary object."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestFileEntry
        uuid = "97b4ece8-b3c5-4e07-b529-6c76b59a5455"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0], ManifestFileEntry))

    def testManifestEntryPath(self):
        """get_manifest_from returns a manifest entry with correct path."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].path, "firefox-0.9.2.tar.gz")

    def testManifestEntryHint(self):
        """get_manifest_from returns a manifest entry with correct hint."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.manifest import ManifestEntryHint
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].hint, ManifestEntryHint.ORIGINAL_SOURCE)

    def testManifestEntryNoHint(self):
        """get_manifest_from returns a manifest entry with no hint."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "97b4ece8-b3c5-4e07-b529-6c76b59a5455"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].hint, None)

    def testManifestEntryDirname(self):
        """get_manifest_from returns a manifest entry with correct dirname."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].dirname, "firefox-0.9.2/")

    def testManifestEntryNoDirname(self):
        """get_manifest_from returns a manifest entry with no dirname."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "97b4ece8-b3c5-4e07-b529-6c76b59a5455"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].dirname, None)

    def testManifestEntryParent(self):
        """get_manifest_from correctly maps parent to sequence."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "2a18a3f1-eec5-4b72-b23c-fb46c8c12a88"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[1].parent, manifest[0])

    def testManifestEntryBranch(self):
        """get_manifest_from returns a manifest entry with a branch."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].branch,
                          "mozilla@arch.ubuntu.com/mozilla--release--0.9.2")

    def testManifestEntryBranchIsBranch(self):
        """get_manifest_from returns a branch object for entry branch."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.branch import Branch
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0].branch, Branch))

    def testManifestEntryNoBranch(self):
        """get_manifest_from returns a manifest entry with no branch."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "bf819b15-10b3-4d1e-9963-b787753e8fb2"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[1].branch, None)

    def testManifestEntryChangeset(self):
        """get_manifest_from returns a manifest entry with a changeset."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        cset = "mozilla@arch.ubuntu.com/mozilla--release--0.9.2--base-0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[0].changeset, cset)

    def testManifestEntryChangesetIsChangeset(self):
        """get_manifest_from returns a changeset object for entry changeset."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        from hct.branch import Changeset
        uuid = "24fce331-655a-4e17-be55-c718c7faebd0"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.failUnless(isinstance(manifest[0].changeset, Changeset))

    def testManifestEntryNoChangeset(self):
        """get_manifest_from returns a manifest entry with no changeset."""
        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_manifest_from
        uuid = "bf819b15-10b3-4d1e-9963-b787753e8fb2"
        manifest = get_manifest_from(db_Manifest.byUuid(uuid))
        self.assertEquals(manifest[1].changeset, None)


class GetManifest(DatabaseScaffold):
    def testReturnsManifest(self):
        """get_manifest returns a Manifest object."""
        from canonical.launchpad.hctapi import get_manifest
        from hct.manifest import Manifest
        url = "lp:///products/firefox/0.9.2"
        self.failUnless(isinstance(get_manifest(url), Manifest))

    def testReturnsRightManifest(self):
        """get_manifest returns the right Manifest."""
        from canonical.launchpad.hctapi import get_manifest
        url = "lp:///products/firefox/0.9.2"
        self.assertEquals(get_manifest(url).ancestor,
                          "24fce331-655a-4e17-be55-c718c7faebd0")

    def testResolvesUrl(self):
        """get_manifest resolves an incomplete url."""
        from canonical.launchpad.hctapi import get_manifest
        url = "firefox"
        self.assertEquals(get_manifest(url).ancestor,
                          "97b4ece8-b3c5-4e07-b529-6c76b59a5455")

    def testNoManifest(self):
        """get_manifest raises LaunchpadError on no manifest at url."""
        from canonical.launchpad.hctapi import get_manifest, LaunchpadError
        url = "lp:///distros/ubuntu/hoary/netapplet"
        self.assertRaises(LaunchpadError, get_manifest, url)

    def testNoUrl(self):
        """get_manifest raises LaunchpadError when url doesn't exist."""
        from canonical.launchpad.hctapi import get_manifest, LaunchpadError
        url = "lp:///products/icebadger/1.0"
        self.assertRaises(LaunchpadError, get_manifest, url)


class GetRelease(DatabaseScaffold):
    def testReturnsUrlForProduct(self):
        """get_release returns the url of the product release."""
        from canonical.launchpad.hctapi import get_release
        self.assertEquals(get_release("lp:///products/firefox", "0.9.2"),
                          "lp:///products/firefox/milestones/0.9.2")

    def testReturnsUrlForProductSeries(self):
        """get_release returns the url of the product series."""
        from canonical.launchpad.hctapi import get_release
        self.assertEquals(get_release("lp:///products/firefox/milestones",
                                      "0.9.2"),
                          "lp:///products/firefox/milestones/0.9.2")

    def testReturnsUrlForSourcePackage(self):
        """get_release returns the url of the source package release."""
        from canonical.launchpad.hctapi import get_release
        self.assertEquals(get_release("lp:///distros/ubuntu/netapplet",
                                      "1.0-1"),
                          "lp:///distros/ubuntu/netapplet/1.0-1")

    def testPartialVersionMatch(self):
        """get_release allows partial version match."""
        from canonical.launchpad.hctapi import get_release
        self.assertEquals(get_release("lp:///distros/ubuntu/netapplet", "1.0"),
                          "lp:///distros/ubuntu/netapplet/1.0-1")

    def testNoRelease(self):
        """get_release returns None when the release does not exist."""
        from canonical.launchpad.hctapi import get_release
        self.assertEquals(get_release("lp:///products/firefox", "1.9.2"),
                          None)

    def testNoUrl(self):
        """get_release raises LaunchpadError when the url does not exist."""
        from canonical.launchpad.hctapi import get_release, LaunchpadError
        self.assertRaises(LaunchpadError, get_release, "lp:///products/wibble",
                          "1.0")

    def testNotProductOrSourcePackage(self):
        """get_release raises LaunchpadError if not product or source package."""
        from canonical.launchpad.hctapi import get_release, LaunchpadError
        self.assertRaises(LaunchpadError, get_release, "lp:///distros/ubuntu",
                          "1.0")


class GetPackage(DatabaseScaffold):
    def testUrlDoesntExist(self):
        """get_package raises LaunchpadError if the url doesn't exist."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/wibble"
        distro = "lp:///distros/ubuntu/hoary"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testDistroDoesntExist(self):
        """get_package raises LaunchpadError if the distro doesn't exist."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet/1.0"
        distro = "lp:///distros/naibed"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testDistroSeriesAsUrl(self):
        """get_package raises LaunchpadError if url is a distro release."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///distros/ubuntu/hoary"
        distro = "lp:///distros/ubuntu/hoary"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testProductAsDistro(self):
        """get_package raises LaunchpadError if the distro is a product."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet/1.0"
        distro = "lp:///product/netapplet"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testDistroAsUrl(self):
        """get_package raises LaunchpadError if url is a distribution."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///distros/ubuntu"
        distro = "lp:///distros/ubuntu/hoary"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testProductReleaseToProduct(self):
        """get_package turns product release into product series."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///products/netapplet/1.0"
        self.assertEquals(get_package(url),
                          "lp:///products/netapplet/releases")

    def testProductReleaseInSeriesToProduct(self):
        """get_package turns product release into product series."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///products/firefox/0.9.2"
        self.assertEquals(get_package(url),
                          "lp:///products/firefox/milestones")

    def testSourcePackageReleaseToProduct(self):
        """get_package turns source package release into product."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///distros/ubuntu/warty/netapplet"
        self.assertEquals(get_package(url),
                          "lp:///products/netapplet/releases")

    def testSourcePackageToProduct(self):
        """get_package turns source package into product."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///distros/ubuntu/netapplet"
        self.assertEquals(get_package(url),
                          "lp:///products/netapplet/releases")

    def testProductToSourcePackage(self):
        """get_package fails to turn product into source package."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet"
        distro = "lp:///distros/ubuntu"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testProductSeriesToSourcePackage(self):
        """get_package turns product series into source package."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///products/netapplet/releases"
        distro = "lp:///distros/ubuntu"
        self.assertEquals(get_package(url, distro),
                          "lp:///distros/ubuntu/netapplet")

    def testProductReleaseToSourcePackageRelease(self):
        """get_package turns product release into source package release."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///products/netapplet/1.0"
        distro = "lp:///distros/ubuntu"
        self.assertEquals(get_package(url, distro),
                          "lp:///distros/ubuntu/netapplet/1.0-1")

    def testProductToSourcePackageRelease(self):
        """get_package fails to turn product into source package release."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet"
        distro = "lp:///distros/ubuntu/hoary"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testProductCannotMapToPackage(self):
        """get_package fails to get a package for a product."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet"
        distro = "lp:///distros/ubuntu/warty"
        self.assertRaises(LaunchpadError, get_package, url, distro)

    def testProductSeriesInNonLatestDistroSeries(self):
        """get_package maps productseries to sp release in non-latest d-r."""
        from canonical.launchpad.hctapi import get_package
        url = "lp:///products/netapplet/releases"
        distro = "lp:///distros/ubuntu/warty"
        self.assertEquals(get_package(url, distro),
                          "lp:///distros/ubuntu/netapplet/0.99.6-1")

    def testProductToSourcePackageReleaseFails(self):
        """get_packages fails if product not in distro release."""
        from canonical.launchpad.hctapi import get_package, LaunchpadError
        url = "lp:///products/netapplet"
        distro = "lp:///distros/ubuntu/grumpy"
        self.assertRaises(LaunchpadError, get_package, url, distro)


class GetBranch(DatabaseScaffold):
    def testReturnsBranchForProduct(self):
        """get_branch fails for a product."""
        from canonical.launchpad.hctapi import get_branch, LaunchpadError
        url = "lp:///products/evolution"
        self.assertRaises(LaunchpadError, get_branch, url)

    def testReturnsBranchForProductSeries(self):
        """get_branch returns a branch for a product series."""
        from canonical.launchpad.hctapi import get_branch
        url = "lp:///products/evolution/main"
        self.assertEquals(get_branch(url),
                          "gnome@arch.ubuntu.com/evolution--MAIN--0")

    def testReturnsBranchForSourcePackage(self):
        """get_branch returns a branch for a source package."""
        from canonical.launchpad.hctapi import get_branch
        url = "lp:///distros/ubuntu/evolution"
        self.assertEquals(get_branch(url),
                          "gnome@arch.ubuntu.com/evolution--MAIN--0")

    def testReturnsBranchObject(self):
        """get_branch returns an hct.branch.Branch object."""
        from canonical.launchpad.hctapi import get_branch
        from hct.branch import Branch
        obj = get_branch("lp:///products/evolution/main")
        self.failUnless(isinstance(obj, Branch))

    def testReturnsNone(self):
        """get_branch returns None if no branch is associated."""
        from canonical.launchpad.hctapi import get_branch
        url = "lp:///products/netapplet/releases"
        self.assertEquals(get_branch(url), None)

    def testUrlDoesntExist(self):
        """get_branch raises LaunchpadError if URL doesn't exist."""
        from canonical.launchpad.hctapi import get_branch, LaunchpadError
        url = "lp:///products/wibble"
        self.assertRaises(LaunchpadError, get_branch, url)


class IdentifyFile(DatabaseScaffold):
    def testReturnsList(self):
        """identify_file returns a list of items."""
        from canonical.launchpad.hctapi import identify_file
        size = 9922560
        sha1 = "a57faa6287aee2c58e115673a119c6083d31d1b9"
        self.assertEquals(len(identify_file("lp:", size, sha1)), 1)

    def testReturnsTupleInList(self):
        """identify_file returns two-item tuples as list items."""
        from canonical.launchpad.hctapi import identify_file
        size = 9922560
        sha1 = "a57faa6287aee2c58e115673a119c6083d31d1b9"
        self.assertEquals(len(identify_file("lp:", size, sha1)[0]), 2)

    def testUnknownDigest(self):
        """identify_file raises LaunchpadError if no file exists."""
        from canonical.launchpad.hctapi import identify_file, LaunchpadError
        size = 182
        sha1 = "938492389489abc89392d9891839859ee898918d"
        self.assertRaises(LaunchpadError, identify_file, "lp:", size, sha1)

    def testNoProducts(self):
        """identify_file raises LaunchpadError if file has no associations."""
        from canonical.launchpad.hctapi import identify_file, LaunchpadError
        size = 62927750
        sha1 = "cfbd3ee1f510c66d49be465b900a3334e8488184"
        self.assertRaises(LaunchpadError, identify_file, "lp:", size, sha1)

    def testTupleUrl(self):
        """identify_file returns the url in the first tuple entry."""
        from canonical.launchpad.hctapi import identify_file
        size = 9922560
        sha1 = "a57faa6287aee2c58e115673a119c6083d31d1b9"
        self.assertEquals(identify_file("lp:", size, sha1)[0][0],
                          "lp:///products/firefox/milestones/0.9.2")

    def testTupleManifest(self):
        """identify_file returns the manifest in the second tuple entry."""
        from canonical.launchpad.hctapi import identify_file
        from hct.manifest import Manifest
        size = 9922560
        sha1 = "a57faa6287aee2c58e115673a119c6083d31d1b9"
        self.failUnless(isinstance(identify_file("lp:", size, sha1)[0][1],
                                   Manifest))

    def testRightManifest(self):
        """identify_file fills in the manifest objects it returns."""
        from canonical.launchpad.hctapi import identify_file
        from hct.manifest import Manifest
        size = 9922560
        sha1 = "a57faa6287aee2c58e115673a119c6083d31d1b9"
        self.assertEquals(identify_file("lp:", size, sha1)[0][1].ancestor,
                          "24fce331-655a-4e17-be55-c718c7faebd0")

    def testSourcePackage(self):
        """identify_file returns the url for a source package release."""
        from canonical.launchpad.hctapi import identify_file
        size = 309386
        sha1 = "b218ca7b52fa813550e3f14cdcf3ba68606e4446"
        self.assertEquals(identify_file("lp:", size, sha1)[0][0],
                          "lp:///distros/ubuntu/evolution/1.0")

    def testNoSourcePackage(self):
        """identify_file raises LaunchpadError on package if upstream=True."""
        from canonical.launchpad.hctapi import identify_file, LaunchpadError
        size = 309386
        sha1 = "b218ca7b52fa813550e3f14cdcf3ba68606e4446"
        self.assertRaises(LaunchpadError, identify_file, "lp:", size, sha1,
                          upstream=True)

    def testProductAndSourcePackage(self):
        """identify_file returns urls for product and source package."""
        from canonical.launchpad.hctapi import identify_file
        size = 178859
        sha1 = "378b3498ead213d35a82033a6e9196014a5ef25c"
        self.assertEquals(set([_f[0] for _f in identify_file("lp:", size, sha1) ]),
                          set(["lp:///products/netapplet/releases/1.0",
                            "lp:///distros/ubuntu/netapplet/1.0-1" ]))

    def testNoManifest(self):
        """identify_file returns None as manifest if there isn't one."""
        from canonical.launchpad.hctapi import identify_file
        size = 178859
        sha1 = "378b3498ead213d35a82033a6e9196014a5ef25c"
        self.assertEquals(identify_file("lp:", size, sha1)[1][1], None)

    def testNoManifestUpstream(self):
        """identify_file raises LaunchpadError on no manifest if upstream=True."""
        from canonical.launchpad.hctapi import identify_file, LaunchpadError
        size = 309386
        sha1 = "b218ca7b52fa813550e3f14cdcf3ba68606e4446"
        self.assertRaises(LaunchpadError, identify_file, "lp:", size, sha1,
                          upstream=True)


class PutManifest(DatabaseScaffold):
    archive = True

    def testCreatesObject(self):
        """put_manifest creates a database object."""
        from hct.manifest import Manifest
        manifest = Manifest()

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertNotEqual(obj, None)

    def testAssignsObject(self):
        """put_manifest assigns the manifest to the parent object."""
        from hct.manifest import Manifest
        manifest = Manifest()

        from canonical.launchpad.hctapi import put_manifest
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Product, ProductRelease
        product = Product.byName("netapplet")
        release = product.getRelease("1.0")
        self.assertNotEquals(release.manifest, None)

    def testGeneratesUuid(self):
        """put_manifest generates a uuid for the new manifest."""
        from hct.manifest import Manifest
        manifest = Manifest()

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertNotEqual(obj.uuid, None)

    def testUuidIsNotAncestor(self):
        """put_manifest generates a new uuid, and doesn't use ancestor."""
        from hct.manifest import Manifest
        manifest = Manifest("97b4ece8-b3c5-4e07-b529-6c76b59a5455")

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertNotEqual(obj.uuid, manifest.ancestor)

    def testAncestorCreatesAncestry(self):
        """put_manifest generates an ancestry record for the ancestor."""
        from hct.manifest import Manifest
        manifest = Manifest("97b4ece8-b3c5-4e07-b529-6c76b59a5455")

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        db_m = db_Manifest.byUuid("97b4ece8-b3c5-4e07-b529-6c76b59a5455")

        self.assertEquals(obj.ancestors, [ db_m ])

    def testMergesCreateAncestry(self):
        """put_manifest generates ancestry records for merges."""
        from hct.manifest import Manifest
        manifest = Manifest("97b4ece8-b3c5-4e07-b529-6c76b59a5455")
        manifest.merges.append("2a18a3f1-eec5-4b72-b23c-fb46c8c12a88")
        manifest.merges.append("bf819b15-10b3-4d1e-9963-b787753e8fb2")

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        db_m = db_Manifest.byUuid("97b4ece8-b3c5-4e07-b529-6c76b59a5455")
        db_m1 = db_Manifest.byUuid("2a18a3f1-eec5-4b72-b23c-fb46c8c12a88")
        db_m2 = db_Manifest.byUuid("bf819b15-10b3-4d1e-9963-b787753e8fb2")

        self.assertEquals(obj.ancestors, [ db_m1, db_m2, db_m ])

    def testCreatesEntries(self):
        """put_manifest creates the right number of entry objects."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest.append(ManifestTarEntry("bar.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(len(obj.entries), 2)

    def testEntryPath(self):
        """put_manifest creates entries with correct path."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].path, manifest[-1].path)

    def testEntryHint(self):
        """put_manifest creates entries with correct hint."""
        from hct.manifest import Manifest, ManifestTarEntry, ManifestEntryHint
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].hint = ManifestEntryHint.PATCH_BASE

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryHint as db_Hint
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].hint, db_Hint.PATCH_BASE)

    def testEntryWithoutHint(self):
        """put_manifest creates entries without a hint."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].hint, None)

    def testEntryDirname(self):
        """put_manifest creates entries with correct dirname."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].dirname = "foo/"

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].dirname, manifest[-1].dirname)

    def testEntryWithoutDirname(self):
        """put_manifest creates entries without a dirname."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].dirname, None)

    def testEntryWithParent(self):
        """put_manifest creates entries with a parent."""
        from hct.manifest import Manifest, ManifestTarEntry, ManifestPatchEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest.append(ManifestPatchEntry("foo.patch.gz"))
        manifest[-1].parent = manifest[0]

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[-1].parent, 1)

    def testEntryWithoutParent(self):
        """put_manifest creates entries without a parent."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].parent, None)

    def testCreatesDirEntry(self):
        """put_manifest creates a dir entry."""
        from hct.manifest import Manifest, ManifestDirEntry
        manifest = Manifest()
        manifest.append(ManifestDirEntry("foo/"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.DIR)

    def testCreatesCopyEntry(self):
        """put_manifest creates a copy entry."""
        from hct.manifest import Manifest, ManifestCopyEntry
        manifest = Manifest()
        manifest.append(ManifestCopyEntry("foo/"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.COPY)

    def testCreatesFileEntry(self):
        """put_manifest creates a file entry."""
        from hct.manifest import Manifest, ManifestFileEntry
        manifest = Manifest()
        manifest.append(ManifestFileEntry("foo.txt"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.FILE)

    def testCreatesTarEntry(self):
        """put_manifest creates a tar entry."""
        from hct.manifest import Manifest, ManifestTarEntry
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.TAR)

    def testCreatesZipEntry(self):
        """put_manifest creates a zip entry."""
        from hct.manifest import Manifest, ManifestZipEntry
        manifest = Manifest()
        manifest.append(ManifestZipEntry("foo.zip.gz"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.ZIP)

    def testCreatesPatchEntry(self):
        """put_manifest creates a patch entry."""
        from hct.manifest import Manifest, ManifestPatchEntry
        manifest = Manifest()
        manifest.append(ManifestPatchEntry("foo.patch"))

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.lp.dbschema import ManifestEntryType
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(obj.entries[0].entrytype, ManifestEntryType.PATCH)

    def testEntryOnBranch(self):
        """put_manifest creates and assigns branch objects."""
        from hct.manifest import Manifest, ManifestTarEntry
        from hct.branch import Branch
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].branch = Branch("%s/foo--bar--0" % self.archive)

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_branch_from
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(get_branch_from(obj.entries[0].branch),
                          "%s/foo--bar--0" % self.archive)

    def testEntryOnExistingBranch(self):
        """put_manifest uses existing branch objects."""
        from hct.manifest import Manifest, ManifestTarEntry
        from hct.branch import Branch
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].branch = Branch("gnome@arch.ubuntu.com/evolution--MAIN--0")

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_branch_from
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(get_branch_from(obj.entries[0].branch),
                          "gnome@arch.ubuntu.com/evolution--MAIN--0")

    def testEntryOnChangeset(self):
        """put_manifest creates and assigns changeset objects."""
        from hct.manifest import Manifest, ManifestTarEntry
        from hct.branch import Branch, Changeset
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].branch = Branch("%s/foo--bar--0" % self.archive)
        manifest[-1].changeset = Changeset("%s--base-0" % manifest[-1].branch)

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_changeset_from
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(get_changeset_from(obj.entries[0].changeset),
                          "%s/foo--bar--0--base-0" % self.archive)

    def testEntryOnExistingChangeset(self):
        """put_manifest uses existing changeset objects."""
        from hct.manifest import Manifest, ManifestTarEntry
        from hct.branch import Branch, Changeset
        manifest = Manifest()
        manifest.append(ManifestTarEntry("foo.tar.gz"))
        manifest[-1].branch = Branch("mozilla@arch.ubuntu.com/mozilla--release--0.9.2")
        manifest[-1].changeset = Changeset("%s--base-0" % manifest[-1].branch)

        from canonical.launchpad.hctapi import put_manifest, get_object
        put_manifest("lp:///products/netapplet/1.0", manifest)

        from canonical.launchpad.database import Manifest as db_Manifest
        from canonical.launchpad.hctapi import get_changeset_from
        obj = get_object("lp:///products/netapplet/1.0").manifest
        self.assertEquals(get_changeset_from(obj.entries[0].changeset),
                          "mozilla@arch.ubuntu.com/mozilla--release--0.9.2--base-0")

    def testUrlDoesntExist(self):
        """put_manifest raises LaunchpadError if the url doesn't exist."""
        from hct.manifest import Manifest
        manifest = Manifest()

        from canonical.launchpad.hctapi import put_manifest, LaunchpadError
        self.assertRaises(LaunchpadError, put_manifest,
                          "lp:///products/wibble/1.0", manifest)

    def testUrlNotReleasable(self):
        """put_manifest raises LaunchpadError if the url isn't releasable."""
        from hct.manifest import Manifest
        manifest = Manifest()

        from canonical.launchpad.hctapi import put_manifest, LaunchpadError
        self.assertRaises(LaunchpadError, put_manifest,
                          "lp:///distros/ubuntu", manifest)

# Disabled hctapi tests until hctapi is fixed for the branches changes. See bug
# #4117. -- Robert Collins 2005-11-02

#register(__name__)

# Temporary hack to make the test runner happy until the register() statement
# can be uncommented. See #4117. -- Robert Collins 2005-11-02
def test_suite():
    import unittest
    return unittest.TestSuite()

"""Launchpad Database.

This module provides support for reading and writing manifest information
directly to and from the Launchpad database.


URL scheme
----------

The URL scheme used by the Launchpad Database backend is 'lp:///'.  The
host portion is unusued and should either be ommitted or left empty, it
may be used in future to identify the PostgreSQL server and database to
connect to.

The path portion of the URL specifies the location of the object within
the database schema, and can refer to an abstract object such as a product
or distribution or be resolved to a manifest.

To specify a product, or release of a product the following format should
be used:
| /products/PRODUCT[/RELEASE]

To specify a distribution, release of a distribution or the currently
published version of a source package within that release the following
format should be used:
| /distros/DISTRO[/DISTRORELEASE[+sources/][/PACKAGE]]

(Note that specifying a distribution or distribution release is not
sufficient to retrieve a manifest).

To specify the currently published version of a source package within
the current development release of a distribution, or a particular version
of a source package within that distribution the following format should
be used:
| /distros/DISTRO/PACKAGE[/RELEASE]

The path may also be shortened to simply stating a distribution,
distribution release, source package name (resolved against the default
distribution - ubuntu) or product to jump straight to that part of the
URL provided the name is unique (names are resolved in that order).

Examples:
| lp:///products/netapplet
| lp:///products/netapplet/1.0
| lp:///mozilla-firefox
| lp:///mozilla-firefox/0.9.2
| lp:///distros/ubuntu/hoary/+sources/netapplet
| lp:///distros/ubuntu/hoary/evolution
| lp:///distros/ubuntu/netapplet
| lp:///distros/ubuntu/netapplet/1.0-1
| lp:///ubuntu/hoary/evolution
| lp:///ubuntu/netapplet
| lp:///netapplet/1.0-1
"""

__metaclass__  = type

import urlparse

from psycopg import IntegrityError
from sqlobject.main import SQLObjectNotFound

import canonical.lp

from pybaz import NameParser
from canonical.lp.dbschema import ManifestEntryType, RevisionControlSystems
from canonical.librarian.db import Library
from canonical.database.sqlbase import ZopelessTransactionManager
from canonical.database.constants import UTC_NOW
from canonical.launchpad.database import (
     Product, ProductSeries, ProductRelease,
     Distribution, DistroRelease, DistroReleaseSet,
     SourcePackageName, SourcePackage, SourcePackageRelease,
     Manifest, ManifestEntry, Archive, ArchNamespace, Branch, Changeset
     )
from canonical.launchpad.database.archbranch import VersionMapper
from hct.url import register_backend, UrlError


# Register this backend against the URL schemes we serve
urlparse.uses_netloc.append("lp")
urlparse.uses_netloc.append("launchpad")
register_backend(__name__, ( "lp", "launchpad" ), 100)

# Default distribution
default_distro = "ubuntu"

# Mapping from ManifestEntryType to typeName
MANIFEST_ENTRY_TYPE_MAP = (
    ( ManifestEntryType.DIR.value,    "dir"   ),
    ( ManifestEntryType.COPY.value,   "copy"  ),
    ( ManifestEntryType.FILE.value,   "file"  ),
    ( ManifestEntryType.TAR.value,    "tar"   ),
    ( ManifestEntryType.ZIP.value,    "zip"   ),
    ( ManifestEntryType.PATCH.value,  "patch" ),
    )


class LaunchpadError(UrlError):
    """URL error caused by the Launchpad backend."""
    pass

class SourcePackageReleaseInDistroRelease:
    """SourcePackageRelease and DistroRelease.

    We use this class instead of a SourcePackageRelease directly as we
    always need to remember which DistroRelease it came from.
    """

    def __init__(self, sourcepackagerelease, distrorelease):
        self.sourcepackagerelease = sourcepackagerelease
        self.distrorelease = distrorelease

    def __repr__(self):
        """Return a debugging representation of the class."""
        text = "<%s %r %r>" % (type(self).__name__,
                               str(self.sourcepackagerelease.name),
                               str(self.distrorelease.name))
        return text

    @property
    def sourcepackage(self):
        """SourcePackage object."""
        return SourcePackage(self.sourcepackagerelease.sourcepackagename,
                             self.distrorelease)


def split_path(url_path):
    """Return the parts of the URL path after canonicalisation.

    Canonicalises the URL path by removing empty parts, /./ and resolving
    /../  etc.  Then splits it and returns the parts as an array.
    """
    parts = []
    for part in url_path.split("/"):
        if not len(part):
            continue
        elif part == ".":
            continue
        elif part == "..":
            if len(parts):
                parts.pop()
        else:
            parts.append(part)

    return parts


def get_ztm():
    """Return ZopelessTransactionManager."""
    if ZopelessTransactionManager._installed is None:
        return canonical.lp.initZopeless()
    else:
        return ZopelessTransactionManager._installed

def begin_transaction():
    """Begin transaction and return ZopelessTransactionManager."""
    ztm = get_ztm()
    ztm.begin()
    return ztm

def end_transaction(commit=False):
    """End current transaction."""
    ztm = get_ztm()
    if commit:
        ztm.commit()
    else:
        ztm.abort()

def get_object(url, resolve=False):
    """Return database object at the given URL.

    This function returns the database object actually referenced by the
    URL, i.e. the Product, ProductSeries, Distro, etc.  To obtain a
    record that can hold a Manifest, call resolve_object() on the return
    value or simply pass resolve=True to this call.

    Returns SQLobject record object.
    """
    (scheme, netloc, url_path, query, fragment) = urlparse.urlsplit(url, "lp")

    parts = split_path(url_path)
    if not len(parts):
        raise LaunchpadError("Malformed URL, path expected: '%s'" % url)

    obj = None
    while len(parts):
        part = parts.pop(0)

        if obj is None:
            # The first part of a URL can be either an explicit starting
            # point in the schema (products or distros) or the name of
            # anything else.  Check for the former first, then go through
            # the tables in precedence order looking for the records.
            if part == "products" or part == "upstream":
                try:
                    product = parts.pop(0)
                    obj = Product.byName(product)
                except IndexError:
                    raise LaunchpadError("Product missing in URL: '%s'" % url)
                except SQLObjectNotFound:
                    raise LaunchpadError("Product '%s' not found in URL: '%s'"
                                         % (product, url))
            elif part == "distros":
                try:
                    distro = parts.pop(0)
                    obj = Distribution.byName(distro)
                except IndexError:
                    raise LaunchpadError("Distribution missing in URL: '%s'"
                                         % url)
                except SQLObjectNotFound:
                    raise LaunchpadError("Distribution '%s' not found in URL: '%s'"
                                         % (distro, url))
            else:
                try:
                    obj = Distribution.byName(part)
                    continue
                except SQLObjectNotFound:
                    pass

                objs = DistroReleaseSet().findByName(part)
                if objs.count() == 1:
                    obj = objs[0]
                    continue

                objs = DistroReleaseSet().findByVersion(part)
                if objs.count() == 1:
                    obj = objs[0]
                    continue

                try:
                    name = SourcePackageName.byName(part)
                    # FIXME "current" distro?
                    distro = Distribution.byName(default_distro)
                    obj = distro.getSourcePackage(name)
                    continue
                except SQLObjectNotFound:
                    pass
                except IndexError:
                    pass

                try:
                    obj = Product.byName(part)
                    continue
                except SQLObjectNotFound:
                    pass

                raise LaunchpadError("URL not found: '%s'" % url)

        elif isinstance(obj, Product):
            # The part of a URL after a product can be either a release
            # version or a series name, check series first as that's less
            # specific and you can always specify /2.0/2.0 to get to the
            # release.
            try:
                obj = obj.getSeries(part)
            except KeyError:
                try:
                    obj = obj.getRelease(part)
                except IndexError:
                    raise LaunchpadError("Product series or release '%s' not found in URL: '%s'"
                                         % (part, url))

        elif isinstance(obj, ProductSeries):
            # The part of a URL after a product series is always a release
            # version.
            try:
                obj = obj.getRelease(part)
            except KeyError:
                raise LaunchpadError("Release '%s' not found in URL: '%s'"
                                     % (part, url))

        elif isinstance(obj, ProductRelease):
            # Nothing is permitted after a release version.
            raise LaunchpadError("Malformed URL, nothing expected after release: '%s'" \
                                 % url)

        elif isinstance(obj, Distribution):
            # The part of a URL after a distribution can be either a release
            # name or a source package name, check release name first as that's
            # less specific.
            try:
                obj = obj.getRelease(part)
                continue
            except KeyError:
                pass

            try:
                name = SourcePackageName.byName(part)
                obj = obj.getSourcePackage(name)
                continue
            except SQLObjectNotFound:
                pass
            except IndexError:
                pass

            raise LaunchpadError("Distribution release or source package '%s' not found in URL: '%s'"
                                 % (part, url))

        elif isinstance(obj, DistroRelease):
            # The part of a URL after a distribution release is always a
            # source package name, for which the currently published version
            # is returned.  A +sources part is optional for compatibility
            # with the Launchpad webapp URLs.
            if part == "+sources":
                if len(parts):
                    part = parts.pop(0)
                else:
                    continue

            try:
                name = SourcePackageName.byName(part)
            except SQLObjectNotFound:
                raise LaunchpadError("Source package '%s' not found in URL: '%s'"
                                     % (part, url))

            objs = obj.getPublishedReleases(name)
            if len(objs) < 1:
                raise LaunchpadError("Source package '%s' not released in URL: '%s'"
                                     % (part, url))

            spr = objs[-1].sourcepackagerelease
            obj = SourcePackageReleaseInDistroRelease(spr, obj)

        elif isinstance(obj, SourcePackage):
            # The part of the URL after a source package is always a
            # source package release.  FIXME this should use
            # SourcePackageHistory or similar
            rels = [ _r for _r in obj.releases if _r.version == part ]
            if not len(rels):
                raise LaunchpadError("Source package release '%s' not found in URL: '%s'"
                                     % (part, url))

            obj = SourcePackageReleaseInDistroRelease(rels[-1],
                                                      obj.distrorelease)

        else:
            raise LaunchpadError("Malformed URL, '%s' unexpected in URL: '%s'"
                                 % (part, url))

    if resolve:
        try:
            return resolve_object(obj)
        except UrlError:
            raise LaunchpadError("URL not found: '%s'" % url)
    else:
        return obj

def where_am_i(obj):
    """Return URL for the database object given.

    This function accepts SQLObject record objects and returns the full
    URL that will retrieve that object's manifest from the database.
    When given higher-level objects such as Products, the latest release
    etc. are not resolved in order to allow them to be resolved at query
    time.

    This function _does_not_ accept a Manifest object, as they can be
    tied to many different places; you need to hold on to the object that
    gave you the manifest in the first place.

    Returns URL.
    """
    parts = []

    if isinstance(obj, ProductRelease):
        parts.append(obj.version)
        obj = obj.productseries

    if isinstance(obj, ProductSeries):
        parts.append(obj.name)
        obj = obj.product

    if isinstance(obj, Product):
        parts.append(obj.name)
        parts.append("products")
        obj = None


    if isinstance(obj, SourcePackageReleaseInDistroRelease):
        parts.append(obj.sourcepackagerelease.version)
        obj = obj.sourcepackage

    if isinstance(obj, SourcePackageRelease):
        parts.append(obj.version)
        obj = SourcePackage(obj.sourcepackagename, obj.uploaddistrorelease)

    if isinstance(obj, SourcePackage):
        parts.append(obj.name)
        obj = obj.distro


    if isinstance(obj, DistroRelease):
        parts.append(obj.name)
        obj = obj.distribution

    if isinstance(obj, Distribution):
        parts.append(obj.name)
        parts.append("distros")
        obj = None


    if not len(parts):
        raise LaunchpadError("Unable to determine URL for object: %r" % obj)

    parts.reverse()
    url = urlparse.urlunsplit(("lp", None, "/".join(parts), None, None))
    return url

def resolve_object(obj):
    """Resolve database object to one that can hold a manifest.

    Starts at the SQLObject record object given and drills down until it
    reaches a 'latest release' underneath it that can hold a manifest,
    where or not it does.

    Returns new object.
    """
    if isinstance(obj, Product):
        try:
            obj = obj.releases[-1]
        except IndexError:
            raise LaunchpadError("No releases in product: '%s'" % obj.name)

    if isinstance(obj, ProductSeries):
        try:
            obj = obj.releases[-1]
        except IndexError:
            raise LaunchpadError("No releases in series: '%s'" % obj.name)

    if isinstance(obj, ProductRelease):
        return obj


    if isinstance(obj, SourcePackage):
        if obj.currentrelease is None:
            raise LaunchpadError("No current development release of package: '%s'" % obj.name)

        obj = SourcePackageReleaseInDistroRelease(obj.currentrelease,
                                                  obj.distrorelease)

    if isinstance(obj, SourcePackageReleaseInDistroRelease):
        return obj.sourcepackagerelease

    if isinstance(obj, SourcePackageRelease):
        return obj


    raise LaunchpadError("Unable to resolve object to manifest holder: %r" % obj)

def get_branch_from(obj):
    """Get hct Branch from database object.

    The object should be a database Branch record object, it is converted
    to an HCT object with the same information.

    Returns hct.branch.Branch class.
    """
    if obj is None:
        return None

    # FIXME we don't do anything to use the same branch objects again and
    # again; it's probably not a problem anymore, but still...
    from hct.branch import Branch
    return Branch(obj.getPackageName())

def get_changeset_from(obj):
    """Get hct Changeset from database object.

    The object should be a database Changeset record object, it is converted
    to an HCT object with the same information.

    Returns hct.changeset.Changeset class.
    """
    if obj is None:
        return None

    from hct.branch import Changeset
    return Changeset(obj.getPackageName())

def get_manifest_from(obj):
    """Get hct Manifest from database object.

    The object should be a database Manifest record object, it is
    converted to an HCT object with the same entries.

    Returns hct.manifest.Manifest class.
    """
    if obj is None:
        return None

    from hct.manifest import Manifest, new_manifest_entry
    manifest = Manifest(new_id=str(obj.uuid))

    sequence_map = {}
    patch_on_map = []

    for obj_entry in obj.entries:
        type_map = dict(MANIFEST_ENTRY_TYPE_MAP)
        if obj_entry.entrytype not in type_map:
            raise LaunchpadError("Unknown manifest entry type from database: %d"
                                 % obj_entry.entrytype)

        # Create ManifestEntry and set up properties
        entry = new_manifest_entry(type_map[obj_entry.entrytype],
                                   obj_entry.path)
        entry.dirname = obj_entry.dirname
        entry.branch = get_branch_from(obj_entry.branch)
        entry.changeset = get_changeset_from(obj_entry.changeset)
        manifest.append(entry)

        # Keep track of sequence numbers and patch_on settings
        sequence_map[obj_entry.sequence] = entry
        if obj_entry.patchon is not None:
            patch_on_map.append((obj_entry.patchon, entry))

    # Map patch_on to sequence numbers
    for patch_on, entry in patch_on_map:
        if patch_on not in sequence_map:
            raise LaunchpadError("Manifest entry parent not in sequence: '%s'"
                                 % entry.path)

        entry.patch_on = sequence_map[patch_on]

    return manifest


def get_manifest(url):
    """Retrieve the manifest with the URL given."""
    begin_transaction()
    try:
        obj = get_object(url, resolve=True)
        manifest = get_manifest_from(obj.manifest)
        if manifest is None:
            raise LaunchpadError("No manifest at URL: '%s'" % url)

        return manifest
    finally:
        end_transaction()

def get_release(url, release):
    """Return the URL of the release of the product or package given.

    If the release does not exist, this function returns None.
    """
    begin_transaction()
    try:
        obj = get_object(url)
        if isinstance(obj, Product):
            try:
                rel = obj.getRelease(release)
            except IndexError:
                return None
        elif isinstance(obj, ProductSeries):
            try:
                rel = obj.getRelease(release)
            except KeyError:
                return None
        elif isinstance(obj, SourcePackage):
            # FIXME more intelligence for version parsing (using sourcerer.deb)
            # and this should use SourcePackageHistory
            rels = [ _r for _r in obj.releases
                     if (_r.version == release
                         or _r.version.startswith("%s-" % release)) ]
            if not len(rels):
                return None

            rel = SourcePackageReleaseInDistroRelease(rels[-1], obj.distrorelease)
        else:
            raise LaunchpadError("Unable to determine release for object: %r" % obj)

        return where_am_i(rel)
    finally:
        end_transaction()

def get_package(url, distro_url=None):
    """Return the URL of the package in the given distro.

    Takes the product, source package or release at url and returns the
    equivalent in the distribution or distribution release given.

    If distro_url is omitted or None, the upstream product is returned.

    Returns URL of equivalent package.
    """
    begin_transaction()
    try:
        obj = get_object(url)
        version = None
        productseries = None

        # Locate the productseries
        if isinstance(obj, ProductRelease):
            version = obj.version
            productseries = obj.productseries

        if isinstance(obj, ProductSeries):
            productseries = obj

        if isinstance(obj, SourcePackageReleaseInDistroRelease):
            version = obj.sourcepackagerelease.version
            obj = obj.sourcepackage

        if isinstance(obj, SourcePackageRelease):
            version = obj.version
            obj = SourcePackage(obj.sourcepackagename, obj.uploaddistrorelease)

        if isinstance(obj, SourcePackage):
            productseries = obj.productseries

        if productseries is None:
            raise LaunchpadError("Unable to resolve URL to product series: '%s'" % url)


        # Return the productseries if no distro was passed
        if distro_url is None:
            return where_am_i(productseries)

        # Locate the distribution
        distro = get_object(distro_url)

        # Find the sourcepackage in the given distrorelease
        if isinstance(distro, DistroRelease):
            package = productseries.getPackage(distro)
            if not package.currentrelease:
                raise LaunchpadError("Source package '%s' not published in '%s'"
                                     % (url, distro_url))
            return where_am_i(SourcePackageReleaseInDistroRelease(
                package.currentrelease, distro))

        # Or in the distribution
        elif isinstance(distro, Distribution):
            package = productseries.getPackage(distro.currentrelease)
            if version is not None:
                return get_release(where_am_i(package), version)
            else:
                return where_am_i(package)

        else:
            raise LaunchpadError("Not a distribution or distro release: '%s'"
                                 % distro_url)
    finally:
        end_transaction()

def get_branch(url):
    """Return branch associated with URL given.

    Returns a Branch object or None if no branch associated. Note that the
    url should be for a productseries
    """
    begin_transaction()
    try:
        obj = get_object(get_package(url))
        if obj.branch is not None:
            return get_branch_from(obj.branch)
        else:
            return None
    finally:
        end_transaction()

def identify_file(ref_url, size, digest, upstream=False):
    """Return URLs and Manifests for a file with the details given.

    Returns a list of tuples of (url, manifest) for each product and
    source package release that include a file with the same size and
    SHA1 digest given.

    If upstream is True, only 'upstream' products with a manifest will
    be returned.
    """
    begin_transaction()
    try:
        library = Library()
        file_ids = library.lookupBySHA1(digest)
        if not len(file_ids):
            raise LaunchpadError("File not found: '%s' (%d)" % (digest, size))

        results = []
        for file_id in file_ids:
            for alias_id, filename, mime_type in library.getAliases(file_id):
                alias = library.getByAlias(alias_id)

                results.extend([ obj for obj in alias.products ])
                if not upstream:
                    results.extend([ obj for obj in alias.sourcepackages ])

        results = [ (where_am_i(obj), get_manifest_from(obj.manifest))
                    for obj in results if (not upstream
                                           or obj.manifest is not None) ]
        if not len(results):
            raise LaunchpadError("No source for file found: '%s' (%d)"
                                 % (digest, size))

        return results
    finally:
        end_transaction()


def put_manifest(url, manifest):
    """Add new manifest under the URL given."""
    success = False
    begin_transaction()
    try:
        obj = get_object(url)
        if isinstance(obj, SourcePackageReleaseInDistroRelease):
            obj = obj.sourcepackagerelease
        if not (isinstance(obj, ProductRelease)
                or isinstance(obj, SourcePackageRelease)):
            raise LaunchpadError("Unable to associate a manifest with: '%s'" % url)

        sequence = 0
        sequence_map = {}
        patch_on_map = []

        obj.manifest = Manifest(uuid=manifest.id)
        for entry in manifest:
            type_map = dict([ (_t, _v) for _v, _t in MANIFEST_ENTRY_TYPE_MAP ])
            if entry.typeName() not in type_map:
                raise LaunchpadError("Unknown manifest entry type from import: %s"
                                     % entry.typeName())

            sequence += 1
            obj_entry = ManifestEntry(manifestID=obj.manifest.id,
                                      sequence=sequence,
                                      entrytype=type_map[entry.typeName()],
                                      path=entry.path,
                                      branchID=None,
                                      changesetID=None,
                                      patchon=None,
                                      dirname=entry.dirname)

            # FIXME this is the "hard" way
            # a lot of the heavy lifting here belongs in Launchpad interfaces
            if entry.branch is not None:
                np = NameParser(entry.branch)

                # Archive table entry
                objs = Archive.selectBy(name=np.get_archive())
                if objs.count():
                    archive = objs[0]
                else:
                    archive = Archive(name=np.get_archive(), visible=True,
                                      title="", description="")

                # ArchNamespace table entry
                objs = ArchNamespace.selectBy(archiveID=archive.id,
                                              category=np.get_category(),
                                              branch=np.get_branch(),
                                              version=np.get_version())
                if objs.count():
                    namespace = objs[0]
                else:
                    namespace = ArchNamespace(archiveID=archive.id, visible=True,
                                              category=np.get_category(),
                                              branch=np.get_branch(),
                                              version=np.get_version())

                # Branch table entry
                objs = Branch.selectBy(archnamespaceID=namespace.id)
                if objs.count():
                    branch = objs[0]
                else:
                    branch = Branch(archnamespaceID=namespace.id,
                                    title="", description="")

                obj_entry.branch = branch

            if entry.changeset is not None:
                np = NameParser(entry.changeset)

                objs = Changeset.selectBy(branchID=branch.id,
                                          name=np.get_patchlevel())
                if objs.count():
                    changeset = objs[0]
                else:
                    changeset = Changeset(branchID=branch.id,
                                          name=np.get_patchlevel(),
                                          datecreated=UTC_NOW,
                                          logmessage="")

                obj_entry.changeset = changeset

            # Keep track of sequence numbers and patchon settings
            sequence_map[entry] = sequence
            if hasattr(entry, "patch_on") and entry.patch_on is not None:
                patch_on_map.append((entry.patch_on, obj_entry))

        # Map patch_on to sequence numbers
        for patch_on, obj_entry in patch_on_map:
            if patch_on not in sequence_map:
                raise LaunchpadError("Manifest entry parent not in sequence: '%s'"
                                     % obj_entry.path)

            obj_entry.patchon = sequence_map[patch_on]

        success = True
    finally:
        end_transaction(commit=success)

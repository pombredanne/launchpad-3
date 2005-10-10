# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Functions used in Rosetta scripts.

Some of the tests for this file are elsewhere. See:

    lib/canonical/launchpad/doc/po-attach.txt
    lib/canonical/launchpad/scripts/ftests/test_po_attach.py
"""

__metaclass__ = type

import doctest
import os
import urllib2
import pytz
import cPickle as pickle
import time

from zope.component import getUtility

from canonical.launchpad import helpers
from canonical.launchpad.interfaces import (
    IDistributionSet, IPersonSet, ISourcePackageNameSet, IPOTemplateSet,
    IPOTemplateNameSet, IBinaryPackageNameSet, IPOFileSet, LanguageNotFound,
    IPOFile, IPOTemplate)
from canonical.sourcerer.deb.version import Version
from canonical.database.constants import UTC_NOW

class URLOpenerError(Exception):
    pass

class URLOpener:
    """Open URLs as file-like objects.

    This class is used to allow functional testing of scripts that fetch
    things from the network.
    """

    def open(self, url):
        try:
            return urllib2.urlopen(url)
        except urllib2.HTTPError, e:
            raise URLOpenerError(str(e))

def fetch_date_list(urlopener, archive_uri, logger):
    uri = archive_uri + '/directories.txt'

    try:
        date_file = urlopener.open(uri)
    except URLOpenerError, e:
        logger.error('Got an error fetching the file %s: %s' % (uri, e))
        raise

    date_list = []

    for line in date_file.readlines():
        date_list.append(line.strip())

    return date_list

def fetch_catalog(urlopener, archive_uri, date, logger):
    uri = "%s/%s/translations.txt" % (archive_uri, date)

    try:
        catalog_file = urlopener.open(uri)
    except URLOpenerError, e:
        logger.error('Got an error fetching the file %s: %s' %
            (uri, e))
        raise

    return parse_catalog(catalog_file)

def parse_catalog(catalog):
    r"""Parse a catalog of package translations.

    Return a list of dictionaries.

    >>> parse_catalog(['foo: bar'])
    [{'foo': 'bar'}]

    >>> catalog = parse_catalog([
    ...     'foo: bar\n',
    ...     'something: whatever\n',
    ...     '\n',
    ...     'key: value\n',
    ...     'speed: boat\n'])
    >>> catalog[0]['foo']
    'bar'
    >>> catalog[0]['something']
    'whatever'
    >>> catalog[1]['key']
    'value'
    >>> catalog[1]['speed']
    'boat'
    """

    res = []
    entry = {}

    for line in catalog:
        if line.isspace():
            # Next record.
            res.append(entry)
            entry = {}
        else:
            (key, value) = line.split(':', 1)
            entry[key] = value.strip()

    if len(entry) > 0:
        res.append(entry)

    return res

def get_test_tarball():
    """Create a translation tarball for doctests.

    >>> tarball = get_test_tarball()
    >>> for member in tarball.getmembers():
    ...     print member.name
    sources/
    sources/po/
    sources/po/cy.po
    sources/po/es.po
    sources/po/uberfrob.pot
    uberfrob/
    uberfrob/usr/
    uberfrob/usr/share/
    uberfrob/usr/share/locales/
    uberfrob/usr/share/locales/cy/
    uberfrob/usr/share/locales/cy/LC_MESSAGES/
    uberfrob/usr/share/locales/cy/LC_MESSAGES/uber.mo
    uberfrob/usr/share/locales/es/
    uberfrob/usr/share/locales/es/LC_MESSAGES/
    uberfrob/usr/share/locales/es/LC_MESSAGES/uber.mo
    """

    return helpers.RosettaWriteTarFile.files_to_tarfile({
        'uberfrob/usr/share/locales/cy/LC_MESSAGES/uber.mo':
            'whatever',
        'uberfrob/usr/share/locales/es/LC_MESSAGES/uber.mo':
            'whatever',
        'sources/po/uberfrob.pot':
            'whatever',
        'sources/po/cy.po':
            'whatever',
        'sources/po/es.po':
            'whatever',
        })

def get_domain_binarypackages(tarball):
    """Return a dictionary mapping domains to binary package names.

    >>> tarball = get_test_tarball()
    >>> get_domain_binarypackages(tarball)
    {'uber': ['uberfrob']}
    >>> tarball.close()
    """

    names = tarball.getnames()

    domains = {}

    for name in names:
        if name.startswith('sources/'):
            continue

        if name.endswith('.mo'):
            mofile = os.path.basename(name)
            domain, extension = os.path.splitext(mofile)
            binarypackage = name.split('/', 1)[0]
            if domain in domains:
                if binarypackage not in domains[domain]:
                    domains[domain].append(binarypackage)
            else:
                domains[domain] = [binarypackage]
    return domains

class TranslationDomain:
    def __init__(self, name):
        self.domainname = name
        # The contents of the PO template.
        self.pot_contents = None
        # The contents of the PO files, indexed by language code.
        self.po_files = {}
        # Paths where we have a PO template for this domain in the source
        # package build.
        self.domain_paths = []
        # The filename of the PO template.
        self.pot_filename = None
        # A list of binary packages that have MO files for this translation
        # domain.
        self.binary_packages = []

class DomainTarballError(Exception):
    """Raised when an error occurs when scanning a translation domain tarball.
    """

def find_pot_and_po_files(tarball):
    """Return a list of all .pot and .po files in a tarball."""

    pot_files = []
    po_files = []

    for name in tarball.getnames():
        if name.endswith('.pot'):
            pot_files.append(name)
        elif name.endswith('.po'):
            po_files.append(name)

    return pot_files, po_files

def get_domains_from_tarball(distrorelease, sourcepackagename, tarball):
    """Return a list with all .pot and .po files from a tarball.

    The parameters are:
        * distrorelease: The distrorelease where this tarball belongs.
        * sourcepackage: the name of the source package the tarball was
        generated from.
        * tarball: the tarball itself.

    Return a list of TranslationDomain objects.

    Raise DomainTarballError if there is any error with the tarball structure.

    How PO templates are matched to translation domains:

     - Debconf templates are treated specially.
     - If there's only one PO template and only one domain name, we assume
       they match.
     - We check to see if the PO template matches one in the database already.
     - We check to see if any domain name matches the filename of the PO
       template, and if one does, we use its name.
     - Otherwise, create a translation domain with a generated name so that it
       can be reviewed by a human.

    The doctest for this function is at canonical/launchpad/doc/rosetta.py
    """

    domains = []


    # Get a mapping of domain names to binary package names.

    domain_binarypackages = get_domain_binarypackages(tarball)

    # Get lists of the PO templates and PO files in the tarball.

    pot_files, po_files = find_pot_and_po_files(tarball)

    # Get the list of PO templates which are not package configuration
    # templates.

    non_pkgconf_templates = [
        template
        for template in pot_files
        if not template.startswith('source/debian/po/')]

    assert len(pot_files) - len(non_pkgconf_templates) in (0, 1)

    # Prefix and suffix are used when we need to generate a name for a PO
    # template (the fallback case).

    prefix = 'review-%s-%s-' % (
        distrorelease.name, sourcepackagename.name)
    suffix = 1

    # For each PO template, try to find a domain which matches it.

    found_domains = []
    found_paths = []

    for pot_file in pot_files:
        pot_dirname, pot_filename = os.path.split(pot_file)
        assert pot_dirname.startswith('source/')
        pot_dirname = pot_dirname[len('source/'):]
        domain_name = None

        if pot_dirname in found_paths:
            # We have alredy a .pot file in this path, we don't handle this
            # situation yet, so the import is not done.
            raise DomainTarballError(
                "The source package %s for %s has more than one .pot file"
                " in source/%s. Ignoring the tarball." %
                (sourcepackagename.name, distrorelease.name, pot_dirname))

        found_paths.append(pot_dirname)

        if pot_dirname == 'debian/po':
            # It's a Debconf PO template.
            domain_name = 'pkgconf-%s' % sourcepackagename.name
        elif len(non_pkgconf_templates) == len(domain_binarypackages) == 1:
            # We have only one non-Debconf PO template and one domain,
            # therefore the mapping is direct.
            domain_name = domain_binarypackages.keys()[0]
        else:
            # Check to see if there is already a PO template in the database
            # with the same path and the same filename as pot_filename.
            potemplateset = getUtility(IPOTemplateSet)
            existing_potemplates = potemplateset.getSubset(
                sourcepackagename=sourcepackagename,
                distrorelease=distrorelease)

            for potemplate in existing_potemplates:
                if (potemplate.path == pot_dirname and
                    potemplate.filename == pot_filename):
                    domain_name = potemplate.potemplatename.translationdomain

            if domain_name is None:
                # No PO templates in the database matched; check to see if
                # there is a domain with a name that matches the filename of
                # this PO template.
                for domain in domain_binarypackages:
                    if (pot_file.endswith('%s.pot' % domain) and
                        domain not in found_domains):
                        domain_name, ext = os.path.splitext(pot_filename)

            if domain_name is None:
                # The PO template didn't match any PO templates that already
                # exist in the database for this distrorelease, nor any
                # domains in the tarball, so we look at previous release
                # for this .pot file inside pot_dirname.
                previous_distrorelease = distrorelease.parentrelease

                if previous_distrorelease is not None:
                    previous_potemplates = potemplateset.getSubset(
                        sourcepackagename=sourcepackagename,
                        distrorelease=previous_distrorelease)
                    for potemplate in previous_potemplates:
                        if (potemplate.path == pot_dirname and
                            potemplate.filename == pot_filename):
                            domain_name = \
                                potemplate.potemplatename.translationdomain

                if domain_name is None:
                    # The .pot file does not exists either in the previous
                    # distribution. Use the fall back method that generates a
                    # name for the PO template to be reviewed later.
                    for potemplate in existing_potemplates:
                        # Check if we already have a potemplatename with the same
                        # prefix so we don't mix two different .pot files when we
                        # don't know their real translation domain.
                        potemplatename = potemplate.potemplatename
                        translationdomain = potemplatename.translationdomain
                        if translationdomain.startswith(prefix):
                            number = int(translationdomain[len(prefix):])
                            if number >= suffix:
                                suffix = number + 1
                    domain_name = '%s%d' % (prefix, suffix)
                    # Update the suffix so that the next pot file in this case
                    # gets the right value.
                    suffix = suffix + 1

        found_domains.append(domain_name)

        # Create the translation domain object.
        td = TranslationDomain(domain_name)
        td.pot_contents = tarball.extractfile(pot_file).read()
        td.pot_filename = pot_filename
        td.domain_paths.append(pot_dirname)

        if domain_name in domain_binarypackages:
            td.binary_packages = domain_binarypackages[domain_name]

        # Search for PO files which are in the same directory as the PO
        # template, and add them to the translation domain.
        for po_file in po_files:
            po_dirname, po_filename = os.path.split(po_file)
            if po_dirname == 'source/' + pot_dirname:
                lang_code, extension = os.path.splitext(po_filename)
                td.po_files[lang_code] = tarball.extractfile(po_file).read()

        domains.append(td)

    return domains


class AttachTranslationCatalog:
    """Attach the .po and .pot files of a set of tarballs into Rosetta."""

    def __init__(self, urlopener, base_uri, catalog, ztm, logger):
        """Initialize the AttachTranslationCatalog object.

        Get Four arguments, the base_uri where the files will be downloaded
        from, the catalog with all files to be attached, the Zope Transaction
        Manager and a logger for the warning/errors messages.
        """
        self.urlopener = urlopener
        self.base_uri = base_uri
        self.catalog = catalog
        self.ztm = ztm
        self.logger = logger
        self.missing_distributions = []
        self.missing_releases = []

    def get_distrorelease(self, distribution_name, release_name):
        """Get the distrorelease object for a distribution and a release."""

        if distribution_name in self.missing_distributions:
            return None

        if (distribution_name, release_name) in self.missing_releases:
            return None

        distributionset = getUtility(IDistributionSet)

        # Check that we have the needed distribution.
        try:
            distribution = distributionset[distribution_name]
        except KeyError:
            # We don't have this distribution in our database, print a
            # warning so we can add it later and return.
            self.logger.warning("No distribution called %s in the "
                                "database" % distribution_name)
            self.missing_distributions.append(distribution_name)
            return None

        # Check that we have the needed release for the current distribution
        try:
            return distribution[release_name]
        except KeyError:
            # We don't have this release for the current distribution in
            # our database, print a warning so we can add it later and
            # return.
            self.logger.warning("No release called %s for the "
                                "distribution %s in the database" % (
                                release_name, distribution_name))
            self.missing_distributions.append(
                (distribution_name, release_name))
            return None

    def get_sourcepackagename(self, sourcepackagename):
        """Get the SourcePackageName object for a given name."""

        sourcepackagenameset = getUtility(ISourcePackageNameSet)
        try:
            return sourcepackagenameset[sourcepackagename]
        except KeyError:
            # We don't have this sourcepackage in our database, print
            # a warning so we can add it later and return.
            self.logger.warning("No source package name '%s' in the "
                                "database" % sourcepackagename)
            return None

    def import_sourcepackage_release(self, sourcepackagename, release, file,
                                     version):
        """Import a tarball to a source package for a distribution release."""

        uri = self.base_uri + '/' + file
        self.logger.info("Getting %s" % uri)

        try:
            tarfile = self.urlopener.open(uri)
        except URLOpenerError, e:
            self.logger.error('Got an error fetching the file %s: %s' %
                (uri, e))
            return

        self.logger.debug("%s attached to %s sourcepackage" % (
                          uri, sourcepackagename.name))

        # Check to see if we have already imported this tarball successfully
        # inside this sourcepackagename and distrorelease.
        # We do it before the tarfile.read() so we don't download the file if
        # it's not needed.
        potemplateset = getUtility(IPOTemplateSet)
        potemplatesubset = potemplateset.getSubset(
            sourcepackagename=sourcepackagename, distrorelease=release)

        for pot in potemplatesubset:
            if pot.sourcepackageversion is not None:
                # The Version class comes from Sourcerer and helps us to
                # compare .deb package version strings. That class has a
                # __cmp__ method so we can compare a normal string with the
                # class.
                if Version(version) <= pot.sourcepackageversion:
                    self.logger.debug(
                        "This tarball or a newer one is already imported."
                        " Ignoring it.")
                    return

        tarball = helpers.string_to_tarfile(tarfile.read())

        try:
            domains = get_domains_from_tarball(
                release, sourcepackagename, tarball)
        except DomainTarballError, e:
            self.logger.warning("Error scanning tarball: %s" % str(e))
            return

        potemplatenameset = getUtility(IPOTemplateNameSet)

        # XXX
        # This should be done with a celebrity.
        #  -- Dafydd Harries, 2005/03/16
        personset = getUtility(IPersonSet)
        admins = personset.getByName('rosetta-admins')
        ubuntu_translators = personset.getByName('ubuntu-translators')

        for domain in domains:
            try:
                template = potemplatesubset[domain.domainname]
            except KeyError:
                # Get or create the PO template name.
                try:
                    potemplatename = potemplatenameset[domain.domainname]
                except KeyError:
                    self.logger.warning("Creating new PO template name '%s'" %
                        domain.domainname)
                    potemplatename = potemplatenameset.new(
                        translationdomain=domain.domainname,
                        title=domain.domainname)

                # Create the PO template.
                self.logger.warning(
                    "Creating new PO template '%s' for %s/%s" % (
                    domain.domainname, release.name, sourcepackagename.name))
                template = potemplatesubset.new(
                    potemplatename=potemplatename,
                    contents=domain.pot_contents,
                    owner=admins)
            else:
                # these are ALWAYS considered "published"
                template.attachRawFileData(domain.pot_contents, True, admins)

            # Choosing the shortest is used as a heuristic for selecting among
            # binary package names and domain paths.
            if domain.binary_packages:
                binarypackagenameset = getUtility(IBinaryPackageNameSet)
                best_binarypackage = helpers.getRosettaBestBinaryPackageName(
                    domain.binary_packages)

                try:
                    template.binarypackagename = (
                        binarypackagenameset[best_binarypackage])
                except KeyError:
                    self.logger.warning(
                        "No binary package name '%s' in the database." %
                        best_binarypackage)

                # Since the domain has binary packages, set this flag on the
                # PO template so that it's included in language pack exports.
                template.languagepack = True

            template.path = helpers.getRosettaBestDomainPath(
                domain.domain_paths)

            template.filename = domain.pot_filename

            # Attach all the PO files.

            for language_code in domain.po_files:
                if '@' in language_code:
                    code, variant = language_code.split('@', 1)
                    variant = unicode(variant)
                else:
                    code, variant = language_code, None

                try:
                    pofile = template.getOrCreatePOFile(code, variant,
                                                        ubuntu_translators)
                except LanguageNotFound:
                    # The language code does not exist in our database.
                    # Usually, it's a translator error.
                    self.logger.warning(
                        "PO file with unknown language code '%s' for %s/%s"
                        % (language_code, release.name, sourcepackagename.name))
                    continue

                # again, these are always considered "published"
                pofile.attachRawFileData(
                    domain.po_files[language_code], True, admins)

            # Now that we've successfully updated the information for the
            # source package, we can update the version in the PO template.
            template.sourcepackageversion = version

        self.ztm.commit()

    def import_catalog(self):
        for entry in self.catalog:
            # Verify that all mandatory keys are present in the entry.

            error = False
            keys = ('Distribution', 'Release', 'Source', 'Version',
                'File')

            for key in keys:
                if key not in entry:
                    self.logger.error(
                        "The field '%s' is missing from this catalog entry" %
                        key)
                    error = True

            if error:
                continue

            distribution, release, source, version, file = (
                entry['Distribution'], entry['Release'], entry['Source'],
                entry['Version'], entry['File'])

            # Get the distribution release and source package name objects,
            # and attach the tarball for this entry to that release/package
            # combination.

            release = self.get_distrorelease(distribution, release)
            sourcepackagename = self.get_sourcepackagename(source)

            if sourcepackagename is not None and release is not None:
                try:
                    self.import_sourcepackage_release(
                        sourcepackagename, release, file, version)
                except:
                    # If an exception is raised, we log it before aborting the
                    # attachment.
                    self.logger.error('We got an unexpected exception', 
                                      exc_info=1)
                    self.ztm.abort()

    def run(self):
        try:
            self.import_catalog()
        except:
            # If an exception is raised, we log it before aborting the
            # attachment.
            self.logger.error('We got an unexpected exception', exc_info=1)
            self.ztm.abort()

def attach(urlopener, archive_uri, ztm, logger):
    """Attach PO templates and PO files from a (possibly remote) archive of
    tarballs.
    """

    dates_list = fetch_date_list(urlopener, archive_uri, logger)

    for date in dates_list:
        catalog = fetch_catalog(urlopener, archive_uri, date, logger)
        base_uri = archive_uri + '/' + date
        process = AttachTranslationCatalog(
            urlopener, base_uri, catalog, ztm, logger)
        process.run()


class ImportProcess:
    """Import .po and .pot files attached to Rosetta."""

    # We cache files we have attempted to import
    POIMPORT_RECENTLY_SEEN_PICKLE = '/var/tmp/rosetta-poimport-seen.pickle'

    def __init__(self, ztm, logger):
        """Initialize the ImportProcess object.

        Get two arguments, the Zope Transaction Manager and a logger for the
        warning/errors messages.
        """
        self.ztm = ztm
        self.logger = logger
        self.potemplateset = getUtility(IPOTemplateSet)
        self.pofileset = getUtility(IPOFileSet)

    def recentlySeen(self, obj):
        """We store a cache on local disk of imports we have recently
        seen. This allows our code to not retry imports that recently
        failed. This method may be replaced one day with something
        more intelligent, or a method that stores this information in the
        PostgreSQL database.
        """
        try:
            seen = pickle.load(open(self.POIMPORT_RECENTLY_SEEN_PICKLE, 'rb'))
            self.logger.debug(
                    'Loaded recent import cache %s',
                    self.POIMPORT_RECENTLY_SEEN_PICKLE
                    )
        except (IOError, pickle.PickleError):
            seen = {}

        if IPOFile.providedBy(obj):
            key = '%df' % obj.id
        elif IPOTemplate.providedBy(obj):
            key = '%dt' % obj.id
        else:
            raise TypeError('Unknown object %r' % (obj,))

        self.logger.debug('Key is %s', key)

        try:
            # Clean out all entries in seen older than 1 day
            for cache_key, cache_value in list(seen.items()):
                if cache_value < time.time() - 24*60*60:
                    self.logger.debug('Garbage collecting %s', cache_key)
                    del seen[cache_key]

            # If we have seen this key recently, return True
            if seen.has_key(key):
                return True
            else:
                return False
        finally:
            now = time.time()
            self.logger.debug('Seen %s at %d', key, now)
            seen[key] = now
            self.logger.debug(
                    'Saving recent import cache %s',
                    self.POIMPORT_RECENTLY_SEEN_PICKLE
                    )
            pickle.dump(
                    seen, open(self.POIMPORT_RECENTLY_SEEN_PICKLE, 'wb'),
                    pickle.HIGHEST_PROTOCOL
                    )

    def getPendingImports(self):
        """Iterate over all templates and PO files which are waiting to be
        imported.
        """
        for template in self.potemplateset.getTemplatesPendingImport():
            yield template

        for pofile in self.pofileset.getPOFilesPendingImport():
            yield pofile

    def run(self):
        UTC = pytz.timezone('UTC')
        while True:

            # Note we invoke getPendingImports each loop, as this avoids
            # needing to cache the objects in RAM (and we can't rely on
            # the cursor remaining valid since we will be committing and
            # aborting the transaction
            object = None
            for object in self.getPendingImports():
                # Skip objects that we have attempted to import in the
                # last 24 hours.
                if self.recentlySeen(object):
                    self.logger.debug(
                            'Recently seen %s. Skipping', object.title
                            )
                    object = None
                else:
                    # We have an object to import.
                    break
            
            if object is None:
                # There are no objects to import. Exit the script.
                break

            # object could be a POTemplate or a POFile but both
            # objects implement the doRawImport method so we don't
            # need to care about it here.
            title = '[Unknown Title]'
            try:
                title = object.title
                self.logger.info('Importing: %s' % title)
                object.doRawImport(self.logger)
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('Got an unexpected exception while'
                                  ' importing %s' % title, exc_info=1)
                self.ztm.abort()
                continue

            # As soon as the import is done, we commit the transaction
            # so it's not lost.
            try:
                self.ztm.commit()
            except KeyboardInterrupt:
                self.ztm.abort()
                raise
            except:
                # If we have any exception, we log it and abort the
                # transaction.
                self.logger.error('We got an unexpected exception while'
                                  ' committing the transaction', exc_info=1)
                self.ztm.abort()


if __name__ == '__main__':
    doctest.testmod()


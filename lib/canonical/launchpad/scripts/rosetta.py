import doctest
import os
import tarfile
import urllib2
from datetime import datetime
from StringIO import StringIO

from canonical.launchpad import helpers
from canonical.launchpad.database import DistributionSet, \
    SourcePackageNameSet, POTemplateSet, POTemplateNameSet, PersonSet
from canonical.sourcerer.deb.version import Version

def fetch_date_list(archive_uri, logger):
    uri = archive_uri + '/directories.txt'

    try:
        date_file = urllib2.urlopen(uri)
    except urllib2.HTTPError, e:
        logger.error('Got an error fetching the file %s: %s' % (uri, e))
        raise

    date_list = []

    for line in date_file.readlines():
        date_list.append(line.strip())

    return date_list

def fetch_catalog(archive_uri, date, logger):
    uri = "%s/%s/translations.txt" % (archive_uri, date)

    try:
        catalogfile = urllib2.urlopen(uri)
    except urllib2.HTTPError, e:
        logger.error('Got an error fetching the file %s: %s' %
            (uri, e))
        raise

    return parse_catalog(catalogfile)

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

def make_tarball(files):
    sio = StringIO()
    tarball = tarfile.open('', 'w', sio)

    sorted_files = files.keys()
    sorted_files.sort()

    for filename in sorted_files:
        helpers.tar_add_file(tarball, filename, files[filename])

    tarball.close()
    sio.seek(0)
    return tarfile.open('', 'r', sio)

def get_test_tarball():
    """Create a translation tarball for doctests.

    >>> tarball = get_test_tarball()
    >>> len(tarball.getmembers())
    5
    """

    return make_tarball({
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

def get_domain_binarypackages(tar):
    """Return a dictionary mapping domains to binary package names.

    >>> tarball = get_test_tarball()
    >>> get_domain_binarypackages(tarball)
    {'uber': ['uberfrob']}
    >>> tarball.close()
    """

    names = tar.getnames()

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
        self.name = name
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


def get_domains_from_tarball(distrorelease_name, sourcepackage_name,
                             existing_potemplates, tar):
    """Return a list with all .pot and .po files from a tarball.

    The parameters are: the name of the source package the tarball was
    generated from, an iterable of PO templates belonging to the distribution
    release and source package that the tarball was generated from, and the
    tarball itself.

    Return a list of TranslationDomain objects.

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

    domain_binarypackages = get_domain_binarypackages(tar)

    # Get lists of the PO templates and PO files in the tarball.

    pot_files, po_files = helpers.examine_tarfile(tar)

    # Get the list of PO templates which are not package configuration
    # templates.

    non_pkgconf_templates = [
        template
        for template in pot_files
        if not template.startswith('source/debian/po/')]

    assert len(pot_files) - len(non_pkgconf_templates) in (0, 1)

    # Prefix and suffix are used when we need to generate a name for a PO
    # template (the fallback case).

    prefix = 'review-potemplate-%s-%s-' % (
        distrorelease_name, sourcepackage_name)
    suffix = 1

    # For each PO template, try to find a domain which matches it.

    found_domains = []

    for pot_file in pot_files:
        pot_dirname, pot_filename = os.path.split(pot_file)
        domain_name = None

        if pot_dirname == 'source/debian/po':
            # It's a Debian debconf .pot file.
            domain_name = 'pkgconf-%s' % sourcepackage_name
        elif len(non_pkgconf_templates) == len(domain_binarypackages) == 1:
            # We have only one non-Debconf .pot file and one domain, therefore
            # the mapping is direct.
            domain_name = domain_binarypackages.keys()[0]
        else:
            # Check to see if there is already a PO Template in the database
            # with the same path and the same filename as pot_filename.
            for potemplate in existing_potemplates:
                if ('source/' + potemplate.path == pot_dirname and
                    potemplate.filename == pot_filename):
                    domain_name = potemplate.potemplatename.name

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
                # exist in the database, nor any domains in the tarball, so we
                # have to fall back to generating a name for the PO template.
                for potemplate in existing_potemplates:
                    # Check if we already have a potemplatename with the same
                    # prefix so we don't mix two different .pot files when we
                    # don't know their real translation domain.
                    if potemplate.potemplatename.name.startswith(prefix):
                        number = int(
                            potemplate.potemplatename.name[len(prefix):])
                        if number >= suffix:
                            suffix = number + 1
                domain_name = '%s%d' % (prefix, suffix)
                # Update the suffix so that the next pot file in this case
                # gets the right value.
                suffix = suffix + 1

        found_domains.append(domain_name)

        # Create the translation domain object.
        td = TranslationDomain(domain_name)
        td.pot_contents = tar.extractfile(pot_file).read()
        td.pot_filename = pot_filename
        td.domain_paths.append(pot_dirname)

        if domain_name in domain_binarypackages:
            td.binary_packages = domain_binarypackages[domain_name]

        # Search for PO files which are in the same directory as the PO
        # template, and add them to the translation domain.
        for po_file in po_files:
            po_dirname, po_filename = os.path.split(po_file)
            if po_dirname == pot_dirname:
                lang_code, extension = os.path.splitext(po_filename)
                td.po_files[lang_code] = tar.extractfile(po_file).read()

        domains.append(td)

    return domains


class AttachTranslationCatalog:
    """Attach the .po and .pot files of a set of tarballs into Rosetta."""

    def __init__(self, base_uri, catalog, ztm, logger):
        """Initialize the AttachTranslationCatalog object.

        Get Four arguments, the base_uri where the files will be downloaded
        from, the catalog with all files to be attached, the Zope Transaction
        Manager and a logger for the warning/errors messages.
        """
        self.ztm = ztm
        self.base_uri = base_uri
        self.catalog = catalog
        self.logger = logger

        self.distributionset = DistributionSet()


    def get_distrorelease(self, distribution_name, release_name):
        """Get the distrorelease object for a distribution and a release."""

        # Check that we have the needed distribution.
        try:
            distribution = self.distributionset[distribution_name]
        except KeyError:
            # We don't have this distribution in our database, print a
            # warning so we can add it later and return.
            self.logger.warning("No distribution called %s in the "
                                "database" % catalogentry['Distribution'])
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
            return None

    def get_sourcepackagename(self, sourcepackagename):
        """Get the sourcepackagename object for a given name."""

        sourcepackagenameset = SourcePackageNameSet()
        try:
            return sourcepackagenameset[sourcepackagename]
        except KeyError:
            # We don't have this sourcepackage in our database, print
            # a warning so we can add it later and return.
            self.logger.warning("No sourcepackagename %s in the "
                                "database" % sourcepackagename)
            return None

    def import_sourcepackage_release(self, sourcepackagename, release, file,
                                     version):
        """Import a tarball to a source package for a distribution release."""

        uri = self.base_uri + '/' + file
        self.logger.info("Getting %s" % uri)

        try:
            tarfile = urllib2.urlopen(uri)
        except urllib2.HTTPError, e:
            self.logger.error('Got an error fetching the file %s: %s' % (uri, e))
            return

        self.logger.debug("%s attached to %s sourcepackage" % (
                          uri, sourcepackagename.name))

        # Check to see if we have already imported this tarball successfully
        # inside this sourcepackagename and distrorelease.
        # We do it before the tarfile.read() so we don't download the file if
        # it's not needed.
        potemplateset = POTemplateSet(sourcepackagename=sourcepackagename,
                            distrorelease=release)
        for pot in potemplateset:
            if pot.sourcepackageversion is not None:
                # The Version class comes from Sourcerer and helps us to
                # compare .deb package version strings. That class has a
                # __cmp__ method so we can compare a normal string with the
                # class.
                if Version(version) <= pot.sourcepackageversion:
                    self.logger.debug(
                        "This tarball or a newer one is already imported."
                        " Ignoring it...")
                    return

        tarball = helpers.string_to_tarfile(tarfile.read())

        domains = get_domains_from_tarball(
            release.name, sourcepackagename.name, potemplateset, tarball)

        potemplatenameset = POTemplateNameSet()

        # XXX
        # This should be done with a celebrity.
        #  -- Dafydd Harries, 2005/03/16
        admins = PersonSet().getByName('rosetta-admins')

        for domain in domains:
            try:
                template = potemplateset[domain.name]
            except KeyError:
                # Get or create the PO template name.
                try:
                    name = potemplatenameset[domain.name]
                except KeyError:
                    self.logger.warning("Creating new PO template name '%s'" %
                        domain.name)
                    name = potemplatenameset.new(name=domain.name,
                                                   title=domain.name)

                # Create the PO template.
                self.logger.warning(
                    "Creating new PO template '%s' for %s/%s" % (
                    domain.name, release.name, sourcepackagename.name))
                template = potemplateset.new(
                    potemplatename=name,
                    title='%s template for %s in %s' % (
                        name, sourcepackagename.name, release.displayname),
                    contents=domain.pot_contents,
                    owner=admins)
            else:
                template.attachRawFileData(domain.pot_contents, admins)

            # Choosing the shortest is used as a heuristic for selecting among
            # binary package names and domain paths.
            if domains.binary_packages:
                binarypackagenameset = BinaryPackageNameSet()
                best_binarypackage = helpers.getRosettaBestBinaryPackageName(
                    domains.binary_packages)
                template.binarypackagename = (
                    binarypackagenameset[best_binarypackage])

            template.path = helpers.getRosettaBestDomainPath(domain.domain_paths)

            template.filename = domain.pot_filename

            # If the domain has any binary packages, set this flag on the PO
            # template so that it's included in language pack exports.
            if domain.binary_packages:
                template.languagepack = True

            # Attach all the PO files.

            for language_code in domain.po_files:
                if '@' in language_code:
                    code, variant = language_code.split('@', 1)
                else:
                    code, variant = language_code, None

                try:
                    pofile = template.getOrCreatePOFile(code, variant)
                except ValueError, value:
                    # The language code does not exist in our database.
                    # Usually, it's a translator error.
                    self.logger.warning(
                        "PO file with unknown language code '%s' for %s/%s"
                        % (language_code, distrorelease.name,
                           sourcepackagename.name))
                    continue

                pofile.attachRawFileData(
                    domain.po_files[language_code], admins)

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
                self.import_sourcepackage_release(
                    sourcepackagename, release, file, version)

    def run(self):
        try:
            self.import_catalog()
        except:
            # If an exception is raised, we log it before aborting the
            # attachment.
            self.logger.error('We got an unexpected exception', exc_info = 1)
            self.ztm.abort()

if __name__ == '__main__':
    doctest.testmod()


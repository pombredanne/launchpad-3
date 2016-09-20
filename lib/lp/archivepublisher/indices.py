# Copyright 2009-2014 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__all__ = [
    'IndexStanzaFields',
    'build_binary_stanza_fields',
    'build_source_stanza_fields',
    'build_translations_stanza_fields',
    ]

__metaclass__ = type

from collections import OrderedDict
import hashlib
import os.path
import re

from lp.soyuz.model.publishing import makePoolPath


class IndexStanzaFields:
    """Store and format ordered Index Stanza fields."""

    def __init__(self):
        self._names_lower = set()
        self.fields = []

    def append(self, name, value):
        """Append an (field, value) tuple to the internal list.

        Then we can use the FIFO-like behaviour in makeOutput().
        """
        if name.lower() in self._names_lower:
            return
        self._names_lower.add(name.lower())
        self.fields.append((name, value))

    def extend(self, entries):
        """Extend the internal list with the key-value pairs in entries.
        """
        for name, value in entries:
            self.append(name, value)

    def makeOutput(self):
        """Return a line-by-line aggregation of appended fields.

        Empty fields values will cause the exclusion of the field.
        The output order will preserve the insertion order, FIFO.
        """
        output_lines = []
        for name, value in self.fields:
            if not value:
                continue

            # do not add separation space for the special file list fields.
            if name not in ('Files', 'Checksums-Sha1', 'Checksums-Sha256'):
                value = ' %s' % value

            # XXX Michael Nelson 20090930 bug=436182. We have an issue
            # in the upload parser that has
            #   1. introduced '\n' at the end of multiple-line-spanning
            #      fields, such as dsc_binaries, but potentially others,
            #   2. stripped the leading space from each subsequent line
            #      of dsc_binaries values that span multiple lines.
            # This is causing *incorrect* Source indexes to be created.
            # This work-around can be removed once the fix for bug 436182
            # is in place and the tainted data has been cleaned.
            # First, remove any trailing \n or spaces.
            value = value.rstrip()

            # Second, as we have corrupt data where subsequent lines
            # of values spanning multiple lines are not preceded by a
            # space, we ensure that any \n in the value that is *not*
            # followed by a white-space character has a space inserted.
            value = re.sub(r"\n(\S)", r"\n \1", value)

            output_lines.append('%s:%s' % (name, value))

        return '\n'.join(output_lines)


def format_file_list(l):
    return ''.join('\n %s %s %s' % ((h,) + f) for (h, f) in l)


def format_description(summary, description):
    # description field in index is an association of summary and
    # description or the summary only if include_long_descriptions
    # is false, as:
    #
    # Descrition: <SUMMARY>\n
    #  <DESCRIPTION L1>
    #  ...
    #  <DESCRIPTION LN>
    descr_lines = [line.lstrip() for line in description.splitlines()]
    bin_description = '%s\n %s' % (summary, '\n '.join(descr_lines))
    return bin_description


def build_source_stanza_fields(spr, component, section):
    """Build a map of fields to be included in a Sources file."""
    # Special fields preparation.
    pool_path = makePoolPath(spr.name, component.name)
    files_list = []
    sha1_list = []
    sha256_list = []
    for spf in spr.files:
        common = (
            spf.libraryfile.content.filesize, spf.libraryfile.filename)
        files_list.append((spf.libraryfile.content.md5, common))
        sha1_list.append((spf.libraryfile.content.sha1, common))
        sha256_list.append((spf.libraryfile.content.sha256, common))
    user_defined_fields = OrderedDict([
        (key.lower(), (key, value))
        for key, value in spr.user_defined_fields])
    # Filling stanza options.
    fields = IndexStanzaFields()
    fields.append('Package', spr.name)
    fields.append('Binary', spr.dsc_binaries)
    fields.append('Version', spr.version)
    fields.append('Section', section.name)
    fields.append('Maintainer', spr.dsc_maintainer_rfc822)
    fields.append('Build-Depends', spr.builddepends)
    fields.append('Build-Depends-Indep', spr.builddependsindep)
    if 'build-depends-arch' in user_defined_fields:
        fields.append(
            'Build-Depends-Arch',
            user_defined_fields.pop('build-depends-arch')[1])
    fields.append('Build-Conflicts', spr.build_conflicts)
    fields.append('Build-Conflicts-Indep', spr.build_conflicts_indep)
    if 'build-conflicts-arch' in user_defined_fields:
        fields.append(
            'Build-Conflicts-Arch',
            user_defined_fields.pop('build-conflicts-arch')[1])
    fields.append('Architecture', spr.architecturehintlist)
    fields.append('Standards-Version', spr.dsc_standards_version)
    fields.append('Format', spr.dsc_format)
    fields.append('Directory', pool_path)
    fields.append('Files', format_file_list(files_list))
    fields.append('Checksums-Sha1', format_file_list(sha1_list))
    fields.append('Checksums-Sha256', format_file_list(sha256_list))
    fields.append('Homepage', spr.homepage)
    fields.extend(user_defined_fields.values())

    return fields


def build_binary_stanza_fields(bpr, component, section, priority,
                               phased_update_percentage,
                               separate_long_descriptions=False):
    """Build a map of fields to be included in a Packages file.

    :param separate_long_descriptions: if True, the long description will
    be omitted from the stanza and Description-md5 will be included.
    """
    spr = bpr.build.source_package_release

    # binaries have only one file, the DEB
    bin_file = bpr.files[0]
    bin_filename = bin_file.libraryfile.filename
    bin_size = bin_file.libraryfile.content.filesize
    bin_md5 = bin_file.libraryfile.content.md5
    bin_sha1 = bin_file.libraryfile.content.sha1
    bin_sha256 = bin_file.libraryfile.content.sha256
    bin_filepath = os.path.join(
        makePoolPath(spr.name, component.name), bin_filename)
    description = format_description(bpr.summary, bpr.description)
    # Our formatted description isn't \n-terminated, but apt
    # considers the trailing \n to be part of the data to hash.
    bin_description_md5 = hashlib.md5(
        description.encode('utf-8') + '\n').hexdigest()
    if separate_long_descriptions:
        # If distroseries.include_long_descriptions is False, the
        # description should be the summary
        bin_description = bpr.summary
    else:
        bin_description = description

    # Dealing with architecturespecific field.
    # Present 'all' in every archive index for architecture
    # independent binaries.
    if bpr.architecturespecific:
        architecture = bpr.build.distro_arch_series.architecturetag
    else:
        architecture = 'all'

    essential = None
    if bpr.essential:
        essential = 'yes'

    source = None
    if bpr.version != spr.version:
        source = '%s (%s)' % (spr.name, spr.version)
    elif bpr.name != spr.name:
        source = spr.name

    fields = IndexStanzaFields()
    fields.append('Package', bpr.name)
    fields.append('Source', source)
    fields.append('Priority', priority.title.lower())
    fields.append('Section', section.name)
    fields.append('Installed-Size', bpr.installedsize)
    fields.append('Maintainer', spr.dsc_maintainer_rfc822)
    fields.append('Architecture', architecture)
    fields.append('Version', bpr.version)
    fields.append('Recommends', bpr.recommends)
    fields.append('Replaces', bpr.replaces)
    fields.append('Suggests', bpr.suggests)
    fields.append('Provides', bpr.provides)
    fields.append('Depends', bpr.depends)
    fields.append('Conflicts', bpr.conflicts)
    fields.append('Pre-Depends', bpr.pre_depends)
    fields.append('Enhances', bpr.enhances)
    fields.append('Breaks', bpr.breaks)
    fields.append('Essential', essential)
    fields.append('Filename', bin_filepath)
    fields.append('Size', bin_size)
    fields.append('MD5sum', bin_md5)
    fields.append('SHA1', bin_sha1)
    fields.append('SHA256', bin_sha256)
    fields.append('Phased-Update-Percentage', phased_update_percentage)
    fields.append('Description', bin_description)
    if separate_long_descriptions:
        fields.append('Description-md5', bin_description_md5)
    if bpr.user_defined_fields:
        fields.extend(bpr.user_defined_fields)

    # XXX cprov 2006-11-03: the extra override fields (Bugs, Origin and
    # Task) included in the template be were not populated.
    # When we have the information this will be the place to fill them.

    return fields


def build_translations_stanza_fields(bpr, packages):
    """Build a map of fields to be included in a Translation-en file.

    :param packages: a set of (Package, Description-md5) tuples used to
        determine if a package has already been added to the translation
        file. The (Package, Description-md5) tuple will be added if it
        doesn't aready exist.
    """
    bin_description = format_description(bpr.summary, bpr.description)
    # Our formatted description isn't \n-terminated, but apt
    # considers the trailing \n to be part of the data to hash.
    bin_description_md5 = hashlib.md5(
        bin_description.encode('utf-8') + '\n').hexdigest()
    if (bpr.name, bin_description_md5) not in packages:
        fields = IndexStanzaFields()
        fields.append('Package', bpr.name)
        fields.append('Description-md5', bin_description_md5)
        fields.append('Description-en', bin_description)
        packages.add((bpr.name, bin_description_md5))

        return fields
    else:
        return None

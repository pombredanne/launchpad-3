# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Components for exporting PO files.

PO files are exported by adapting objects to interfaces which have methods for
exporting. Exported objects are either a single PO file, or a tarball of many
PO files.

See IPOTemplateExporter and IDistroReleasePOExporter.
"""

# XXX
# A note about tarballs, StringIO and unicode. SQLObject returns unicode
# values for columns which are declared as StringCol. We have to be careful
# not to pass unicode instances to the tarfile module, because when the
# tarfile's filehandle is a StringIO object, the StringIO object gets upset
# later when we ask it for its value and it tries to join together its
# buffers. This is why the tarball code is sprinkled with ".encode('ascii')".
# If we get separate StringCol and UnicodeCol column types, we won't need this
# any longer.
#  -- Dafydd Harries, 2005/04/07.

__metaclass__ = type

import codecs
import datetime
import gettextpo
import logging
import os
import subprocess
import tarfile
import time
import pytz
from StringIO import StringIO

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad import helpers

from canonical.launchpad.interfaces import (
    IPOTemplateExporter, IDistroReleasePOExporter, IPOFileOutput,
    IVPOExportSet, IVPOTExportSet, EXPORT_DATE_HEADER)

from canonical.launchpad.components.poparser import POMessage, POHeader

class RosettaWriteTarFile:
    """Convenience wrapper around the tarfile module.

    This class makes it convenient to generate tar files in various ways.
    """

    def __init__(self, stream):
        self.tarfile = tarfile.open('', 'w:gz', stream)
        self.closed = False

    @classmethod
    def files_to_stream(cls, files):
        """Turn a dictionary of files into a data stream."""
        buffer = StringIO()
        archive = cls(buffer)
        archive.add_files(files)
        archive.close()
        buffer.seek(0)
        return buffer

    @classmethod
    def files_to_string(cls, files):
        """Turn a dictionary of files into a data string."""
        return cls.files_to_stream(files).read()

    @classmethod
    def files_to_tarfile(cls, files):
        """Turn a dictionary of files into a tarfile object."""
        return tarfile.open('', 'r', cls.files_to_stream(files))

    def close(self):
        """Close the archive.

        After the archive is closed, the data written to the filehandle will
        be complete. The archive may not be appended to after it has been
        closed.
        """

        self.tarfile.close()
        self.closed = True

    def add_file(self, path, contents):
        """Add a file to the archive."""

        if self.closed:
            raise RuntimeError("Can't add a file to a closed archive")

        now = int(time.time())
        path_bits = path.split(os.path.sep)

        # Ensure that all the directories in the path are present in the
        # archive.

        for i in range(1, len(path_bits)):
            joined_path = os.path.join(*path_bits[:i])

            try:
                self.tarfile.getmember(joined_path + os.path.sep)
            except KeyError:
                tarinfo = tarfile.TarInfo(joined_path)
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.mtime = now
                tarinfo.mode = 0755
                tarinfo.uname = 'rosetta'
                tarinfo.gname = 'rosetta'
                self.tarfile.addfile(tarinfo)

        tarinfo = tarfile.TarInfo(path)
        tarinfo.time = now
        tarinfo.mtime = now
        tarinfo.mode = 0644
        tarinfo.size = len(contents)
        tarinfo.uname = 'rosetta'
        tarinfo.gname = 'rosetta'
        self.tarfile.addfile(tarinfo, StringIO(contents))

    def add_files(self, files):
        """Add a number of files to the archive.

        :files: A dictionary mapping file names to file contents.
        """

        for filename in sorted(files.keys()):
            self.add_file(filename, files[filename])


class OutputPOFile:
    """Buffer PO header/message set data for output."""

    def __init__(self, header):
        self.header = header
        self.msgsets = []

    def append(self, msgset):
        """Append a message set to this PO file."""
        self.msgsets.append(msgset)

    def export_string(self):
        """Return a string representation of this PO file."""

        # Sort all the PO file's message sets by sequence number.
        msgsets = [
            (msgset.obsolete, msgset.sequence, msgset)
            for msgset in self.msgsets
            ]
        msgsets.sort()
        msgsets = [msgset for obsolete, sequence, msgset in msgsets]

        chunks = [unicode(self.header).encode(self.header.charset)]
        for msgset in msgsets:
            if msgset.obsolete and len(msgset.msgstrs) == 0:
                continue

            chunks.append(msgset.export_string())

        return '\n\n'.join(chunks)

    def dump_file(self):
        """Return a string representing a .po file.


        The encoding of the string will depend on the declared charset at
        self.header or 'UTF-8' if cannot be represented by it.
        """

        try:
            # Export the object.
            return self.export_string()
        except UnicodeEncodeError:
            # Got any message that cannot be represented by its default
            # encoding, need to force a UTF-8 export.
            self.header['Content-Type'] = 'text/plain; charset=UTF-8'
            self.header.updateDict()
            return self.export_string()

class OutputMsgSet:
    """Buffer message set data for output."""

    def __init__(self, pofile):
        self.pofile = pofile
        self.msgids = []
        self.msgstrs = []
        self.flags = []
        self.obsolete = False
        self.commenttext = ''
        self.sourcecomment = ''
        self.filereferences = ''

    def add_msgid(self, msgid):
        """Add a message ID to this message set."""
        self.msgids.append(msgid)

    def add_msgstr(self, pluralform, msgstr):
        """Add a translation to this message set."""

        # The msgstr should be item with index pluralform in the list
        # self.msgstrs. I.e. after this function has returned:
        #
        #   self.msgstrs[pluralform] == msgstr
        #
        # However, unlike msgids, we can't assume that groups of msgstrs are
        # contiguous. I.e. we might get translations for plural forms 0 and 2,
        # but not 1. This means we need to add empty values if pluralform >
        # len(self.msgstrs).
        #
        # We raise an error if pluralform < len(self.msgstrs).

        if pluralform < len(self.msgstrs):
            raise ValueError(
                'This message set already has a translation for plural form'
                ' %d' % pluralform)
        elif pluralform > len(self.msgstrs):
            self.msgstrs.extend([None] * (pluralform - len(self.msgstrs)))

        self.msgstrs.append(msgstr)

    def export_unicode_string(self):
        """Return a unicode string representation of this message set."""
        assert len(self.msgids) <= 2, "Too many message IDs for a message set."
        assert len(self.msgids) > 0, (
            "Can't export a message set with no message IDs.")

        if len(self.msgids) == 2:
            msgidPlural = self.msgids[1]

            # If there are fewer translations than the PO file's header
            # specifies, add blank ones.
            while len(self.msgstrs) < self.pofile.header.nplurals:
                self.msgstrs.append('')
        else:
            msgidPlural = None

        if len(self.msgids) == 2 and self.msgstrs:
            # We have more than one translation
            msgstr = None
            msgstrPlurals = self.msgstrs
        elif self.msgstrs:
            msgstr = self.msgstrs[0]
            msgstrPlurals = None
        else:
            msgstr = None
            msgstrPlurals = None

        message = POMessage(
            msgid=self.msgids[0],
            msgidPlural=msgidPlural,
            msgstr=msgstr,
            msgstrPlurals=msgstrPlurals,
            obsolete=self.obsolete,
            header=self.pofile.header,
            flags=self.flags,
            commentText=self.commenttext,
            sourceComment=self.sourcecomment,
            fileReferences=self.filereferences)

        return unicode(message)

    def export_string(self):
        """Return a string representation of this message set.

        It uses PO file's header.charset info.
        """
        return self.export_unicode_string().encode(self.pofile.header.charset)

def last_translator_text(person):
    """Calculate a value for a Last-Translator field for a person.

    The preferred email address is used for preference, otherwise the first
    validated email address, otherwise any email address associated with the
    person. Hence the address returned should not be used for sending mail.
    """

    if person.preferredemail:
        # The translator has a preferred email address set.
        email = person.preferredemail.email
    elif person.guessedemails:
        # Fall back to using one of the guessed email addresses.
        email = person.guessedemails[0].email
    elif person.merged is not None:
        # If we reach this point, it means that the people merge account is
        # broken because only merged accounts can have no email addresses at
        # all, but also they can't have anything assigned to them.
        raise RuntimeError(
            "Got merged person %r as translator." % person.name)
    else:
        # We should never reach this point because we are supposed to have an
        # email address for every non-merged person.
        raise RuntimeError(
            "Non-merged person %r has no email addresses!" % person.name)

    return '%s <%s>' % (person.browsername, email)

def export_rows(rows, pofile_output, force_utf8=False):
    """Convert a list of PO file export view rows to a set of PO files.

    :pofile_output: Implements IPOFileOutput. It is used to output the
        generated PO files.
    :force_utf8: Whether the export should be exported as UTF-8 or not.

    This function depends on the rows being sorted in a very particular order.
    This allows it to minimise the amount of data that is held in memory at a
    time, and hence the memory usage of exports. Currently, the most data held
    in data at a time is an entire PO file.
    """

    potemplate = None
    language = None
    variant = None
    potsequence = None
    posequence = None

    exported_file = None
    msgset = None

    for row in rows:
        # Assert added due we allowed this situation on the past and it's
        # broken.
        assert ((row.poheader is not None and row.pofile is not None) or
                row.poheader is None), (
            'row.pofile cannot be None, we have a poheader!')

        new_pofile = False
        new_msgset = False

        # Skip messages which are neither in the PO template nor in the PO
        # file. (Messages which are in the PO template but not in the PO file
        # are untranslated, and messages which are not in the PO template but
        # in the PO file are obsolete.)

        if ((row.posequence == 0 or row.posequence is None) and
            row.potsequence == 0):
            continue

        # The PO template has changed, thus so must have the PO file.

        if row.potemplate != potemplate:
            new_pofile = True

        # The language or variant has changed: new PO file.

        if row.language != language or row.variant != variant:
            new_pofile = True

        # If the PO file has changed, we have to outptut its last message set.

        if new_pofile:
            new_msgset = True

        # If the sequence number of either the PO template or the PO file has
        # changed, we start a new message set.

        if (row.potsequence != potsequence or
            row.posequence != posequence):

            new_msgset = True

        # The order of output/creation is as follows:
        #
        # - if we need to create a new message set, output the old one
        # - if we need to create a new PO file
        #   - output the old one
        #   - create a new one
        # - if we need to create a new message set, create the new one
        #
        # Why things are ordered in this way: if we need to create a new PO
        # file, the old message set needs to be added to the old PO file
        # before it is output, and the new message set needs to be added to
        # the new PO file, and so the new PO file must be created first.

        if new_msgset:
            # Output the current message set.

            if msgset is not None:
                # validate the translation
                if 'fuzzy' not in msgset.flags and len(msgset.msgstrs) > 0:
                    # The validation is done only if the msgset is not fuzzy
                    # and has a translation.
                    new_translations = {}
                    for index, translation in enumerate(msgset.msgstrs):
                        new_translations[index] = translation
                    try:
                        helpers.validate_translation(
                            msgset.msgids, new_translations, msgset.flags)
                    except gettextpo.error:
                        # There is an error in this translation, instead of
                        # export a broken value, we set it as fuzzy.
                        msgset.flags.append('fuzzy')

                exported_file.append(msgset)

        if new_pofile:
            # If the PO file has changed, flush the old one and print the
            # header for the new one.

            # Output the current PO file.
            if exported_file is not None:
                exported_file_content = exported_file.dump_file()
                pofile_output(
                    potemplate, language, variant, exported_file_content)

            # Get the pot header
            if row.potheader is None:
                pot_header_value = ''
            else:
                pot_header_value = row.potheader
            pot_header = POHeader(
                msgstr=pot_header_value)
            # PO templates have always the fuzzy flag set on headers.
            pot_header.flags.add('fuzzy')
            # The parsing finished, we need this to get the header available.
            pot_header.updateDict()
            if force_utf8:
                # Change the charset declared for this file.
                pot_header['Content-Type'] = 'text/plain; charset=UTF-8'
                pot_header.updateDict()

            pofile = row.pofile
            if pofile is not None:
                # Generate the header of the new PO file.
                header = POHeader(
                    commentText=row.potopcomment,
                    msgstr=row.poheader)

                if row.pofuzzyheader:
                    header.flags.add('fuzzy')

                # Needed to be sure that the header has the right information.
                header.updateDict()

                if 'Domain' in pot_header:
                    header['Domain'] = pot_header['Domain']

                if 'POT-Creation-Date' in pot_header:
                    # Rosetta merges by default all .po files with the latest
                    # .pot imported and thus, we need to update the field that
                    # indicates when was the .pot file created.
                    header['POT-Creation-Date'] = (
                        pot_header['POT-Creation-Date'])

                if force_utf8:
                    # Change the charset declared for this file.
                    header['Content-Type'] = 'text/plain; charset=UTF-8'

                # To be sure that the header is updated..
                header.updateDict()
            else:
                # We are exporting an IPOTemplate.
                header = pot_header

            try:
                codecs.getdecoder(header.charset)
            except LookupError:
                # The codec we are using to do the export is not valid,
                # we default to UTF-8 for the export.
                header.charset = u'UTF-8'
                header['Content-Type'] = 'text/plain; charset=UTF-8'
                header.updateDict()

            # This part is conditional on the PO file being present in order
            # to make it easier to fake data for testing.

            if (pofile is not None and
                pofile.last_touched_pomsgset is not None and
                pofile.last_touched_pomsgset.reviewer is not None):
                # Update the last translator field.
                last_touched_pomsgset = pofile.last_touched_pomsgset

                header['Last-Translator'] = last_translator_text(
                    last_touched_pomsgset.reviewer)

                # Update the revision date field.

                header['PO-Revision-Date'] = (
                    last_touched_pomsgset.date_reviewed.strftime('%F %R%z'))

            if row.potemplate.hasPluralMessage():
                if pofile.language.pluralforms is not None:
                    # We have pluralforms information for this language so we
                    # update the header to be sure that we use the language
                    # information from our database instead of use the one
                    # that we got from upstream. We check this information so
                    # we are sure it's valid.
                    header['Plural-Forms'] = 'nplurals=%d; plural=(%s);' % (
                        pofile.language.pluralforms,
                        pofile.language.pluralexpression)
            elif 'Plural-Forms' in header:
                # There is no plural forms here but we have a 'Plural-Forms'
                # header, we remove it because it's not needed.
                del header['Plural-Forms']

            # We need to tag every export from Rosetta so we know whether a
            # later upload should change every translation in our database or
            # that we got a change between the export and the upload with
            # modifications.
            UTC = pytz.timezone('UTC')
            dt = datetime.datetime.now(UTC)
            header[EXPORT_DATE_HEADER] = dt.strftime('%F %R%z')

            # Create the new PO file.

            exported_file = OutputPOFile(header)

        if new_msgset:
            # Create new message set

            if row.posequence is None and row.potsequence == 0:
                # The po sequence is unknown, that means that we don't have
                # this message as part of IPOFile and the pot sequence is
                # zero which means that this message is not anymore valid for
                # the IPOTemplate we are handling and it's an obsolete entry.
                # Ignore it.
                continue

            msgset = OutputMsgSet(exported_file)
            if row.isfuzzy is not None:
                msgset.fuzzy = row.isfuzzy

            if row.potsequence > 0:
                msgset.sequence = row.potsequence
                msgset.obsolete = False
            elif row.posequence > 0:
                msgset.sequence = row.posequence
                msgset.obsolete = True
            else:
                msgset.sequence = 0
                msgset.obsolete = True

        # Because of the way the database view works, message IDs and
        # translations will appear multiple times. We see how many we've added
        # already to check whether the message ID/translation in the current
        # row are ones we need to add.

        # Note that the msgid plural form must be equal to the number of
        # message IDs, while the translation plural form can be greater than
        # or equal to. This allows for non-contiguous plural form indices,
        # though we require that indices monotonically increase.

        if row.msgidpluralform == len(msgset.msgids):
            msgset.add_msgid(row.msgid)

        if (row.activesubmission is not None and
            row.translationpluralform >= len(msgset.msgstrs)):
            # There is an active submission, the plural form is higher than
            # the last imported plural form.

            if (pofile.language.pluralforms is not None and
                row.translationpluralform >= pofile.language.pluralforms):
                # The plural form index is higher than the number of plural
                # form for this language, so we should ignore it.
                continue

            msgset.add_msgstr(row.translationpluralform, row.translation)

        if row.isfuzzy and not 'fuzzy' in msgset.flags:
            msgset.flags.append('fuzzy')

        if row.pocommenttext and not msgset.commenttext:
            msgset.commenttext = row.pocommenttext

        if row.sourcecomment and not msgset.sourcecomment:
            msgset.sourcecomment = row.sourcecomment

        if row.filereferences and not msgset.filereferences:
            msgset.filereferences = row.filereferences

        if row.flagscomment and not msgset.flags:
            msgset.flags = [
                flag.strip()
                for flag in row.flagscomment.split(',')
                if flag
                ]

        potemplate = row.potemplate
        language = row.language
        variant = row.variant
        potsequence = row.potsequence
        posequence = row.posequence

    # If we've processed all the rows, output the last message set and PO
    # file.

    if msgset:
        # validate the translation
        if 'fuzzy' not in msgset.flags and len(msgset.msgstrs) > 0:
            new_translations = {}
            for index, translation in enumerate(msgset.msgstrs):
                new_translations[index] = translation
            try:
                helpers.validate_translation(
                    msgset.msgids, new_translations, msgset.flags)
            except gettextpo.error:
                msgset.flags.append('fuzzy')
        exported_file.append(msgset)

    if exported_file is not None:
        exported_file_content = exported_file.dump_file()
        pofile_output(potemplate, language, variant, exported_file_content)

def export_pot_rows(rows, pofile_output, force_utf8=False):
    """Convert a list of POT file export view rows to a set of POT files.

    :pofile_output: Implements IPOFileOutput. It is used to output the
        generated POT files.
    :force_utf8: Whether the export should be exported as UTF-8 or not.

    This function depends on the rows being sorted in a very particular order.
    This allows it to minimise the amount of data that is held in memory at a
    time, and hence the memory usage of exports. Currently, the most data held
    in data at a time is an entire POT file.
    """
    potemplate = None
    sequence = None

    exported_file = None
    msgset = None

    for row in rows:
        new_potemplate = False
        new_msgset = False

        # Skip messages which aren't in the PO template.
        if row.sequence == 0:
            continue

        # The PO template has changed, thus so must have the PO file.
        if row.potemplate != potemplate:
            new_potemplate = True
            new_msgset = True

        # If the sequence number changes, the POT file has changed, we start a
        # new message set.
        if row.sequence != sequence:
            new_msgset = True

        # The order of output/creation is as follows:
        #
        # - if we need to create a new message set, output the old one
        # - if we need to create a new POT file
        #   - output the old one
        #   - create a new one
        # - if we need to create a new message set, create the new one
        #
        # Why things are ordered in this way: if we need to create a new POT
        # file, the old message set needs to be added to the old POT file
        # before it is output, and the new message set needs to be added to
        # the new POT file, and so the new PO file must be created first.
        if new_msgset:
            # Output the current message set.
            if msgset is not None:
                exported_file.append(msgset)

        if new_potemplate:
            # If the POT file has changed, flush the old one and print the
            # header for the new one.

            # Output the current POT file.
            if exported_file is not None:
                exported_file_content = exported_file.dump_file()
                pofile_output(potemplate, None, None, exported_file_content)

            # Get the pot header
            if row.header is None:
                header_value = ''
            else:
                header_value = row.header
            header = POHeader(
                msgstr=header_value)
            # PO templates have always the fuzzy flag set on headers.
            header.flags.add('fuzzy')
            # The parsing finished, we need this to get the header available.
            header.updateDict()
            if force_utf8:
                # Change the charset declared for this file.
                header['Content-Type'] = 'text/plain; charset=UTF-8'
                header.updateDict()

            exported_file = OutputPOFile(header)

        if new_msgset:
            # Create new message set

            if row.sequence == 0:
                # The pot sequence is zero which means that this message is
                # not anymore valid for the IPOTemplate we are handling.
                # Ignore it.
                continue

            msgset = OutputMsgSet(exported_file)

            msgset.sequence = row.sequence
            msgset.obsolete = False

        # Because of the way the database view works, message IDs will appear
        # multiple times. We see how many we've added already to check whether
        # the message ID/translation in the current row are ones we need to add.

        # Note that the msgid plural form must be equal to the number of
        # message IDs

        if row.pluralform == len(msgset.msgids):
            msgset.add_msgid(row.msgid)

        if row.commenttext and not msgset.commenttext:
            msgset.commenttext = row.commenttext

        if row.sourcecomment and not msgset.sourcecomment:
            msgset.sourcecomment = row.sourcecomment

        if row.filereferences and not msgset.filereferences:
            msgset.filereferences = row.filereferences

        if row.flagscomment and not msgset.flags:
            msgset.flags = [
                flag.strip()
                for flag in row.flagscomment.split(',')
                if flag
                ]

        potemplate = row.potemplate
        sequence = row.sequence

    # If we've processed all the rows, output the last message set and POT
    # file.

    if msgset:
        exported_file.append(msgset)

    if exported_file is not None:
        exported_file_content = exported_file.dump_file()
        pofile_output(potemplate, None, None, exported_file_content)


class FilePOFileOutput:
    """Output PO files from an export to a single file handle."""

    implements(IPOFileOutput)

    def __init__(self, filehandle):
        self.filehandle = filehandle

    def __call__(self, potemplate, language, variant, contents):
        """See IPOFileOutput."""
        self.filehandle.write(contents)

class TemplateTarballPOFileOutput:
    """Add exported PO files to a tarball."""

    implements(IPOFileOutput)

    def __init__(self, archive, directory):
        self.archive = archive
        self.directory = directory

    def __call__(self, potemplate, language, variant, contents):
        """See IPOFileOutput."""

        if language is None:
            # We are exporting an IPOTemplate.
            name = '%s.pot' % potemplate.potemplatename.translationdomain
        else:
            # We are exporting an IPOFile
            language_code = language.code.encode('ascii')

            if variant is not None:
                code = '%s@%s' % (language_code, variant.encode('UTF-8'))
            else:
                code = language_code

            code = language.code.encode('ascii')
            name = '%s.po' % code

        # Put it in the archive.
        fileinfo = tarfile.TarInfo("%s/%s" % (self.directory, name))
        fileinfo.size = len(contents)
        fileinfo.mtime = int(time.time())
        self.archive.addfile(fileinfo, StringIO(contents))

def export_potemplate_tarball(filehandle, potemplate, force_utf8=False):
    """Export a tarball of translations for a PO template to a filehandle."""

    # Create a tarfile.

    archive = tarfile.open('', 'w:gz', filehandle)

    # Create the directory the PO files will be put in.
    directory = 'rosetta-%s' % potemplate.potemplatename.name.encode('ascii')
    dirinfo = tarfile.TarInfo(directory)
    dirinfo.type = tarfile.DIRTYPE
    dirinfo.mtime = int(time.time())
    archive.addfile(dirinfo)

    rows = getUtility(IVPOExportSet).get_potemplate_rows(potemplate)
    pofile_output = TemplateTarballPOFileOutput(archive, directory)
    export_rows(rows, pofile_output, force_utf8)

    archive.close()

class DistroReleaseTarballPOFileOutput:
    """Add exported PO files to a tarball using language pack directory
    structure.
    """

    def __init__(self, release, archive):
        self.release = release
        self.archive = archive

    def __call__(self, potemplate, language, variant, contents):
        """See IPOFileOutput."""

        language_code = language.code.encode('ascii')

        if variant is not None:
            code = '%s@%s' % (language_code, variant.encode('UTF-8'))
        else:
            code = language_code

        domain = potemplate.potemplatename.translationdomain.encode('ascii')
        path = os.path.join(
            'rosetta-%s' % self.release.name,
            code,
            'LC_MESSAGES',
            '%s.po' % domain
            )
        self.archive.add_file(path, contents)

def export_distrorelease_tarball(filehandle, release, date=None):
    """Export a tarball of translations for a distribution release."""

    # Open the archive.
    archive = RosettaWriteTarFile(filehandle)

    # Do the export.
    pofiles = getUtility(IVPOExportSet).get_distrorelease_pofiles(
        release, date)
    pofile_output = DistroReleaseTarballPOFileOutput(release, archive)

    for pofile in pofiles:
        pofile_output(
            potemplate=pofile.potemplate,
            language=pofile.language,
            variant=pofile.variant,
            contents=pofile.export())

    # Add a timestamp file.
    path = 'rosetta-%s/timestamp.txt' % release.name
    contents = datetime.datetime.utcnow().strftime('%Y%m%d\n')
    archive.add_file(path, contents)

    archive.close()

class POTemplateExporter:
    """Adapt a PO template for export."""

    implements(IPOTemplateExporter)

    def __init__(self, potemplate):
        self.potemplate = potemplate
        self.force_utf8 = False

    def export_pofile(self, language, variant=None, included_obsolete=True):
        """See IPOTemplateExporter."""

        outputbuffer = StringIO()
        self.export_pofile_to_file(outputbuffer, language, variant,
            included_obsolete)
        return outputbuffer.getvalue()

    def export_pofile_to_file(self, filehandle, language, variant=None,
                              included_obsolete=True):
        """See IPOTemplateExporter."""
        rows = getUtility(IVPOExportSet).get_pofile_rows(
            self.potemplate, language, variant, included_obsolete)
        pofile_output = FilePOFileOutput(filehandle)
        export_rows(rows, pofile_output, self.force_utf8)

    def export_potemplate(self):
        """See IPOTemplateExporter."""
        outputbuffer = StringIO()
        self.export_potemplate_to_file(outputbuffer)
        return outputbuffer.getvalue()

    def export_potemplate_to_file(self, filehandle):
        """See IPOTemplateExporter."""
        rows = getUtility(IVPOTExportSet).get_potemplate_rows(self.potemplate)
        pofile_output = FilePOFileOutput(filehandle)
        export_pot_rows(rows, pofile_output, self.force_utf8)

    def export_tarball(self):
        """See IPOTemplateExporter."""

        outputbuffer = StringIO()
        export_potemplate_tarball(
            outputbuffer, self.potemplate, force_utf8=self.force_utf8)
        return outputbuffer.getvalue()

    def export_tarball_to_file(self, filehandle):
        """See IPOTemplateExporter."""
        export_potemplate_tarball(
            filehandle, self.potemplate, force_utf8=self.force_utf8)

class DistroReleasePOExporter:
    """Adapt a distribution release for PO exports."""

    implements(IDistroReleasePOExporter)

    def __init__(self, release):
        self.release = release

    def export_tarball(self, date=None):
        """See IDistroReleasePOExporter."""

        outputbuffer = StringIO()
        export_distrorelease_tarball(outputbuffer, self.release, date)
        return outputbuffer.getvalue()

    def export_tarball_to_file(self, filehandle, date=None):
        """See IDistroReleasePOExporter."""
        export_distrorelease_tarball(filehandle, self.release, date)


class MOCompilationError(Exception):
    pass

class MOCompiler:
    """Compile PO files to MO files."""

    MSGFMT = '/usr/bin/msgfmt'

    def compile(self, pofile):
        """Return a MO version of the given PO file."""

        msgfmt = subprocess.Popen(
            args=[MOCompiler.MSGFMT, '-v', '-o', '-', '-'],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        stdout, stderr = msgfmt.communicate(pofile)

        if msgfmt.returncode != 0:
            raise MOCompilationError("PO file compilation failed:\n" + stdout)

        return stdout

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

import datetime
import os
import subprocess
import tarfile
import time
from StringIO import StringIO

from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.helpers import RosettaWriteTarFile

from canonical.launchpad.interfaces import IPOTemplateExporter
from canonical.launchpad.interfaces import IDistroReleasePOExporter
from canonical.launchpad.interfaces import IPOFileOutput
from canonical.launchpad.interfaces import IVPOExportSet

from canonical.launchpad.components.poparser import POMessage, POHeader

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
        chunks.extend([msgset.export_string() for msgset in msgsets])

        return '\n\n'.join(chunks)

class OutputMsgSet:
    """Buffer message set data for output."""

    def __init__(self, pofile):
        self.pofile = pofile
        self.msgids = []
        self.msgstrs = []
        self.flags = []
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

    def export_string(self):
        """Return a string representation of this message set.

        Raises a ValueError if there are errors in the message set.
        """

        if len(self.msgids) > 2:
            raise ValueError("Too many message IDs for a message set.")
        elif len(self.msgids) == 2:
            msgidPlural = self.msgids[1]

            # If there are fewer translations than the PO file's header
            # specifies, add blank ones.

            while len(self.msgstrs) < self.pofile.header.nplurals:
                self.msgstrs.append('')
        elif self.msgids:
            msgidPlural = None
        else:
            raise ValueError(
                "Can't export a message set with no message IDs.")

        if len(self.msgstrs) > 1:
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

        return unicode(message).encode(self.pofile.header.charset)

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

def export_rows(rows, pofile_output):
    """Convert a list of PO file export view rows to a set of PO files.

    pofile_output must provide IPOFileOutput. It is used to output the
    generated PO files.

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

    pofile = None
    msgset = None

    for row in rows:
        new_pofile = False
        new_msgset = False

        # Skip messages which are neither in the PO template nor in the PO
        # file. (Messages which are in the PO template but not in the PO file
        # are untranslated, and messages which are not in the PO template but
        # in the PO file are obsolete.)

        if row.potsequence == 0 and row.posequence == 0:
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

            if msgset:
                pofile.append(msgset)

        if new_pofile:
            # If the PO file has changed, flush the old one and print the
            # header for the new one.

            # Output the current PO file.

            if pofile:
                pofile_output(potemplate, language, variant,
                    pofile.export_string())

            # Generate the header of the new PO file.

            header = POHeader(
                commentText=row.potopcomment,
                msgstr=row.poheader)

            if row.pofuzzyheader:
                header.flags.add('fuzzy')

            header.finish()

            # Update header fields.

            if row.potheader:
                pot_header = POHeader(
                    msgstr=row.potheader)
                pot_header.finish()

                if 'Domain' in pot_header:
                    header['Domain'] = pot_header['Domain']


            # This part is conditional on the PO file being present in order
            # to make it easier to fake data for testing.

            if (row.pofile is not None and
                row.pofile.latestsubmission is not None):
                # Update the last translator field.

                submission = row.pofile.latestsubmission
                assert not submission.person.isTeam(), submission.person.name
                header['Last-Translator'] = (
                    last_translator_text(submission.person))

                # Update the revision date field.

                header['PO-Revision-Date'] = (
                    submission.datecreated.strftime('%F %R%z'))

            # Create the new PO file.

            pofile = OutputPOFile(header)

        if new_msgset:
            # Create new message set

            msgset = OutputMsgSet(pofile)
            msgset.fuzzy = row.isfuzzy

            if row.potsequence:
                msgset.sequence = row.potsequence
                msgset.obsolete = False
            else:
                msgset.sequence = row.posequence
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

        if row.activesubmission and \
            row.translationpluralform >= len(msgset.msgstrs):
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
        pofile.append(msgset)

    if pofile:
        pofile_output(potemplate, language, variant, pofile.export_string())

class FilePOFileOutput:
    """Output PO files from an export to a single file handle."""

    implements(IPOFileOutput)

    def __init__(self, filehandle):
        self.filehandle = filehandle

    def __call__(self, potemplate, language, variant, pofile):
        """See IPOFileOutput."""
        self.filehandle.write(pofile)

def export_pofile(filehandle, potemplate, language, variant=None):
    """Export a single PO file for a PO template."""

    rows = getUtility(IVPOExportSet).get_pofile_rows(
        potemplate, language, variant)
    pofile_output = FilePOFileOutput(filehandle)
    export_rows(rows, pofile_output)

class TemplateTarballPOFileOutput:
    """Add exported PO files to a tarball."""

    implements(IPOFileOutput)

    def __init__(self, archive, directory):
        self.archive = archive
        self.directory = directory

    def __call__(self, potemplate, language, variant, contents):
        """See IPOFileOutput."""

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

def export_potemplate_tarball(filehandle, potemplate):
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
    export_rows(rows, pofile_output)

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

    def export_pofile(self, language, variant=None):
        """See IPOTemplateExporter."""

        outputbuffer = StringIO()
        export_pofile(outputbuffer, self.potemplate, language, variant)
        return outputbuffer.getvalue()

    def export_pofile_to_file(self, filehandle, language, variant=None):
        """See IPOTemplateExporter."""
        export_pofile(filehandle, self.potemplate, language, variant)

    def export_tarball(self):
        """See IPOTemplateExporter."""

        outputbuffer = StringIO()
        export_potemplate_tarball(outputbuffer, self.potemplate)
        return outputbuffer.getvalue()

    def export_tarball_to_file(self, filehandle):
        """See IPOTemplateExporter."""
        export_potemplate_tarball(filehandle, self.potemplate)

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


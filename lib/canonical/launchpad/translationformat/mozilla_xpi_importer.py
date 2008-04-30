# Copyright 2006-2008 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaXpiImporter',
    ]

import cElementTree
import textwrap
from email.Utils import parseaddr
from os.path import splitext
from StringIO import StringIO
from old_xmlplus.parsers.xmlproc import dtdparser, xmldtd, utils
from zipfile import ZipFile
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatImporter, ITranslationHeaderData, TranslationConstants,
    TranslationFileFormat, TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationFileData, TranslationMessageData)
from canonical.launchpad.translationformat.xpi_manifest import (
    make_jarpath, XpiManifest)
from canonical.librarian.interfaces import ILibrarianClient


class MozillaHeader:
    implements(ITranslationHeaderData)

    def __init__(self, header_content):
        self._raw_content = header_content
        self.is_fuzzy = False
        self.template_creation_date = None
        self.translation_revision_date = None
        self.language_team = None
        self.has_plural_forms = False
        self.number_plural_forms = 0
        self.plural_form_expression = None
        self.charset = 'UTF-8'
        self.launchpad_export_date = None
        self.comment = None

    def getRawContent(self):
        """See `ITranslationHeaderData`."""
        return self._raw_content

    def updateFromTemplateHeader(self, template_header):
        """See `ITranslationHeaderData`."""
        # Nothing to do for this format.
        return

    def getLastTranslator(self):
        """See `ITranslationHeaderData`."""
        name = None
        email = None
        parse = cElementTree.iterparse(StringIO(self._raw_content))
        for event, elem in parse:
            if elem.tag == "{http://www.mozilla.org/2004/em-rdf#}contributor":
                # This file would have more than one contributor, but
                # we are only getting latest one.
                name, email = parseaddr(elem.text)

        return name, email

    def setLastTranslator(self, email, name=None):
        """Set last translator information.

        :param email: A string with the email address for last translator.
        :param name: The name for the last translator or None.
        """
        # Nothing to do for this format.
        return


def add_source_comment(message, comment):
    """Add the given comment inside message.source_comment."""
    if message.source_comment:
        message.source_comment += comment
    else:
        message.source_comment = comment

    if not message.source_comment.endswith('\n'):
        message.source_comment += '\n'


class MozillaZipFile:
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It handles embedded jar, dtd and properties files.
    """

    def __init__(self, filename, content, xpi_path='', manifest=None):
        """Open zip (or XPI, or jar) file and scan its contents.

        :param filename: Name of this zip (XPI/jar) file.
        :param content: The data making up this zip file.
        :param xpi_path: Full path of this file inside the XPI archive.
            Leave blank for the XPI file itself.
        :param manifest: `XpiManifest` representing the XPI archive's
            manifest file, if any.
        """
        self.filename = filename
        self.header = None
        self.messages = []
        self.last_translator = None

        archive = ZipFile(StringIO(content), 'r')
        for entry in sorted(archive.namelist()):

            # We're only interested in this file if its name ends with one of
            # these dot suffixes.
            root, suffix = splitext(entry)
            if suffix not in ['.jar', '.dtd', '.properties']:
                continue

            if suffix == '.jar':
                subpath = make_jarpath(xpi_path, entry)
            else:
                subpath = "%s/%s" % (xpi_path, entry)

            # If we have a manifest, we skip anything that it doesn't list as
            # having something useful for us.
            if manifest is None:
                chrome_path = None
            else:
                if suffix == '.jar':
                    chrome_path = None
                    if not manifest.containsLocales(subpath):
                        # Jar file contains no directories with locale files.
                        continue
                else:
                    chrome_path, locale = manifest.getChromePathAndLocale(
                        subpath)
                    if chrome_path is None:
                        # File is not in a directory containing locale files.
                        continue

            # Parse file, subsume its messages.
            parsed_file = self._parseFile(
                archive, entry, subpath, chrome_path, manifest)
            self.extend(parsed_file.messages)

        # Eliminate duplicate messages.
        seen_messages = set()
        deletions = []
        for index, message in enumerate(self.messages):
            identifier = (message.msgid_singular, message.context)
            if identifier in seen_messages:
                # This message is a duplicate.  Mark it for removal.
                deletions.append(index)
            else:
                seen_messages.add(identifier)
        for index in reversed(deletions):
            del self.messages[index]

    def _parseFile(self, archive, entry, subpath, chrome_path, manifest):
        """Read file "`entry`" from zip file "`archive`", and parse it.

        :param archive: `ZipFile` to read from.
        :param entry: name (including path) of file within `archive`.
        :param subpath: file's path inside overall XPI file.  Used to figure
            out paths inside jar files.
        :param chrome_path: file's chrome path within the XPI file.
        :param manifest: optional `XpiManifest` file describint the overall
            XPI file we're reading.
        """
        data = archive.read(entry)

        root, suffix = splitext(entry)
        if suffix == '.jar':
            parsed_file = MozillaZipFile(filename=entry, xpi_path=subpath,
            content=data, manifest=manifest)
        elif suffix == '.dtd':
            parsed_file = DtdFile(filename=entry, chrome_path=chrome_path,
                content=data)
        elif suffix == '.properties':
            parsed_file = PropertyFile(filename=entry,
                chrome_path=chrome_path, content=data)
        else:
            raise AssertionError(
                "Unexpected filename suffix: %s." % suffix)

        return parsed_file

    def _updateMessageFileReferences(self, message):
        """Update message's file_references with full path."""
        if self.filename is not None:
            # Include self.filename to this entry's file reference.
            if self.filename.endswith('.jar'):
                filename = '%s!' % self.filename
            else:
                filename = self.filename
            message.file_references_list = [
                "%s/%s" % (filename, file_reference)
                for file_reference in message.file_references_list]
        # Fill file_references field based on the list of files we
        # found.
        message.file_references = ', '.join(
            message.file_references_list)

    def _isCommandKeyMessage(self, message):
        """Whether the message represents a command key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid_singular.endswith('.commandkey') or
                message.msgid_singular.endswith('.key')))

    def _isAccessKeyMessage(self, message):
        """Whether the message represents an access key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid_singular.endswith('.accesskey')))

    def extend(self, newdata):
        """Append 'newdata' messages to self.messages."""
        for message in newdata:
            self._updateMessageFileReferences(message)

            # Special case accesskeys and commandkeys:
            # these are single letter messages, lets display
            # the value as a source comment.
            if self._isCommandKeyMessage(message):
                comment = u'\n'.join(textwrap.wrap(
                    u"Select the shortcut key that you want to use. It should"
                    u" be translated, but often shortcut keys (for example"
                    u" Ctrl + KEY) are not changed from the original. If a"
                    u" translation already exists, please don't change it if"
                    u" you are not sure about it. Please find the context of"
                    u" the key from the end of the 'Located in' text below."))
                add_source_comment(message, comment)
            elif self._isAccessKeyMessage(message):
                comment = u'\n'.join(textwrap.wrap(
                    u"Select the access key that you want to use. These have"
                    u" to be translated in a way that the selected"
                    u" character is present in the translated string of the"
                    u" label being referred to, for example 'i' in 'Edit'"
                    u" menu item in English. If a translation already"
                    u" exists, please don't change it if you are not sure"
                    u" about it. Please find the context of the key from the"
                    u" end of the 'Located in' text below."))
                add_source_comment(message, comment)
            self.messages.append(message)


class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    msgids are stored as entities. This class extracts it along
    with translations, comments and source references.
    """
    def __init__(self, parser, filename, chrome_path, messages):
        self.started = False
        self.last_comment = None
        self.chrome_path = chrome_path
        self.messages = messages
        self.filename = filename
        xmldtd.WFCDTD.__init__(self, parser)

    def dtd_start(self):
        """See `xmldtd.WFCDTD`."""
        self.started = True

    def dtd_end(self):
        """See `xmldtd.WFCDTD`."""
        self.started = False

    def handle_comment(self, contents):
        """See `xmldtd.WFCDTD`."""
        if not self.started:
            return

        if self.last_comment is not None:
            self.last_comment += contents
        elif len(contents) > 0:
            self.last_comment = contents

        if self.last_comment and not self.last_comment.endswith('\n'):
            # Comments must end always with a new line.
            self.last_comment += '\n'

    def new_general_entity(self, name, value):
        """See `xmldtd.WFCDTD`."""
        if not self.started:
            return

        message = TranslationMessageData()
        message.msgid_singular = name
        # CarlosPerelloMarin 20070326: xmldtd parser does an inline
        # parsing which means that the content is all in a single line so we
        # don't have a way to show the line number with the source reference.
        message.file_references_list = ["%s(%s)" % (self.filename, name)]
        message.addTranslation(TranslationConstants.SINGULAR_FORM, value)
        message.singular_text = value
        message.context = self.chrome_path
        message.source_comment = self.last_comment
        self.messages.append(message)
        self.started += 1
        self.last_comment = None


class DtdFile:
    """Class for reading translatable messages from a .dtd file.

    It uses DTDParser which fills self.messages with parsed messages.
    """
    def __init__(self, filename, chrome_path, content):
        self.messages = []
        self.filename = filename
        self.chrome_path = chrome_path

        # .dtd files are supposed to be using UTF-8 encoding, if the file is
        # using another encoding, it's against the standard so we reject it
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid UTF-8 text')

        parser = dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, chrome_path, self.messages)
        parser.set_dtd_consumer(dtd)
        parser.parse_string(content)


def valid_property_msgid(msgid):
    """Whether the given msgid follows the restrictions to be valid.

    Checks done are:
        - It cannot have white spaces.
    """
    return u' ' not in msgid


class PropertyFile:
    """Class for reading translatable messages from a .properties file.

    The file format is described at:
    http://www.mozilla.org/projects/l10n/mlp_chrome.html#text
    """

    license_block_text = u'END LICENSE BLOCK'

    def __init__(self, filename, chrome_path, content):
        """Constructs a dictionary from a .properties file.

        :arg filename: The file name where the content came from.
        :arg content: The file content that we want to parse.
        """
        self.filename = filename
        self.chrome_path = chrome_path
        self.messages = []

        # Parse the content.
        self.parse(content)

    def parse(self, content):
        """Parse given content as a property file.

        Once the parse is done, self.messages has a list of the available
        `ITranslationMessageData`s.
        """

        # .properties files are supposed to be unicode-escaped, but we know
        # that there are some .xpi language packs that instead, use UTF-8.
        # That's against the specification, but Mozilla applications accept
        # it anyway, so we try to support it too.
        # To do this support, we read the text as being in UTF-8
        # because unicode-escaped looks like ASCII files.
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid unicode-escaped text')

        line_num = 0
        is_multi_line_comment = False
        last_comment = None
        last_comment_line_num = 0
        ignore_comment = False
        is_message = False
        translation = u''
        for line in content.splitlines():
            # Now, to "normalize" all to the same encoding, we encode to
            # unicode-escape first, and then decode it to unicode
            # XXX: Danilo 2006-08-01: we _might_ get performance
            # improvements if we reimplement this to work directly,
            # though, it will be hard to beat C-based de/encoder.
            # This call unescapes everything so we don't need to care about
            # quotes escaping.
            line = line.encode('unicode_escape').decode('unicode_escape')

            line_num += 1
            if not is_multi_line_comment:
                # Remove any white space before the useful data, like
                # ' # foo'.
                line = line.lstrip()
                if line.startswith(u'#'):
                    # It's a whole line comment.
                    ignore_comment = False
                    line = line[1:].strip()
                    if last_comment:
                        last_comment += line
                    elif len(line) > 0:
                        last_comment = line

                    if last_comment and not last_comment.endswith('\n'):
                        # Comments must end always with a new line.
                        last_comment += '\n'

                    last_comment_line_num = line_num
                    continue
                elif len(line) == 0:
                    # It's an empty line. Reset any previous comment we have.
                    last_comment = None
                    last_comment_line_num = 0
                    ignore_comment = False
            while line:
                if is_multi_line_comment:
                    if line.startswith(u'*/'):
                        # The comment ended, we jump the closing tag and
                        # continue with the parsing.
                        line = line[2:]
                        is_multi_line_comment = False
                        last_comment_line_num = line_num
                        if ignore_comment:
                            last_comment = None
                            ignore_comment = False

                        # Comments must end always with a new line.
                        last_comment += '\n'
                    elif line.startswith(self.license_block_text):
                        # It's a comment with a license notice, this
                        # comment can be ignored.
                        ignore_comment = True
                        # Jump the whole tag
                        line = line[len(self.license_block_text):]
                    else:
                        # Store the character.
                        if last_comment is None:
                            last_comment = line[0]
                        elif last_comment_line_num == line_num:
                            last_comment += line[0]
                        else:
                            last_comment = u'%s\n%s' % (last_comment, line[0])
                            last_comment_line_num = line_num
                        # Jump the processed char.
                        line = line[1:]
                    continue
                elif line.startswith(u'//'):
                    # It's an 'end of the line comment'
                    last_comment = '%s\n' % line[2:].strip()
                    last_comment_line_num = line_num
                    # Jump to next line
                    break
                elif line.startswith(u'/*'):
                    # It's a multi line comment
                    is_multi_line_comment = True
                    ignore_comment = False
                    last_comment_line_num = line_num
                    # Jump the comment starting tag
                    line = line[2:]
                    continue
                elif is_message:
                    # Store the char and continue.
                    translation += line[0]
                    line = line[1:]
                    continue
                elif u'=' in line:
                    # Looks like a message string.
                    (key, value) = line.split('=', 1)
                    # Remove leading and trailing white spaces.
                    key = key.strip()

                    if valid_property_msgid(key):
                        is_message = True
                        # Jump the msgid, control chars and leading white
                        # space.
                        line = value.lstrip()
                        continue
                    else:
                        raise TranslationFormatSyntaxError(
                            line_number=line_num,
                            message=u"invalid msgid: '%s'" % key)
                else:
                    # Got a line that is not a valid message nor a valid
                    # comment. Ignore it because main en-US.xpi catalog from
                    # Firefox has such line/error. We follow the 'be strict
                    # with what you export, be permisive with what you import'
                    # policy.
                    break
            if is_message:
                # We just parsed a message, so we need to add it to the list
                # of messages.
                if ignore_comment or last_comment_line_num < line_num - 1:
                    # We must ignore the comment or either the comment is not
                    # the last thing before this message or is not in the same
                    # line as this message.
                    last_comment = None
                    ignore_comment = False

                message = TranslationMessageData()
                message.msgid_singular = key
                message.context = self.chrome_path
                message.file_references_list = [
                    "%s:%d(%s)" % (self.filename, line_num, key)]
                value = translation.strip()
                message.addTranslation(
                    TranslationConstants.SINGULAR_FORM, value)
                message.singular_text = value
                message.source_comment = last_comment
                self.messages.append(message)

                # Reset status vars.
                last_comment = None
                last_comment_line_num = 0
                is_message = False
                translation = u''


class MozillaXpiImporter:
    """Support class to import Mozilla .xpi files."""

    implements(ITranslationFormatImporter)

    def __init__(self):
        self.basepath = None
        self.productseries = None
        self.distroseries = None
        self.sourcepackagename = None
        self.is_published = False
        self.content = None
        self._translation_file = None

    def getFormat(self, file_contents):
        """See `ITranslationFormatImporter`."""
        return TranslationFileFormat.XPI

    priority = 0

    # using "application/x-xpinstall" would trigger installation in
    # firefox.
    content_type = 'application/zip'

    file_extensions = ['.xpi']
    template_suffix = 'en-US.xpi'

    uses_source_string_msgids = True

    def _extract_manifest(self, archive, contained_files):
        """Extract manifest file from `ZipFile`."""
        manifest_names = ['chrome.manifest', 'en-US.manifest']
        for filename in manifest_names:
            if filename in contained_files:
                return XpiManifest(archive.read(filename))

        return None

    def _extract_install_rdf(self, archive, contained_files):
        if 'install.rdf' not in contained_files:
            raise TranslationFormatInvalidInputError("No install.rdf found")
        return MozillaHeader(archive.read('install.rdf'))

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        self._translation_file = TranslationFileData()
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        # Before going into MozillaZipFile, extract metadata.
        content = self.content.read()
        archive = ZipFile(StringIO(content), 'r')
        contained_files = set(archive.namelist())
        manifest = self._extract_manifest(archive, contained_files)
        header = self._extract_install_rdf(archive, contained_files)

        archive = None

        parser = MozillaZipFile(self.basepath, content, manifest=manifest)

        self._translation_file.header = header
        self._translation_file.messages = parser.messages

        return self._translation_file

    def getHeaderFromString(self, header_string):
        """See `ITranslationFormatImporter`."""
        return MozillaHeader(header_string)


# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaXpiImporter',
    ]

import logging
import os
import cElementTree
from email.Utils import parseaddr
from StringIO import StringIO
from xml.parsers.xmlproc import dtdparser, xmldtd, utils
from zipfile import ZipFile
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatImporter, ITranslationHeader, TranslationConstants,
    TranslationFormatInvalidInputError, TranslationFormatSyntaxError)
from canonical.launchpad.translationformat.translation_common_format import (
    TranslationFile, TranslationMessage)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import TranslationFileFormat


class MozillaHeader:
    implements(ITranslationHeader)

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
        """See `ITranslationHeader.`"""
        return self._raw_content

    def updateFromTemplateHeader(self, template_header):
        """See `ITranslationHeader.`"""
        # Nothing to do for this format.
        return

    def getLastTranslator(self):
        """See `ITranslationHeader.`"""
        name = None
        email = None
        for event, elem in cElementTree.iterparse(StringIO(self._raw_content)):
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


class MozillaZipFile:
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It handles embedded jar, dtd and properties files.
    """

    def __init__(self, filename, content):
        self.filename = filename
        self.header = None
        self.messages = []
        self._msgids = []
        self.last_translator = None

        zip = ZipFile(StringIO(content), 'r')
        for entry in zip.namelist():
            if entry.endswith('.properties'):
                data = zip.read(entry)
                pf = PropertyFile(filename=entry, content=data)
                self.extend(pf.messages)
            elif entry.endswith('.dtd'):
                data = zip.read(entry)
                dtdf = DtdFile(filename=entry, content=data)
                self.extend(dtdf.messages)
            elif entry.endswith('.jar'):
                data = zip.read(entry)
                jarf = MozillaZipFile(filename=entry, content=data)
                self.extend(jarf.messages)
            elif entry == 'install.rdf':
                data = zip.read(entry)
                self.header = MozillaHeader(data)
            else:
                # Ignore this file, we don't need to do anything with it.
                continue

    def _updateMessageFileReferences(self, message):
        """Update message's file_references with full path."""
        if self.filename is not None:
            # Include self.filename to this entry's file reference.
            message.file_references_list = [
                os.path.join(self.filename, file_reference)
                for file_reference in message.file_references_list]
        # Fill file_references field based on the list of files we
        # found.
        message.file_references = ', '.join(
            message.file_references_list)

    def _isKeyShortcutMessage(self, message):
        """Whether the message represents a key shortcut."""
        return (
            self.filename is not None and
            self.filename.startswith('en-US.xpi') and
            message.translations and (
                message.msgid.endswith('.accesskey') or
                message.msgid.endswith('.commandkey')))

    def extend(self, newdata):
        """Append 'newdata' messages to self.messages."""
        for message in newdata:
            if message.msgid in self._msgids:
                logging.info("Duplicate message ID '%s'." % message.msgid)
                continue

            self._updateMessageFileReferences(message)

            # Special case accesskeys and commandkeys:
            # these are single letter messages, lets display
            # the value as a source comment.
            if self._isKeyShortcutMessage(message):
                message.source_comment = u"Default key in en_US: '%s'" % (
                    message.translations[TranslationConstants.SINGULAR_FORM])
                message.resetAllTranslations()

            self._msgids.append(message.msgid)
            self.messages.append(message)


class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    msgids are stored as entities. This class extracts it along
    with translations, comments and source references.
    """
    def __init__(self, parser, filename, messages):
        self.started = False
        self.last_comment = None
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

        # Comments would be multiline.
        for line in contents.split(u'\n'):
            line = line.strip()
            if self.last_comment is not None:
                self.last_comment = u'%s %s' % (self.last_comment, line)
            elif len(line) > 0:
                self.last_comment = line

    def new_general_entity(self, name, value):
        """See `xmldtd.WFCDTD`."""
        if not self.started:
            return

        message = TranslationMessage()
        message.msgid = name
        # CarlosPerelloMarin 20070326: xmldtd parser does an inline
        # parsing which means that the content is all in a single line so we
        # don't have a way to show the line number with the source reference.
        message.file_references_list = ["%s(%s)" % (self.filename, name)]
        message.addTranslation(TranslationConstants.SINGULAR_FORM, value)
        message.source_comment = self.last_comment
        self.messages.append(message)
        self.started += 1
        self.last_comment = None


class DtdFile:
    """Class for reading translatable messages from a .dtd file.

    It uses DTDParser which fills self.messages with parsed messages.
    """
    def __init__(self, filename, content):
        self.messages = []
        self.filename = filename

        # .dtd files are supposed to be using UTF-8 encoding, if the file is
        # using another encoding, it's against the standard so we reject it
        try:
            content = content.decode('utf-8')
        except UnicodeDecodeError:
            raise TranslationFormatInvalidInputError, (
                'Content is not valid UTF-8 text')

        parser=dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, self.messages)
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

    def __init__(self, filename, content):
        """Constructs a dictionary from a .properties file.

        :arg filename: The file name where the content came from.
        :arg content: The file content that we want to parse.
        """
        self.filename = filename
        self.messages = []

        # Parse the content.
        self.parse(content)

    def parse(self, content):
        """Parse given content as a property file.

        Once the parse is done, self.messages has a list of the available
        ITranslationMessages.
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

        # Now, to "normalize" all to the same encoding, we encode to
        # unicode-escape first, and then decode it to unicode
        # XXX: Danilo 2006-08-01: we _might_ get performance
        # improvements if we reimplement this to work directly,
        # though, it will be hard to beat C-based de/encoder.
        # This call unescapes everything so we don't need to care about quotes
        # escaping.
        content = content.encode('unicode_escape').decode('unicode_escape')

        line_num = 0
        is_multi_line_comment = False
        last_comment = None
        last_comment_line_num = 0
        ignore_comment = False
        is_message = False
        translation = u''
        for line in content.split(u'\n'):
            line_num += 1
            if not is_multi_line_comment:
                if line.startswith(u'#'):
                    # It's a whole line comment.
                    ignore_comment = False
                    line = line[1:].strip()
                    if last_comment:
                        last_comment = u' '.join((last_comment, line))
                    else:
                        last_comment = line
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
                    last_comment = line[2:].strip()
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
                    # commnet. Ignore it because main en-US.xpi catalog from
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

                message = TranslationMessage()
                message.msgid = key
                message.file_references_list = [
                    "%s:%d(%s)" % (self.filename, line_num, key)]
                message.addTranslation(
                    TranslationConstants.SINGULAR_FORM,
                    translation.strip())
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

    try_this_format_before = None

    # using "application/x-xpinstall" would trigger installation in
    # firefox.
    content_type = 'application/zip'

    file_extensions = ['.xpi']

    uses_source_string_msgids = True

    def parse(self, translation_import_queue_entry):
        """See `ITranslationFormatImporter`."""
        self._translation_file = TranslationFile()
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        parser = MozillaZipFile(self.basepath, self.content.read())

        self._translation_file.header = parser.header
        self._translation_file.messages = parser.messages

        return self._translation_file

    def getHeaderFromString(self, header_string):
        """See `ITranslationFormatImporter`."""
        return MozillaHeader(header_string)

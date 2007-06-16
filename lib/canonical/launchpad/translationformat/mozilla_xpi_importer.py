# Copyright 2006-2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'MozillaXpiImporter',
    ]

import os
import cElementTree
from email.Utils import parseaddr
from StringIO import StringIO
from xml.parsers.xmlproc import dtdparser, xmldtd, utils
from zipfile import ZipFile
from zope.component import getUtility
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatImporter, ITranslationMessage,
    TranslationConstants, TranslationFormatInvalidInputError,
    TranslationFormatSyntaxError)
from canonical.librarian.interfaces import ILibrarianClient
from canonical.lp.dbschema import TranslationFileFormat


class XpiMessage:
    implements(ITranslationMessage)

    def __init__(self):
        self.msgid = None
        self.msgid_plural = None
        self.translations = []
        self.comment = None
        self.source_comment = None
        self.file_references = None
        self.flags = ()
        self.obsolete = False
        self.nplurals = None
        self.pluralExpr = None

    def flagsText(self, flags=None):
        """See ITranslationMessage."""
        if flags is not None:
            return flags

        return u''


class MozillaZipFile:
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It behaves as an iterator over all messages in the file, indexed by
    msgid's.  It handles embedded jar, dtd and properties files.
    """

    def __init__(self, filename, content, logger=None):
        self.filename = filename
        self.logger = logger
        self.header = None
        self.messages = []
        self._msgids = []
        self.last_translator = None

        zip = ZipFile(StringIO(content), 'r')
        for entry in zip.namelist():
            if entry.endswith('.properties'):
                data = zip.read(entry)
                pf = PropertyFile(filename=entry, content=data, logger=logger)
                self.extend(pf.messages)
            elif entry.endswith('.dtd'):
                data = zip.read(entry)
                dtdf = DtdFile(filename=entry, content=data, logger=logger)
                self.extend(dtdf.messages)
            elif entry.endswith('.jar'):
                data = zip.read(entry)
                jarf = MozillaZipFile(filename=entry, content=data, logger=logger)
                self.extend(jarf.messages)
            elif entry == 'install.rdf':
                data = zip.read(entry)
                for event, elem in cElementTree.iterparse(StringIO(data)):
                    if elem.tag == "{http://www.mozilla.org/2004/em-rdf#}contributor":
                        # This file would have more than one contributor, but
                        # we are only getting latest one.
                        self.last_translator = elem.text
            else:
                # Ignore this file, we don't need to do anything with it.
                continue

    def getLastTranslator(self):
        """Return a string representing last translator name and email."""
        return self.last_translator

    def extend(self, newdata):
        """Append 'newdata' messages to self.messages."""
        for message in newdata:
            if not message.msgid in self._msgids:
                if self.filename is not None:
                    # Include self.filename to this entry's file reference.
                    message.file_references_list = [
                        os.path.join(self.filename, file_reference)
                        for file_reference in message.file_references_list]
                # Fill file_references field based on the list of files we
                # found.
                message.file_references = ', '.join(
                    message.file_references_list)
                # Add an extra comment for some special msgid that refer to
                # key shortcuts.
                if (self.filename is not None and
                    self.filename.startswith('en-US.xpi') and
                    message.translations and (
                        message.msgid.endswith('.accesskey') or
                        message.msgid.endswith('.commandkey'))):
                    # Special case accesskeys and commandkeys:
                    # these are single letter messages, lets display
                    # the value as a source comment.
                    message.source_comment = u"Default key in en_US: '%s'" % (
                        message.translations[
                            TranslationConstants.SINGULAR_FORM])
                    message.translations = []
                self._msgids.append(message.msgid)
                self.messages.append(message)
            elif self.logger is not None:
                self.logger.info("Duplicate message ID '%s'." % message.msgid)


class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    Extracts all entities along with comments and source references.
    """
    def __init__(self, parser, filename, messages):
        self.started = False
        self.lastcomment = None
        self.messages = messages
        self.filename = filename
        xmldtd.WFCDTD.__init__(self, parser)

    def dtd_start(self):
        self.started = True

    def dtd_end(self):
        self.started = False

    def handle_comment(self, contents):
        if not self.started:
            return

        # Comments would be multiline.
        for line in contents.split(u'\n'):
            line = line.strip()
            if self.lastcomment is not None:
                self.lastcomment = u'%s %s' % (self.lastcomment, line)
            elif len(line) > 0:
                self.lastcomment = line

    def new_general_entity(self, name, value):
        if not self.started:
            return

        message = XpiMessage()
        message.msgid = name
        # CarlosPerelloMarin 20070326: xmldtd parser does an inline
        # parsing which means that the content is all in a single line so we
        # don't have a way to show the line number with the source reference.
        message.file_references_list = ["%s(%s)" % (self.filename, name)]
        message.translations = [value]
        message.source_comment = self.lastcomment
        self.messages.append(message)
        self.started += 1
        self.lastcomment = None


class DtdFile:
    """Class for reading translatable messages from a .dtd file.

    It behaves as an iterator over messages in the file, indexed by entity
    names from the .dtd file.
    """
    def __init__(self, filename, content, logger=None):
        self.messages = []
        self.filename = filename
        self.logger = logger

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
    """Whether the given msgid follows the restrictions to be valid."""
    # It cannot have white spaces.
    return u' ' not in msgid

class PropertyFile:
    """Class for reading translatable messages from a .properties file.

    It behaves as an iterator over messages in the file, indexed by keys
    from the .properties file.

    The file format is described at:
    http://www.mozilla.org/projects/l10n/mlp_chrome.html#text
    """

    license_block_text = u'END LICENSE BLOCK'

    def __init__(self, filename, content, logger=None):
        """Constructs a dictionary from a .properties file.

        :arg filename: The file name where the content came from.
        :arg content: The file content that we want to parse.
        :arg logger: A logger object to log events, or None.
        """
        self.filename = filename
        self.messages = []
        self.logger = logger

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
                    line = line[2:]
                    if last_comment:
                        last_comment = u'%s %s' % (last_comment, line)
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
            if is_message:
                # We just parsed a message, so we need to add it to the list
                # of messages.
                if ignore_comment or last_comment_line_num < line_num - 1:
                    # We must ignore the comment or either the comment is not
                    # the last thing before this message or is not in the same
                    # line as this message.
                    last_comment = None
                    ignore_comment = False

                message = XpiMessage()
                message.msgid = key
                message.file_references_list = [
                    "%s:%d(%s)" % (self.filename, line_num, key)]
                message.translations = [translation.strip()]
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

    def __init__(self, logger=None):
        self.logger = logger
        self.basepath = None
        self.productseries = None
        self.distroseries = None
        self.sourcepackagename = None
        self.is_published = False
        self.content = None
        self.header = None
        self.messages = []
        self.last_translator_text = None

    @property
    def format(self):
        """See ITranslationFormatImporter."""
        return TranslationFileFormat.XPI

    @property
    def content_type(self):
        """See ITranslationFormatImporter."""
        # using "application/x-xpinstall" would trigger installation in
        # firefox.
        return 'application/zip'

    @property
    def file_extensions(self):
        """See ITranslationFormatImporter."""
        return ['.xpi']

    @property
    def has_alternative_msgid(self):
        """See ITranslationFormatImporter."""
        return True

    def parse(self, translation_import_queue_entry):
        """See ITranslationFormatImporter."""
        self.basepath = translation_import_queue_entry.path
        self.productseries = translation_import_queue_entry.productseries
        self.distroseries = translation_import_queue_entry.distroseries
        self.sourcepackagename = (
            translation_import_queue_entry.sourcepackagename)
        self.is_published = translation_import_queue_entry.is_published

        librarian_client = getUtility(ILibrarianClient)
        self.content = librarian_client.getFileByAlias(
            translation_import_queue_entry.content.id)

        parser = MozillaZipFile(self.basepath, self.content.read(), self.logger)

        self.header = parser.header
        self.messages = parser.messages

        self.last_translator_text = parser.getLastTranslator()

    def getLastTranslator(self):
        """See ITranslationFormatImporter."""
        # At this point we don't have a way to figure this information from
        # the XPI file format.
        if self.last_translator_text is None:
            return None, None

        return parseaddr(self.last_translator_text)

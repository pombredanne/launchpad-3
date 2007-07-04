# Copyright 2007 Canonical Ltd.  All rights reserved.

__metaclass__ = type

__all__ = [
    'GettextPoExporter'
    ]

import os.path
from StringIO import StringIO
from zope.interface import implements

from canonical.launchpad.interfaces import (
    ITranslationFormatExporter, TranslationConstants)
from canonical.launchpad.translationformat.translation_export import (
    LaunchpadWriteTarFile, ExportedTranslationFile)
from canonical.lp.dbschema import TranslationFileFormat

def comments_text_representation(translation_message):
    r'''Return text representation of the comments.

    :param translation_message: An ITranslationMessage that will get comments
        exported.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> translation_message.flags = ('fuzzy', )
    >>> export_translation_message(translation_message)
    u'#, fuzzy\nmsgid "foo"\nmsgstr "bar"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'a'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'b')
    >>> translation_message.comment = u' blah\n'
    u'# blah\nmsgid "a"\nmsgstr "b"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'%d foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'%d bar')
    >>> translation_message.flags = ('fuzzy', 'c-format')
    >>> export_translation_message(translation_message)
    u'#, fuzzy, c-format\nmsgid "%d foo"\nmsgstr "%d bar"'
    '''
    text = []
    # comment and source_comment always end in a newline, so
    # splitting by \n always results in an empty last element
    if translation_message.comment:
        for line in translation_message.comment.split('\n')[:-1]:
            text.append(u'#' + line)
    if not translation_message.obsolete:
        # Source comments are only exported if it's not an obsolete entry.
        if translation_message.source_comment:
            for line in translation_message.source_comment.split('\n')[:-1]:
                text.append(u'#. ' + line)
        if translation_message.file_references:
            for line in translation_message.file_references.split('\n'):
                text.append(u'#: ' + line)
    if translation_message.flags:
        text.append(translation_message.flagsText())

    return u'\n'.join(text)

def wrap_text(text, prefix, wrap_width):
    r'''Return a list of strings with the given text wrapped to given width.

    :param text: Unicode string to wrap.
    :param prefix: Unicode prefix to prepend to the given text before wrapping
        it.
    :param wrap_width: The width where the text should be wrapped.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijkl'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap=20)
    u'msgid "abcdefghijkl"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijklmnopqr'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap=20)
    u'msgid ""\n"abcdefghijklmnopqr"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdef hijklm'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap=20)
    u'msgid ""\n"abcdef hijklm"\nmsgstr "z"'

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abcdefghijklmnopqr st'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap=20)
    u'msgid ""\n"abcdefghijklmnopqr "\n"st"\nmsgstr "z"'

    newlines in the text interfere with wrapping.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abc\ndef'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message, wrap=20)
    u'msgid ""\n"abc\\n"\n"def"\nmsgstr "z"'

    but not when it's just a line that ends with a newline char
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'abc\n'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'def\n')
    >>> export_translation_message(translation_message)
    u'msgid "abc\\n"\nmsgstr "def\\n"'

    It's time to test the wrapping with the '-' char:
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"WARNING: unsafe enclosing directory permissions on homedir"
    ...     u" `%s'\n")
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM,
    ...     u"WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses"
    ...         u" des Home-Verzeichnisses `%s'\n")
    >>> export_translation_message(translation_message)
    msgid "WARNING: unsafe enclosing directory permissions on homedir `%s'\n"
    msgstr ""
    "WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses des Home-"
    "Verzeichnisses `%s'\n"

    When we changed the wrapping code, we got a bug with this string.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"The location and hierarchy of the Evolution contact folders has"
    ...         u" changed since Evolution 1.x.\n\n")
    >>> print export_translation_message(translation_message)
    msgid ""
    "The location and hierarchy of the Evolution contact folders has changed "
    "since Evolution 1.x.\n"
    "\n"
    msgstr ""

    When the wrapping size was exactly gotten past by in the middle of
    escape sequence like \" or \\, it got cut off in there, thus
    creating a broken PO message.  This is the test for bug #46156.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcde word\"1234567890abcdefghij")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcde "
    "word\"1234567890abcd"
    "efghij"
    msgstr ""

    Lets also make sure that the unconditional break is not occurring
    inside a single long word in the middle of the escape sequence
    like \" or \\:
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefghij\\klmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefghij"
    "\\klmno"
    msgstr ""

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefgh\\ijklmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefgh\\"
    "ijklmno"
    msgstr ""

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"1234567890abcdefg\\\\hijklmno")
    >>> print export_translation_message(translation_message, wrap_width=20)
    msgid ""
    "1234567890abcdefg\\"
    "\\hijklmno"
    msgstr ""

    For compatibility with msgcat -w, it also wraps on \\ properly.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = (
    ...     u"\\\\\\\\\\")
    >>> print export_translation_message(translation_message, wrap_width=5)
    msgid ""
    "\\\\"
    "\\\\"
    "\\"
    msgstr ""

    >>> print export_translation_message(translation_message, wrap_width=6)
    msgid ""
    "\\\\\\"
    "\\\\"
    msgstr ""
    '''
    def local_escape(text):
        ret = text.replace(u'\\', u'\\\\')
        ret = ret.replace(ur'"', ur'\"')
        ret = ret.replace(u'\t', u'\\t')
        return ret.replace(u'\n', u'\\n')

    # Quickly get escaped character byte widths using
    #   escaped_length.get(char, 1)
    escaped_length = {
        '\\': 2,
        '\"': 2,
        '\t': 2,
        '\n': 2}

    # What characters to wrap at
    wrap_at = [' ', '\t', '\n', '-', '\\']

    if wrap_width is None:
        raise AssertionError('wrap_width should not be None')
    wrapped_lines = [u'%s%s' % (prefix, u' ""')]
    if not text:
        return wrapped_lines
    if '\n' not in text[:-1]:
        # If there are no new-lines, or it's at the end of string.
        unwrapped_line = u'%s "%s"' % (prefix, local_escape(text))
        if len(unwrapped_line) <= wrap_width:
            return [unwrapped_line]
        del unwrapped_line
    paragraphs = text.split('\n')
    end = len(paragraphs) - 1
    for i, paragraph in enumerate(paragraphs):
        if i == end:
            if not paragraph:
                break
        else:
            paragraph += '\n'

        if len(local_escape(paragraph)) <= wrap_width:
            wrapped_line = [paragraph]
        else:
            line = u''
            escaped_line_len = 0
            new_block = u''
            escaped_new_block_len = 0
            wrapped_line = []
            for char in paragraph:
                escaped_char_len = escaped_length.get(char, 1)
                if (escaped_line_len + escaped_new_block_len
                    + escaped_char_len <= wrap_width):
                    if char in wrap_at:
                        line += u'%s%s' % (new_block, char)
                        escaped_line_len += (escaped_new_block_len
                                             + escaped_char_len)
                        new_block = u''
                        escaped_new_block_len = 0
                    else:
                        new_block += char
                        escaped_new_block_len += escaped_char_len
                else:
                    if escaped_line_len == 0:
                        # Word is too long to fit into single line,
                        # break it carefully, watching not to break
                        # in the middle of the escape
                        line = new_block
                        line_len = len(line)
                        escaped_line_len = escaped_new_block_len
                        while escaped_line_len > wrap_width:
                            escaped_line_len -= (
                                escaped_length.get(line[line_len-1], 1))
                            line_len -= 1
                        line = line[:line_len]
                        new_block = new_block[line_len:]
                        escaped_new_block_len -= escaped_line_len
                    wrapped_line.append(line)
                    line = u''
                    escaped_line_len = 0
                    new_block += char
                    escaped_new_block_len += escaped_char_len
            if line or new_block:
                wrapped_line.append(u'%s%s' % (line, new_block))
        for line in wrapped_line:
            wrapped_lines.append(u'"%s"' % (local_escape(line)))
    return wrapped_lines

def msgid_text_representation(translation_message, wrap_width):
    """Return text representation of the msgids.

    :param translation_message: An ITranslationMessage that will get its
        msgids exported.
    :param wrap_width: The width where the text should be wrapped.
    """
    text = wrap_text(translation_message.msgid, u'msgid', wrap_width)
    if translation_message.msgid_plural is not None:
        text.extend(
            wrap_text(
                translation_message.msgid_plural, u'msgid_plural', wrap_width)
            )
    if translation_message.obsolete:
        text = ['#~ ' + l for l in text]

    return u'\n'.join(text)

def translation_text_representation(translation_message, wrap_width):
    """Return text representation of the translations.

    :param translation_message: An ITranslationMessage that will get its
        translations exported.
    :param wrap_width: The width where the text should be wrapped.
    """
    text = []
    if translation_message.msgid_plural is None:
        # It's a message without plural form.
        if translation_message.translations:
            translation = translation_message.translations[
                TranslationConstants.SINGULAR_FORM]
            text = wrap_text(translation, u'msgstr', wrap_width)
        else:
            text = [u'msgstr ""']
    else:
        # It's a message with plural forms.
        for i, s in enumerate(translation_message.translations):
            text.extend(wrap_text(s, u'msgstr[%s]' % i, wrap_width))
        else:
            # We don't have any translation for it.
            text = [u'msgstr[0] ""', u'msgstr[1] ""']

    if translation_message.obsolete:
        text = ['#~ ' + l for l in text]

    return u'\n'.join(text)

def export_translation_message(translation_message, wrap_width=77):
    r'''Return a text representing translation_message.

    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> export_translation_message(translation_message)
    u'msgid "foo"\nmsgstr "bar"'

    obsolete entries are prefixed with #~ .
    >>> translation_message.obsolete = True
    >>> export_translation_message(translation_message)
    u'#~ msgid "foo"\n#~ msgstr "bar"'

    also, obsolete entries preserve fuzzy strings.
    >>> translation_message.flags = ('fuzzy', )
    >>> export_translation_message(translation_message)
    u'#, fuzzy\n#~ msgid "foo"\n#~ msgstr "bar"'

    plural forms have its own way to represent translations.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo'
    >>> translation_message.msgid_plural = u'foos'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'bar')
    >>> translation_message.addTranslation(
    ...     TranslationConstants.PLURAL_FORM, u'bars')
    >>> translation_message.nplurals = 2
    >>> export_translation_message(translation_message)
    u'msgid "foo"\nmsgid_plural "foos"\nmsgstr[0] "bar"\nmsgstr[1] "bars"'

    backslashes are escaped (doubled) and quotes are backslashed.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'foo"bar\\baz'
    >>> translation_message.addTranslation(
    ...     TranslationConstants.SINGULAR_FORM, u'z')
    >>> export_translation_message(translation_message)
    u'msgid "foo\\"bar\\\\baz"\nmsgstr "z"'

    tabs are backslashed too, with standard C syntax.
    >>> translation_message = TranslationMessage()
    >>> translation_message.msgid = u'\tServer name: %s'
    >>> export_translation_message(translation_message)
    u'msgid "\\tServer name: %s"\nmsgstr ""'

    '''
    return '\n'.join([
        comments_text_representation(translation_message),
        msgid_text_representation(translation_message, wrap_width),
        translation_text_representation(translation_message, wrap_width),
        ]).strip()


class GettextPoExporter:
    """Support class to export Gettext .po files."""
    implements(ITranslationFormatExporter)

    def __init__(self, context=None):
        pass

    @property
    def format(self):
        """See `ITranslationFormatExporter`."""
        return TranslationFileFormat.PO

    @property
    def handlable_formats(self):
        """See `ITranslationFormatExporter`."""
        return [TranslationFileFormat.PO, TranslationFileFormat.XPI]

    def exportTranslationFiles(self, translation_file_list):
        """See `ITranslationFormatExporter`."""
        assert len(translation_file_list) > 0, (
            'Got an empty list of files to export!')

        exported_files = {}
        for translation_file in translation_file_list:
            if translation_file.is_template:
                file_path = '%s/%s.pot' % (
                    os.path.dirname(translation_file.path),
                    translation_file.translation_domain)
            else:
                file_path = '%s/%s-%s.po' % (
                    os.path.dirname(translation_file.path),
                    translation_file.translation_domain,
                    translation_file.language_code)

            # XXX: We should export the Header too.
            #chunks = [unicode(self.header).encode(self.header.charset)]
            chunks = []
            for message in translation_file.messages:
                if message.obsolete and len(message.translations) == 0:
                    # Ignore obsolete messages without translations.
                    continue
                chunks.append(export_translation_message(message))

            exported_file_content = u'\n\n'.join(chunks)

            exported_files[file_path] = exported_file_content

        exported_file = ExportedTranslationFile()
        if len(exported_files) == 1:
            # It's a single file export. Return it directly.
            exported_file.path = file_path
            exported_file.content = StringIO(exported_file_content)
            exported_file.content_type = 'application/x-po'
        else:
            # There are multiple files being exported. We need to generate an
            # archive that include all them.
            exported_file.content = LaunchpadWriteTarFile.files_to_stream(
                exported_files)
            exported_file.content_type = 'application/x-gtar'
            # We cannot give a proper file path for the tarball, that's why we
            # don't set it. We leave that decision to the caller.

        return exported_file

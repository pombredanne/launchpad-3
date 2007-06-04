# Contains code from msgfmt.py (available from python source code),
#     written by Martin v. Loewis <loewis@informatik.hu-berlin.de>
#     changed by Christian 'Tiran' Heimes <ch@comlounge.net>


# XXX: Carlos Perello Marin 2005-04-15: This code will be "componentized"
# soon. https://launchpad.ubuntu.com/malone/bugs/403

import re
import codecs
import logging
import doctest
import unittest

from canonical.launchpad.interfaces import (
    IPOMessage, IPOHeader, IPOParser, EXPORT_DATE_HEADER)
from zope.interface import implements
from zope.app import datetimeutils

# Exceptions and warnings

class POSyntaxError(Exception):
    """ Syntax error in a po file """
    def __init__(self, lno=None, msg=None):
        self.lno = lno
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        if self.lno is None:
            return 'PO file: syntax error on an unknown line'
        else:
            return 'PO file: syntax error on entry at line %d' % self.lno

class POInvalidInputError(Exception):
    """ Syntax error in a po file """
    def __init__(self, lno=None, msg=None):
        self.lno = lno
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        elif self.lno is None:
            return 'PO file: invalid input on unknown line'
        else:
            return 'PO file: invalid input on entry at line %d' % self.lno

class POSyntaxWarning(Warning):
    """ Syntax warning in a po file """
    def __init__(self, lno=0, msg=None):
        self.lno = lno
        self.msg = msg

    def __str__(self):
        if self.msg:
            return self.msg
        elif self.lno is None:
            return 'PO file: syntax warning on unknown line'
        else:
            return 'Po file: syntax warning on entry at line %d' % self.lno


# classes

class POMessage(object):
    implements(IPOMessage)

    def __init__(self, **kw):
        self.check(**kw)
        self.msgid = kw.get('msgid', '')
        self.msgidPlural = kw.get('msgidPlural', '')
        self.msgstr = kw.get('msgstr', '')
        self.commentText = kw.get('commentText', '')
        self.sourceComment = kw.get('sourceComment', '')
        self.fileReferences = kw.get('fileReferences', '').strip()
        self.flags = kw.get('flags', set())
        self.msgstrPlurals = kw.get('msgstrPlurals', [])
        self.obsolete = kw.get('obsolete', False)
        self._lineno = kw.get('_lineno')

    def check(self, **kw):
        if kw.get('msgstrPlurals'):
            if 'header' not in kw or type(kw['header'].nplurals) is not int:
                logging.warning(POSyntaxWarning(
                    msg="File has plural forms, but plural-forms header entry"
                        " is missing or invalid."
                    ))
            if len(kw['msgstrPlurals']) > kw['header'].nplurals:
                logging.warning(POSyntaxWarning(
                    lno=kw.get('_lineno'),
                    msg="Bad number of plural-forms in entry '%s' (line %s)."
                        % (kw['msgid'], str(kw.get('_lineno')))
                    ))

    def is_obsolete(self):
        return self.obsolete

    def __nonzero__(self):
        return bool(self.msgid)

    def flagsText(self, flags=None, withHash=True):
        if flags is None:
            flags = self.flags
        if not flags:
            return ''
        flags = list(flags)
        flags.sort()
        if 'fuzzy' in flags:
            flags.remove('fuzzy')
            flags.insert(0, 'fuzzy')
        if withHash:
            prefix = u'#, '
        else:
            prefix = u''
        return prefix + u', '.join(flags)

    class _fake_wrapper(object):
        width = None
        initial_indent = subsequent_indent = u'"'
        def wrap(self, text):
            return [self.initial_indent + text]

    def __unicode__(self, wrap=77):
        r'''
        Text representation of the message.  Should wrap correctly.
        For some of these examples to work (the ones with plural forms),
        we need a header that looks valid.
        '
        >>> header = POHeader()

        >>> header.nplurals = 2

        (end of initialization)

        >>> unicode(POMessage(msgid="foo", msgstr="bar"))
        u'msgid "foo"\nmsgstr "bar"'

        obsolete entries are prefixed with #~
        >>> unicode(POMessage(msgid="foo", msgstr="bar", flags=("fuzzy",), obsolete=True))
        u'#, fuzzy\n#~ msgid "foo"\n#~ msgstr "bar"'

        plural forms automatically trigger the correct syntax
        >>> unicode(POMessage(header=header, msgid="foo", msgidPlural="foos", msgstrPlurals=["bar", "bars"]))
        u'msgid "foo"\nmsgid_plural "foos"\nmsgstr[0] "bar"\nmsgstr[1] "bars"'

        backslashes are escaped (doubled) and quotes are backslashed
        >>> unicode(POMessage(msgid='foo"bar\\baz', msgstr='z'))
        u'msgid "foo\\"bar\\\\baz"\nmsgstr "z"'

        tabs are backslashed too, with standard C syntax
        >>> unicode(POMessage(msgid="\tServer name: %s", msgstr=""))
        u'msgid "\\tServer name: %s"\nmsgstr ""'

        '''
        return '\n'.join([
            self._comments_representation(),
            self._msgids_representation(wrap),
            self._msgstrs_representation(wrap),
            ]).strip()

    def _comments_representation(self):
        r'''
        Text representation of the comments.
        '

        >>> unicode(POMessage(msgid="foo", msgstr="bar",flags=("fuzzy",)))
        u'#, fuzzy\nmsgid "foo"\nmsgstr "bar"'
        >>> unicode(POMessage(msgid="a", msgstr="b", commentText=" blah\n"))
        u'# blah\nmsgid "a"\nmsgstr "b"'
        >>> unicode(POMessage(msgid="%d foo", msgstr="%d bar", flags=('fuzzy', 'c-format')))
        u'#, fuzzy, c-format\nmsgid "%d foo"\nmsgstr "%d bar"'

        '(this single-quote is here to appease emacs)
        '''
        text = []
        # commentText and sourceComment always end in a newline, so
        # splitting by \n always results in an empty last element
        if self.commentText:
            for line in self.commentText.split('\n')[:-1]:
                text.append(u'#' + line)
        if self.sourceComment and not self.obsolete:
            # If it's an obsolete entry, the source comments are not exported.
            for line in self.sourceComment.split('\n')[:-1]:
                text.append(u'#. ' + line)
        # not so for references - we strip() it
        if self.fileReferences and not self.obsolete:
            # If it's an obsolete entry, the references are not exported.
            for line in self.fileReferences.split('\n'):
                text.append(u'#: ' + line)
        if self.flags:
            text.append(self.flagsText())
        return u'\n'.join(text)

    def _msgids_representation(self, wrap_width):
        text = self._wrap(self.msgid, u'msgid', wrap_width)
        if self.msgidPlural:
            text.extend(
                self._wrap(self.msgidPlural, u'msgid_plural', wrap_width))
        if self.obsolete:
            text = ['#~ ' + l for l in text]
        return u'\n'.join(text)

    def _msgstrs_representation(self, wrap_width):
        text = []
        if self.msgstrPlurals:
            for i, s in enumerate(self.msgstrPlurals):
                text.extend(self._wrap(s, u'msgstr[%s]' % i, wrap_width))
        elif self.msgidPlural:
            # It's a plural form but we don't have any translation for it.
            text = ([u'msgstr[0] ""', u'msgstr[1] ""'])
        else:
            # It's a singular form.
            text = self._wrap(self.msgstr, u'msgstr', wrap_width)
        if self.obsolete:
            text = ['#~ ' + l for l in text]
        return u'\n'.join(text)

    def _wrap(self, text, prefix, wrap_width):
        r'''
        This method does the actual wrapping.

        >>> POMessage(msgid="abcdefghijkl", msgstr="z").__unicode__(20)
        u'msgid "abcdefghijkl"\nmsgstr "z"'
        >>> POMessage(msgid="abcdefghijklmnopqr", msgstr="z").__unicode__(20)
        u'msgid ""\n"abcdefghijklmnopqr"\nmsgstr "z"'
        >>> POMessage(msgid="abcdef hijklm", msgstr="z").__unicode__(20)
        u'msgid ""\n"abcdef hijklm"\nmsgstr "z"'
        >>> POMessage(msgid="abcdefghijklmnopqr st", msgstr="z").__unicode__(20)
        u'msgid ""\n"abcdefghijklmnopqr "\n"st"\nmsgstr "z"'
        >>> POMessage(msgid="abc\ndef", msgstr="z").__unicode__(20)
        u'msgid ""\n"abc\\n"\n"def"\nmsgstr "z"'

        newlines in the text interfere with wrapping
        >>> unicode(POMessage(msgid="abc\ndef", msgstr="z"))
        u'msgid ""\n"abc\\n"\n"def"\nmsgstr "z"'

        but not when it's just a line that ends with a newline char
        >>> unicode(POMessage(msgid="abc\n", msgstr="def\n"))
        u'msgid "abc\\n"\nmsgstr "def\\n"'

        It's time to test the wrapping with the '-' char:
        >>> pomsg = POMessage(
        ...     msgid="WARNING: unsafe enclosing directory permissions on homedir `%s'\n",
        ...     msgstr="WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses des Home-Verzeichnisses `%s'\n"
        ...     )
        >>> print unicode(pomsg)
        msgid "WARNING: unsafe enclosing directory permissions on homedir `%s'\n"
        msgstr ""
        "WARNUNG: Unsichere Zugriffsrechte des umgebenden Verzeichnisses des Home-"
        "Verzeichnisses `%s'\n"

        When we changed the wrapping code, we got a bug with this string.
        >>> pomsg = POMessage(
        ...     msgid="The location and hierarchy of the Evolution contact folders has changed since Evolution 1.x.\n\n",
        ...     msgstr="")
        >>> print unicode(pomsg)
        msgid ""
        "The location and hierarchy of the Evolution contact folders has changed "
        "since Evolution 1.x.\n"
        "\n"
        msgstr ""


        '''
        if wrap_width is None:
            raise AssertionError('wrap_width should not be None')
        wrapped_lines = [u'%s%s' % (prefix, u' ""')]
        if not text:
            return wrapped_lines
        text = text.replace(u'\\', u'\\\\')
        text = text.replace(ur'"', ur'\"')
        text = text.replace(u'\t', u'\\t')
        if (text.endswith('\n') and '\n' not in text[:-1]):
            # If there is only one newline char and it's at the end of the
            # string.
            text = text.replace(u'\n', u'\\n')
        unwrapped_line = u'%s "%s"' % (prefix, text)
        if ('\n' not in unwrapped_line and
            len(unwrapped_line) <= wrap_width):
            return [unwrapped_line]
        del unwrapped_line
        paragraphs = text.split('\n')
        end = len(paragraphs) - 1
        for i, paragraph in enumerate(paragraphs):
            if i == end:
                if not paragraph:
                    break
            else:
                paragraph += u'\\n'
            if len(paragraph) <= wrap_width:
                wrapped_line = [u'%s%s' % (u'"', paragraph)]
            else:
                line = u''
                new_block = u''
                wrapped_line = []
                for char in paragraph:
                    if len(line) + len(new_block) < wrap_width:
                        if char in [' ', '\t', '\n', '-']:
                            line += u'%s%s' % (new_block, char)
                            new_block = u''
                        else:
                            new_block += char
                    else:
                        wrapped_line.append(u'%s%s' % (u'"', line))
                        line = u'%s%s' % (new_block, char)
                        new_block = u''
                if line or new_block:
                    wrapped_line.append(u'%s%s%s' % (u'"', line, new_block))
            for line in wrapped_line[:-1]:
                wrapped_lines.append(u'%s%s' % (line, u'"'))
            wrapped_lines.append(u'%s%s' % (wrapped_line[-1], u'"'))
        return wrapped_lines

class POHeader(dict, POMessage):
    implements(IPOHeader, IPOMessage)

    def __init__(self, **kw):
        dict.__init__(self)

        # the charset is not known til the header has been parsed.
        # Scan for the charset in the same way that gettext does.
        self.charset = 'CHARSET'
        if 'msgstr' in kw:
            match = re.search(r'charset=([^\s]+)', kw['msgstr'])
            if match:
                self.charset = match.group(1)
        if self.charset == 'CHARSET':
            self.charset = 'US-ASCII'

        for attr in ['msgid', 'msgstr', 'commentText', 'sourceComment']:
            if attr in kw:
                if isinstance(kw[attr], str):
                    kw[attr] = unicode(kw[attr], self.charset, 'replace')

        POMessage.__init__(self, **kw)
        self._casefold = {}
        self.header = self
        self.messages = kw.get('messages', [])
        self.nplurals = None
        self.pluralExpr = '0'


    def updateDict(self):
        """Sync the msgstr content with the dict like object that represents
        this object.
        """
        for key in self.keys():
            # Remove any previous dict entry.
            dict.__delitem__(self, key)

        for attr in ('msgidPlural', 'msgstrPlurals', 'fileReferences'):
            if getattr(self, attr):
                logging.warning(POSyntaxWarning(
                    msg='PO file header entry should have no %s' % attr))
                setattr(self, attr, u'')

        for line in self.msgstr.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            try:
                field, value = line.split(':', 1)
            except ValueError:
                logging.warning(POSyntaxWarning(
                    msg='PO file header entry has a bad entry: %s' % line))
                continue
            field, value = field.strip(), value.strip()
            if field.lower() == 'plural-forms':
                try:
                    self.__setitem__(field, value, False)
                except ValueError:
                    raise POInvalidInputError(
                            msg='Malformed plural-forms header entry')
            else:
                self.__setitem__(field, value, False)
        if 'content-type' not in self:
            logging.warning(POSyntaxWarning(
                msg='PO file header entry has no content-type field'))
            self['Content-Type'] = 'text/plain; charset=ASCII'

    def _decode(self, v):
        try:
            v = unicode(v, self.charset)
        except UnicodeError:
            logging.warning(POSyntaxWarning(
                self._lineno,
                'string is not in declared charset %r' % self.charset
                ))
            v = unicode(v, self.charset, 'replace')
        except LookupError:
            raise POInvalidInputError(msg='Unknown charset %r' % self.charset)

        return v

    def get(self, item, default=None):
        v = None
        try:
            v = dict.__getitem__(self, item)
        except KeyError:
            try:
                v = self._casefold[item.lower()]
            except KeyError:
                if default == []:
                    raise KeyError, item
                else:
                    return default
        if type(v) is str:
            v = self._decode(v)
        return v

    def __getitem__(self, item):
        return self.get(item, [])

    def has_key(self, item):
        try:
            self[item]
        except KeyError:
            return False
        else:
            return True

    __contains__ = has_key

    def __setitem__(self, item, value, update_msgstr=True):
        if not self.has_key(item) and self._casefold.has_key(item.lower()):
            for key in self.keys():
                if key.lower() == item.lower():
                    item = key
        oldvalue = self.get(item)
        dict.__setitem__(self, item, value)
        self._casefold[item.lower()] = value

        if item.lower() == 'content-type':
            parts = parse_assignments(self['content-type'], skipfirst=True)
            if 'charset' in parts:
                if parts['charset'] != 'CHARSET':
                    self.charset = parts['charset']
                else:
                    self.charset = 'ASCII'
            # Convert attributes to unicode
            for attr in ('msgid', 'msgstr', 'commentText', 'sourceComment'):
                v = getattr(self, attr)
                if type(v) is str:
                    v = self._decode(v)
                setattr(self, attr, v)

        # Plural forms logic
        elif item.lower() == 'plural-forms':
            parts = parse_assignments(self['plural-forms'])
            if parts.get('nplurals') == 'INTEGER':
                # sure hope it's a template.
                self.nplurals = 2
            else:
                nplurals = parts.get('nplurals')
                try:
                    self.nplurals = int(nplurals)
                except TypeError:
                    # There are some po files with bad headers that have a non
                    # numeric value here and sometimes an empty value. In that
                    # case, set the default value.
                    logging.warning(POSyntaxWarning(
                        self._lineno,
                        "The plural form header has an unknown error. Using"
                        " the default value..."
                        ))
                    self.nplurals = 2
                self.pluralExpr = parts.get('plural', '0')

        # Update msgstr
        if update_msgstr:
            text = []
            printed = set()
            for l in self.msgstr.strip().split('\n'):
                l = l.strip()
                if not l:
                    continue
                try:
                    field, value = l.split(':', 1)
                except ValueError:
                    # The header has an entry without ':' that's an error in
                    # the header, log it and continue with next entry.
                    logging.warning(
                        POSyntaxWarning(self._lineno, 'Invalid header entry.'))
                    continue
                field = field.strip()
                try:
                    value = self[field]
                except KeyError:
                    # The header has an entry with ':' but otherwise
                    # unrecognized: it happens with plural form formulae
                    # split into two lines, yet containing C-style ':' operator
                    # log it and continue with next entry.
                    logging.warning(
                        POSyntaxWarning(self._lineno, 'Invalid header entry.'))
                    continue
                text.append(u'%s: %s' % (field, self[field]))
                printed.add(field)
            for field in self.keys():
                if field not in printed:
                    value = self[field]
                    text.append(u'%s: %s' % (field, self[field]))
            text.append('')
            self.msgstr = u'\n'.join(text)

    def __delitem__(self, item):
        # Update the msgstr entry
        # XXX: CarlosPerelloMarin 20050901 This parser sucks too much!
        text = []
        for l in self.msgstr.strip().split('\n'):
            l = l.strip()
            if not l:
                continue
            try:
                field, value = l.split(':', 1)
            except ValueError:
                # The header has an entry without ':' that's an error in
                # the header, log it and continue with next entry.
                logging.warning(
                    POSyntaxWarning(self._lineno, 'Invalid header entry.'))
                continue
            field = field.strip()
            if field.lower() != item.lower():
                text.append(l)
        text.append('')
        self.msgstr = u'\n'.join(text)

        # And now, the dict part of the object needs to be rebuilt...
        self.updateDict()

    def update(self, other):
        for key in other:
            # not using items() because this way we get decoding
            self[key] = other[key]

    def copy(self):
        cp = POHeader(self)
        cp.updateDict()
        # copy any changes made by user-code
        cp.update(self)
        return cp

    def recode(self, charset):
        "A copy with a different charset"
        cp = self.copy()
        cp.charset = charset
        ct_flags = ['text/plain']
        for o in self['content-type'].split(';')[1:]:
            try:
                name, value = o.split('=')
            except ValueError:
                ct_flags.append(o.strip())
                continue
            name, value = name.strip(), value.strip()
            if name.lower() == 'charset':
                value = charset
            ct_flags.append('%s=%s' % (name, value))
        cp['Content-Type'] = '; '.join(ct_flags)
        return cp

    def __nonzero__(self):
        return bool(self.keys())

    def getPORevisionDate(self):
        """See IPOHeader."""

        date_string = self.get('PO-Revision-Date')
        if date_string is None:
            date = None
            date_string = 'Missing header'
        else:
            try:
                date = datetimeutils.parseDatetimetz(date_string)
            except datetimeutils.DateTimeError:
                # invalid date format
                date = None

        return (date_string, date)

    def getRosettaExportDate(self):
        """See IPOHeader."""

        date_string = self.get(EXPORT_DATE_HEADER, None)
        if date_string is None:
            date = None
        else:
            try:
                date = datetimeutils.parseDatetimetz(date_string)
            except datetimeutils.DateTimeError:
                # invalid date format
                date = None

        return date

    def getPluralFormExpression(self):
        """See IPOHeader."""
        plural = self.get('Plural-Forms')
        if not plural:
            return None
        parts = parse_assignments(plural)
        if parts.has_key("plural"):
            return parts["plural"]
        else:
            return None


class POParser(object):
    implements(IPOParser)

    def __init__(self, translation_factory=POMessage, header_factory=POHeader):
        self.translation_factory = translation_factory
        self.header_factory = header_factory
        self.header = None
        self.messages = []
        self._messageids = {}
        self._pending_chars = ''
        self._pending_unichars = u''
        self._lineno = 0
        self._make_dataholder()
        self._section = None
        self._plural_case = None

    def _convert_chars(self):
        # is there anything to convert?
        if not self._pending_chars:
            return

        # if the PO header hasn't been parsed, then we don't know the
        # encoding yet
        if not self.header:
            return

        decode = codecs.getdecoder(self.header.charset)
        # decode as many characters as we can:
        try:
            newchars, length = decode(self._pending_chars, 'strict')
        except UnicodeDecodeError, exc:
            # XXX: James Henstridge 20060316
            # If the number of unconvertable chars is longer than a
            # multibyte sequence to be, the UnicodeDecodeError indicates
            # a real error, rather than a partial read.
            # I don't know what the longest multibyte sequence in the
            # encodings we need to support, but it shouldn't be more
            # than 10 bytes ...
            if len(self._pending_chars) - exc.start > 10:
                raise POInvalidInputError(self._lineno,
                                          "could not decode input from %s"
                                          % self.header.charset)
            newchars, length = decode(self._pending_chars[:exc.start],
                                      'strict')
        self._pending_unichars += newchars
        self._pending_chars = self._pending_chars[length:]

    def _get_header_line(self):
        if self.header:
            # We know what charset the data is in, as we've already
            # parsed the header.  However, we're going to handle this
            # more efficiently, so we don't want to use _get_header_line
            # except for parsing the header.
            raise AssertionError(
                'using _get_header_line after header is parsed')

        # We don't know what charset the data is in, so we parse it one line
        # at a time until we have the header, and then we'll know how to
        # treat the rest of the data.
        parts = re.split(r'\n|\r\n|\r', self._pending_chars, 1)
        if len(parts) == 1:
            # only one line
            return None
        line, self._pending_chars = parts
        return line

    def write(self, string):
        """Parse string as a PO file fragment."""
        self._pending_chars += string
        if self.header:
            self._convert_chars()
            return

        # Header not parsed yet. Do that first, inefficiently.
        # It ought to be short, so this isn't disastrous.
        line = self._get_header_line()
        while line is not None:
            self.parse_line(line)
            if self.header:
                break
            line = self._get_header_line()

        if line is None:
            # There is nothing left to parse.
            return

        # Parse anything left all in one go.
        lines = re.split(r'\n|\r\n|\r', self._pending_unichars)
        if lines:
            # If we have any lines, the last one should be the empty string,
            # if we have a properly-formed po file with a new line at the
            # end.  So, put the last line into _pending_unichars so the rest
            # of the parser gets what's expected.
            self._pending_unichars = lines[-1]
            lines = lines[:-1]
        for line in lines:
            self.parse_line(line)

    def _make_dataholder(self):
        self._partial_transl = {}
        self._partial_transl['msgid'] = ''
        self._partial_transl['msgidPlural'] = ''
        self._partial_transl['msgstr'] = ''
        self._partial_transl['commentText'] = ''
        self._partial_transl['sourceComment'] = ''
        self._partial_transl['fileReferences'] = ''
        self._partial_transl['flags'] = set()
        self._partial_transl['msgstrPlurals'] = []
        self._partial_transl['obsolete'] = False
        self._partial_transl['_lineno'] = self._lineno

    def append(self):
        if self._partial_transl:
            if self._messageids.has_key(self._partial_transl['msgid']):
                lineno = self._partial_transl['_lineno']
                # XXX: I changed the exception below to use %r
                # because the original %d returned "<unprintable
                # instance object>" in a traceback in bug 2896
                #    -- kiko, 2005-10-06
                raise POInvalidInputError('Po file: duplicate msgid '
                                          'ending on line %r' % lineno)
            try:
                transl = self.translation_factory(header=self.header,
                                                  **self._partial_transl)
            except (POSyntaxError, POInvalidInputError), e:
                if e.lno is None:
                    e.lno = self._partial_transl['_lineno']
                raise
            self.messages.append(transl)
            self._messageids[self._partial_transl['msgid']] = True
        self._partial_transl = None

    def _make_header(self):
        try:
            self.header = self.header_factory(messages=self.messages, 
                                              **self._partial_transl)
            self.header.updateDict()
        except (POSyntaxError, POInvalidInputError), e:
            if e.lno is None:
                e.lno = self._partial_transl['_lineno']
            raise
        if self.messages:
            logging.warning(POSyntaxWarning(self._lineno,
                                          'Header entry is not first entry'))

        # convert buffered input to the encoding specified in the PO header
        self._convert_chars()

    def _parse_quoted_string(self, string):
        r"""Parse a quoted string, interpreting escape sequences.

          >>> parser = POParser()
          >>> parser._parse_quoted_string(u'\"abc\"')
          u'abc'
          >>> parser._parse_quoted_string(u'\"abc\\ndef\"')
          u'abc\ndef'
          >>> parser._parse_quoted_string(u'\"ab\x63\"')
          u'abc'
          >>> parser._parse_quoted_string(u'\"ab\143\"')
          u'abc'

          After the string has been converted to unicode, the backslash
          escaped sequences are still in the encoding that the charset header
          specifies. Such quoted sequences will be converted to unicode by
          this method.

          We don't know the encoding of the escaped characters and cannot be
          just recoded as Unicode so it's a POInvalidInputError
          >>> utf8_string = u'"view \\302\\253${version_title}\\302\\273"'
          >>> parser._parse_quoted_string(utf8_string)
          Traceback (most recent call last):
          ...
          POInvalidInputError: could not decode escaped string: (\302\253)

          Now, we note the original encoding so we get the right Unicode
          string.

          >>> class FakeHeader:
          ...     charset = 'UTF-8'
          >>> parser.header = FakeHeader()
          >>> parser._parse_quoted_string(utf8_string)
          u'view \xab${version_title}\xbb'

          Let's see that we raise a POInvalidInputError exception when we
          have an escaped char that is not valid in the declared encoding
          of the original string:

          >>> iso8859_1_string = u'"foo \\xf9"'
          >>> parser._parse_quoted_string(iso8859_1_string)
          Traceback (most recent call last):
          ...
          POInvalidInputError: could not decode escaped string as UTF-8: (\xf9)

          An error will be raised if the entire string isn't contained in
          quotes properly:

          >>> parser._parse_quoted_string(u'abc')
          Traceback (most recent call last):
            ...
          POSyntaxError: string is not quoted
          >>> parser._parse_quoted_string(u'\"ab')
          Traceback (most recent call last):
            ...
          POSyntaxError: string not terminated
          >>> parser._parse_quoted_string(u'\"ab\"x')
          Traceback (most recent call last):
            ...
          POSyntaxError: extra content found after string: (x)
        """
        if string[0] != '"':
            raise POSyntaxError(self._lineno, "string is not quoted")

        escape_map = {
            'a': '\a',
            'b': '\b',
            'f': '\f',
            'n': '\n',
            'r': '\r',
            't': '\t',
            'v': '\v',
            '"': '"',
            '\'': '\'',
            '\\': '\\',
            }

        # Remove initial quote char
        string = string[1:]
        output = ''
        while string:
            if string[0] == '"':
                # Reached the end of the quoted string.  It's rare, but there
                # may be another quoted string on the same line.  It should be
                # suffixed to what we already have, with any whitespace
                # between the strings removed.
                string = string[1:].lstrip()
                if not string:
                    # End of line, end of string: the normal case
                    break
                if string[0] == '"':
                    # Start of a new string.  We've already swallowed the
                    # closing quote and any intervening whitespace; now
                    # swallow the re-opening quote and go on as if the string
                    # just went on normally
                    string = string[1:]
                    continue

                # if there is any non-string data afterwards, raise an
                # exception
                if string and not string.isspace():
                    raise POSyntaxError(self._lineno,
                        "extra content found after string: (%s)" % string)
                break
            elif string[0] == '\\' and string[1] in escape_map:
                # We got one of the special escaped chars we know about, we
                # unescape them using the mapping table we have.
                output += escape_map[string[1]]
                string = string[2:]
                continue

            escaped_string = ''
            while string[0] == '\\':
                # Let's handle any normal char escaped. This kind of chars are
                # still in the original encoding so we need to extract the
                # whole block of escaped chars to recode them later into
                # Unicode.
                if string[1] == 'x':
                    # hexadecimal escape
                    escaped_string += string[:4]
                    string = string[4:]
                elif string[1].isdigit():
                    # octal escape
                    escaped_string += string[:2]
                    string = string[2:]
                    # up to two more octal digits
                    for i in range(2):
                        if string[0].isdigit():
                            escaped_string += string[0]
                            string = string[1:]
                        else:
                            break
                elif string[1] in escape_map:
                    # It's part of our mapping table, we ignore it here.
                    break
                else:
                    raise POSyntaxError(self._lineno,
                                        "unknown escape sequence %s"
                                        % string[:2])
            if escaped_string:
                # We found some text escaped that should be recoded to
                # Unicode.
                # First, we unescape it.
                unescaped_string = escaped_string.decode('string-escape')

                if self.header is not None:
                    # There is a header, so we know the original encoding for
                    # the given string.
                    try:
                        output += unescaped_string.decode(self.header.charset)
                    except UnicodeDecodeError:
                        raise POInvalidInputError(self._lineno,
                            "could not decode escaped string as %s: (%s)" %
                                (self.header.charset, escaped_string))
                else:
                    # We don't know the original encoding of the imported file
                    # so we cannot get the right values. We store the string
                    # assuming that is a valid ASCII escape sequence.
                    try:
                        output += unescaped_string.decode('ascii')
                    except UnicodeDecodeError:
                        raise POInvalidInputError(self._lineno,
                            "could not decode escaped string: (%s)" %
                                escaped_string)
            else:
                # It's a normal char, we just store it and jump to next one.
                output += string[0]
                string = string[1:]
        else:
            # We finished parsing the string without finding the ending quote
            # char.
            raise POSyntaxError(self._lineno, "string not terminated")

        return output

    def parse_line(self, l):
        self._lineno += 1
        # Skip empty lines
        l = l.strip()

        obsolete = False
        if l[:2] == '#~':
            obsolete = True
            l = l[2:].lstrip()

        if not l:
            return
        # If we get a comment line after a msgstr or a line starting with
        # msgid, this is a new entry
        # XXX: l.startswith('msgid') is needed because not all msgid/msgstr
        # pairs have a leading comment
        if ((l.startswith('#') or l.startswith('msgid')) and
            self._section == 'msgstr'):
            if self._partial_transl is None:
                # first entry - do nothing
                pass
            elif self._partial_transl['msgid']:
                self.append()
            elif not self.header:
                # this is the potfile header
                self._make_header()
            self._make_dataholder()
            self._section = None
        # Record that the message is known obsolete
        if obsolete:
            self._partial_transl['obsolete'] = True

        if l[0] == '#':
            # Record flags
            if l[:2] == '#,':
                new_flags = [flag.strip() for flag in l[2:].split(',')]
                self._partial_transl['flags'].update(new_flags)
                return
            # Record file references
            if l[:2] == '#:':
                self._partial_transl['fileReferences'] += l[2:].strip() + '\n'
                return
            # Record source comments
            if l[:2] == '#.':
                self._partial_transl['sourceComment'] += l[2:].strip() + '\n'
                return
            # Record comments
            self._partial_transl['commentText'] += l[1:] + '\n'
            return
        # Now we are in a msgid section, output previous section
        if l.startswith('msgid_plural'):
            if self._section != 'msgid':
                raise POSyntaxError(self._lineno)
            self._section = 'msgid_plural'
            l = l[12:]
        elif l.startswith('msgid'):
            if self._section and self._section.startswith('msgid'):
                raise POSyntaxError(self._lineno)
            self._section = 'msgid'
            l = l[5:]
            self._plural_case = None
        # Now we are in a msgstr section
        elif l.startswith('msgstr'):
            self._section = 'msgstr'
            l = l[6:]
            # XXX kiko: if l is empty, it means we got an msgstr
            # followed by a newline; that may be critical, but who knows?
            if l and l[0] == '[':
                # plural case
                new_plural_case, l = l[1:].split(']', 1)
                new_plural_case = int(new_plural_case)
                if (self._plural_case is not None) and (
                        new_plural_case != self._plural_case + 1):
                    logging.warning(POSyntaxWarning(self._lineno,
                                                  'bad plural case number'))
                if new_plural_case != self._plural_case:
                    self._partial_transl['msgstrPlurals'].append('')
                    self._plural_case = new_plural_case
                else:
                    logging.warning(POSyntaxWarning(
                        self._lineno, 'msgstr[] but same plural case number'))
            else:
                self._plural_case = None

        l = l.strip()
        if not l:
            logging.warning(POSyntaxWarning(
                self._lineno,
                'line has no content; this is not supported by '
                'some implementations of msgfmt'))
            return

        l = self._parse_quoted_string(l)

        if self._section == 'msgid':
            self._partial_transl['msgid'] += l
        elif self._section == 'msgid_plural':
            self._partial_transl['msgidPlural'] += l
        elif self._section == 'msgstr':
            if self._plural_case is None:
                self._partial_transl['msgstr'] += l
            else:
                self._partial_transl['msgstrPlurals'][-1] += l
        else:
            raise POSyntaxError(self._lineno)

    def finish(self):
        """Indicate that the PO data has come to an end.
        Throws an exception if the parser was in the
        middle of a message."""
        # handle remaining buffered data:
        if self.header:
            if self._pending_chars:
                raise POInvalidInputError(self._lineno,
                                          'could not decode input from %s'
                                          % self.header.charset)
            if self._pending_unichars:
                logging.warning(POSyntaxWarning(
                    self._lineno, 'No newline at end of file'))
                self.parse_line(self._pending_unichars)
        else:
            if self._pending_chars:
                logging.warning(POSyntaxWarning(
                    self._lineno, 'No newline at end of file'))
                self.parse_line(self._pending_chars)

        if self._section and self._section.startswith('msgid'):
            raise POSyntaxError(self._lineno)

        if self._partial_transl and self._partial_transl['msgid']:
            self.append()
        elif self._partial_transl is not None:
            if self._partial_transl and (self._section is None):
                # input ends in a comment -- should this always be an error?
                raise POSyntaxError(self._lineno)
            elif not self.header:
                # header is last entry... in practice this should
                # only happen when the file is empty
                self._make_header()

        if not self.header:
            raise POSyntaxError(msg='No header found in this pofile')


# convenience function to parse "assignment" expressions like
# the plural-form header

def parse_assignments(text, separator=';', assigner='=', skipfirst=False):
    parts = {}
    if skipfirst:
        start=1
    else:
        start=0
    for assignment in text.split(separator)[start:]:
        if not assignment.strip():
            # empty
            continue
        if assigner in assignment:
            name, value = assignment.split(assigner, 1)
        else:
            logging.warning(POSyntaxWarning(
                msg="Found an error in the header content: %s" % text
                ))
            continue

        parts[name.strip()] = value.strip()
    return parts

if __name__ == '__main__':
    runner = unittest.TextTestRunner()
    runner.run(doctest.DocTestSuite())

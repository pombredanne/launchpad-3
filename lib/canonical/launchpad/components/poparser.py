# Contains code from msgfmt.py (available from python source code),
#     written by Martin v. Loewis <loewis@informatik.hu-berlin.de>
#     changed by Christian 'Tiran' Heimes <ch@comlounge.net>


# XXX: Carlos Perello Marin 2005-04-15: This code will be "componentized"
# soon. https://launchpad.ubuntu.com/malone/bugs/403

import sys
import sets
import textwrap
import codecs
import logging
import doctest
import unittest

from canonical.launchpad.interfaces import IPOMessage, IPOHeader, IPOParser
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
        self.flags = kw.get('flags', sets.Set())
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
        POMessage.__init__(self, **kw)
        self._casefold = {}
        self.header = self
        self.charset = kw.get('charset', 'utf8')
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
            self['Content-Type'] = 'text/plain; charset=us-ascii'

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
                    self.charset = 'us-ascii'
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
            printed = sets.Set()
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
                value = self[field]
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
            except (datetimeutils.SyntaxError, datetimeutils.DateError,
                    datetimeutils.DateTimeError, ValueError):
                # invalid date format
                date = None

        return (date_string, date)

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
        self._pending_line = ''
        self._lineno = 0
        self._make_dataholder()
        self._section = None
        self._plural_case = None

    def write(self, string):
        """Parse string as a PO file fragment."""
        string = self._pending_line + string
        lines = string.split('\n')
        for l in lines[:-1]:
            self.parse_line(l)
        self._pending_line = lines[-1]

    def _make_dataholder(self):
        self._partial_transl = {}
        self._partial_transl['msgid'] = ''
        self._partial_transl['msgidPlural'] = ''
        self._partial_transl['msgstr'] = ''
        self._partial_transl['commentText'] = ''
        self._partial_transl['sourceComment'] = ''
        self._partial_transl['fileReferences'] = ''
        self._partial_transl['flags'] = sets.Set()
        self._partial_transl['msgstrPlurals'] = []
        self._partial_transl['obsolete'] = False
        self._partial_transl['_lineno'] = self._lineno

    def append(self):
        if self._partial_transl:
            for message in self.messages:
                if message.msgid == self._partial_transl['msgid']:
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

    def to_unicode(self, text):
        'Convert text to unicode'
        if self.header: # header converts itself to unicode on updateDict()
            try:
                return unicode(text, self.header.charset)
            except UnicodeError:
                logging.warning(POSyntaxWarning(
                    self._lineno,
                    'string is not in declared charset %r' % self.header.charset
                    ))
                return unicode(text, self.header.charset, 'replace')
        else:
            return text

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
            l = self.to_unicode(l)
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

        # Parse a str line
        if not (l[0] == l[-1] == '"'):
            raise POSyntaxError(self._lineno)
        # XXX: not sure if all Python escapes are OK in a PO file...
        # better be tolerant than strict when reading, since
        # we're already quite strict when writing
        try:
            l = l[1:-1].decode('string_escape')
        except ValueError:
            raise POSyntaxError(self._lineno)

        l = self.to_unicode(l)

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
        if self._pending_line:
            logging.warning(POSyntaxWarning(self._lineno,
                                          'No newline at end of file'))
            self.parse_line(self._pending_line)
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
            # XXX kiko: it may be that we need to run a _make_header() here
            # to ensure we have one, but I'm not guessing.
            logging.warning(POSyntaxWarning(self._lineno,
                                            'No header found in this pofile'))


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

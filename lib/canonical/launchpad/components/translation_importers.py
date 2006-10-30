# Copyright 2006 Canonical Ltd.  All rights reserved.

from UserDict import DictMixin
from StringIO import StringIO


class LocalizableFile (DictMixin):
    """Class for reading translatable messages from different files.

    It behaves as an iterator over all the messages in the file.
    """

    def __init__(self):
        self._data = {}

    def __getitem__(self, key):
        return self._data.__getitem__(key)

    def __delitem__(self, key):
        return self._data.__delitem__(key)

    def __setitem__(self, key, value):
        return self._data.__setitem__(key, value)

    def keys(self):
        return self._data.keys()

    def iteritems(self):
        return self._data.iteritems()

    def __iter__(self):
        return self._data.__iter__()

    def __contains__(self, key):
        return self._data.__contains__(key)

    def getLastTranslator(self):
        return None




class MozillaZipFile (LocalizableFile):
    """Class for reading translatable messages from Mozilla XPI/JAR files.

    It behaves as an iterator over all messages in the file, indexed by 
    msgid's.  It handles embedded jar, dtd and properties files.
    """

    def __init__(self, file):
        LocalizableFile.__init__(self)
        self.last_translator = None

        from zipfile import ZipFile, ZipInfo

        zip = ZipFile(file, 'r')
        for file in zip.namelist():
            if file.endswith('.properties'):
                data = zip.read(file)
                pf = PropertyFile(filename=file, file=StringIO(data))
                self._data.update(pf)
            elif file.endswith('.dtd'):
                data = zip.read(file)
                dtdf = DtdFile(filename=file, file=StringIO(data))
                self._data.update(dtdf)
            elif file.endswith('.jar'):
                data = zip.read(file)
                jarf = MozillaZipFile(StringIO(data))
                self._data.update(jarf)
            elif file == 'install.rdf':
                import re
                data = zip.read(file)
                match = re.match('<em:contributor>(.*)</em:contributor>')
                if match:
                    self.last_translator = match.group(1)

    def getLastTranslator(self):
        return self.last_translator



from xml.parsers.xmlproc import dtdparser, xmldtd, utils
class MozillaDtdConsumer (xmldtd.WFCDTD):
    """Mozilla DTD translatable message parser.

    Extracts all entities along with comments and source references.
    """
    def __init__(self, parser, filename, messages):
        self.started = 0
        self.lastcomment = None
        self.messages = messages
        self.filename = filename
        xmldtd.WFCDTD.__init__(self, parser)

    def dtd_start(self):
        self.started = 1

    def dtd_end(self):
        self.started = 0

    def handle_comment(self, contents):
        if not self.started: return
        if contents.strip().startswith('LOCALIZATION NOTE'):
            self.lastcomment = contents

    def new_general_entity(self, name, value):
        if not self.started: return
        if self.messages.has_key(name):
            print >>sys.stderr, "Warning: there is already a message with key '%s'." % name
            self.messages[name]['sourcerefs'].append(self.filename)
            if self.lastcomment:
                self.messages[name]['comments'].append(self.lastcomment)
        else:
            self.messages[name] = { 'sourcerefs' : [ self.filename ],
                                    'content' : value,
                                    'order' : self.started,
                                    'comments' : [ ] }
            if self.lastcomment:
                self.messages[name]['comments'] = [ self.lastcomment]
            self.started += 1

        self.lastcomment = None

class DtdFile (LocalizableFile):
    """Class for reading translatable messages from a .dtd file.

    It behaves as an iterator over messages in the file, indexed by entity
    names from the .dtd file.
    """
    def __init__(self, filename, file):
        self._data = {}

        parser=dtdparser.DTDParser()
        parser.set_error_handler(utils.ErrorCounter())
        dtd = MozillaDtdConsumer(parser, filename, self._data)
        parser.set_dtd_consumer(dtd)
        parser.parse_string(file.read())



class PropertyFile (LocalizableFile):
    """Class for reading translatable messages from a .properties file.

    It behaves as an iterator over messages in the file, indexed by keys
    from the .properties file.
    """

    def __init__(self, filename, file):
        """Constructs a dictionary from a .properties file.

        It expects a file-like object "file".
        "filename" is used for source code references.
        """
        self.filename = filename
        self._data = {}
        data = file.read()

        # .properties files are defined to be unicode-escaped, but
        # also allow direct UTF-8
        udata = data.decode('utf-8')

        count = 0
        lastcomment = 0

        lines = udata.split("\n")
        for line in lines:
            # Ignore empty and comment lines
            if not len(line.strip()) or line[0]=='#' or line[0]=='!':
                continue
            (key, value) = line.split('=', 1)

            # Now, to "normalize" all to the same encoding, we encode to
            # unicode-escape first, and then decode it to unicode
            # XXX: Danilo 2006-08-01: we _might_ get performance
            # improvements if we reimplement this to work directly,
            # though, it will be hard to beat C-based de/encoder
            value = value.encode('unicode_escape').decode('unicode_escape')

            if self._data.has_key(key):
                print >>sys.stderr, "Warning: there is already a message with key '%s'." % name
                self._data[key]['sourcerefs'].append(filename)
                if lastcomment:
                    self._data[key]['comments'].append(lastcomment)
            else:
                count += 1
                self._data[key] = { 'sourcerefs' : [ filename ],
                                    'content' : value,
                                    'order' : count,
                                    'comments' : [] }
                if lastcomment:
                    self._data[key]['comments'] = [ lastcomment]

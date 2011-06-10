# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Unicode support for CSV files.

Adapted from the Python documentation:
http://docs.python.org/lib/csv-examples.html

Modified to work for Python 2.4.
"""

__metaclass__ = type
__all__ = ['UnicodeReader',
           'UnicodeWriter',
           'UnicodeDictReader',
           'UnicodeDictWriter']


import codecs
import cStringIO
import csv


class UTF8Recoder:
    """Iterator that reads a stream and re-encodes to UTF-8.

    A stream of the given encoding is read and then re-encoded to UTF-8
    before being returned.
    """

    def __init__(self, f, encoding):
        self.reader = codecs.getreader(encoding)(f)

    def __iter__(self):
        return self

    def next(self):
        return self.reader.next().encode("utf-8")


class UnicodeCSVReader:
    """A CSV reader that reads encoded files and yields unicode."""

    class DelegateLineNumAccessDescriptor:
        """The Python 2.5 DictReader expects its reader to support access to a
        line_num attribute, therefore to keep UnicodeCSVReader capable of being
        used within a DictReader we provide a line_num attribute which
        delegates to the real reader."""

        def __get__(self, obj, type):
            return obj.reader.line_num

    line_num = DelegateLineNumAccessDescriptor()

    def __init__(self, file_, dialect=csv.excel, encoding="utf-8", **kwds):
        file_ = UTF8Recoder(file_, encoding)
        self.reader = csv.reader(file_, dialect=dialect, **kwds)

    def next(self):
        row = self.reader.next()
        return [unicode(element, "utf-8") for element in row]

    def __iter__(self):
        return self


class UnicodeCSVWriter:
    """A CSV writer that encodes unicode and writes to the file."""

    def __init__(self, file_, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = file_
        self.encoder = codecs.getencoder(encoding)

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and re-encode it into the target encoding
        (data,len_encoded) = self.encoder(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


class UnicodeDictReader(csv.DictReader):
    """A CSV dict reader that reads encoded files and yields unicode."""

    def __init__(self, file_, fieldnames=None, restkey=None, restval=None,
                 dialect="excel", encoding="utf-8", *args, **kwds):
        csv.DictReader.__init__(self, file_, fieldnames, restkey, restval,
                                dialect, *args, **kwds)
        # overwrite the reader with a UnicodeCSVReader
        self.reader = UnicodeCSVReader(file_, dialect, encoding, *args, **kwds)


class UnicodeDictWriter(csv.DictWriter):
    """A CSV dict writer that encodes unicode and writes to the file."""

    def __init__(self, file_, fieldnames, restval="", extrasaction="raise",
                 dialect="excel", encoding="utf-8",
                 *args, **kwds):
        csv.DictWriter.__init__(self, file_, fieldnames, restval,
                                extrasaction, dialect, *args, **kwds)
        # overwrite the writer with a UnicodeCSVWriter
        self.writer = UnicodeCSVWriter(file_, dialect, encoding, *args, **kwds)

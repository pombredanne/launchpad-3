# Copyright 2005 Canonical Ltd. All rights reserved.

"""Sort SQL dumps.

This library provides functions for the script sort_sql.py, which resides in
database/schema/.

There are limitations on accurate parsing; see the Parser class for details.
"""

__metaclass__ = type

import re, sys

class Line:
    """A single logical line in an SQL dump.

    A line may be composed of several physical lines. It has a value, which is
    a hint about how to sort it.

    >>> line = Line("INSERT INTO Foo VALUES (42, 'blah', 'blah');")
    >>> line.value
    42
    >>> line = Line("Blah blah.")
    >>> line.value is None
    True
    """

    def __init__(self, line):
        self.line = line

        ins_re = re.compile('''
            ^INSERT \s+ INTO \s+ .* VALUES \s+ \(.*? (\d+),.*\);
            ''', re.X)
        match = ins_re.match(line)
        if match is not None:
            self.value = int(match.group(1))
        else:
            self.value = None

    def __str__(self):
        return self.line

    def __repr__(self):
        return '(%r, %r)' % (self.value, self.line)

class Parser:
    r"""Parse an SQL dump into logical lines.

    This has the limitation that it assumes that the string ';' on the end of
    a line indicates the end of an SQL statement, which is not strictly true
    for multi-line dump statements.

    >>> p = Parser()
    >>> p.write_line('blah blah blah);')
    >>> p.write_line('')
    >>> p.write_line('blah')
    >>> p.write_line('blah);')
    >>> p.lines
    ['blah blah blah);', '', 'blah\nblah);']

    >>> p = Parser()
    >>> p.write_line("UPDATE foo SET bar='baz';")
    >>> p.write_line("")
    >>> p.write_line("INSERT INTO foo VALUES (1,23);")
    >>> p.write_line("INSERT INTO foo VALUES (2,23);")
    >>> for line in p.lines:
    ...     print repr(line)
    "UPDATE foo SET bar='baz';"
    ''
    'INSERT INTO foo VALUES (1,23);'
    'INSERT INTO foo VALUES (2,23);'

    """

    def __init__(self):
        self.lines = []
        self.state = 'default'

    def write_line(self, line):
        """Give the parser a physical line of dump to parse.

        The line should not have a terminating newline.
        """

        if self.state == 'default':
            if line and not line.endswith(';'):
                self.state = 'continue'

            self.lines.append(line)
        else:
            if line and line.endswith(';'):
                self.state = 'default'

            self.lines[-1] += '\n' + line

def sort_lines(lines):
    """Sort a set of Line objects."""
    lines.sort(lambda x, y: cmp(x.value, y.value))

def print_lines_sorted(file, lines):
    r"""Print a set of Line objects in sorted order to a file-like object.

    Sorting only occurs within blocks of statements.

    >>> class FakeLine:
    ...     def __init__(self, line, value):
    ...         self.line, self.value = line, value
    ...
    ...     def __str__(self):
    ...         return self.line
    ...
    >>> lines = [
    ...     FakeLine('foo', 3),
    ...     FakeLine('bar', 1),
    ...     FakeLine('baz', 2),
    ...     FakeLine('', None),
    ...     FakeLine('quux', 2),
    ...     FakeLine('asdf', 1),
    ...     FakeLine('zxcv', 3),
    ...     ]
    ...
    >>> print_lines_sorted(sys.stdout, lines)
    bar
    baz
    foo
    <BLANKLINE>
    asdf
    quux
    zxcv

    >>> lines = [
    ...     Line("INSERT INTO foo (id, x) VALUES (10, 'data');"),
    ...     Line("INSERT INTO foo (id, x) VALUES (1, 'data\nmore\nmore');"),
    ...     Line("INSERT INTO foo (id, x) VALUES (7, 'data');"),
    ...     Line("INSERT INTO foo (id, x) VALUES (4, 'data');"),
    ...     Line(""),
    ...     Line("INSERT INTO baz (id, x) VALUES (2, 'data');"),
    ...     Line("INSERT INTO baz (id, x) VALUES (1, 'data');"),
    ...     ]
    >>> print_lines_sorted(sys.stdout, lines)
    INSERT INTO foo (id, x) VALUES (1, 'data
    more
    more');
    INSERT INTO foo (id, x) VALUES (4, 'data');
    INSERT INTO foo (id, x) VALUES (7, 'data');
    INSERT INTO foo (id, x) VALUES (10, 'data');
    <BLANKLINE>
    INSERT INTO baz (id, x) VALUES (1, 'data');
    INSERT INTO baz (id, x) VALUES (2, 'data');

    """

    block = []

    for line in lines:
        if str(line) == '':
            if block:
                sort_lines(block)

                for line in block:
                    file.write(str(line) + '\n')

                block = []

            file.write('\n')
        else:
            block.append(line)

    if block:
        sort_lines(block)

        for line in block:
            file.write(str(line) + '\n')


# Copyright 2005 Canonical Ltd. All rights reserved.

"""Sort SQL dumps.

This library provides functions for the script sort_sql.py, which resides in
database/schema/.

There are limitations on accurate parsing; see the Parser class for details.
"""

__metaclass__ = type

class Line:
    """A single logical line in an SQL dump.

    A line may be composed of several physical lines. It has a value, which is
    a hint about how to sort it.

    >>> line = Line("INSERT INTO Foo VALUES (42, 'blah', 'blah')")
    >>> line.value
    42
    >>> line = Line("Blah blah.")
    >>> line.value is None
    True
    """

    def __init__(self, line):
        self.line = line
        self.is_insert = line.startswith('INSERT ')

        if self.is_insert:
            s = 'VALUES ('
            start = line.index(s) + len(s)
            end = start + line[start:].index(',')
            self.value = int(line[start:end])
        else:
            self.value = None

    def __str__(self):
        return self.line

class Parser:
    r"""Parse an SQL dump into logical lines.

    This has the limitation that it assumes that the string ');' on the end of
    a line indicates the end of an SQL statement, which is not strictly true
    for multi-line dump statements.

    >>> p = Parser()
    >>> p.write_line('blah blah blah);')
    >>> p.write_line('')
    >>> p.write_line('blah')
    >>> p.write_line('blah);')
    >>> p.lines
    ['blah blah blah);', '', 'blah\nblah);']
    """

    def __init__(self):
        self.lines = []
        self.state = 'default'

    def write_line(self, line):
        """Give the parser a physical line of dump to parse.

        The line should not have a terminating newline.
        """

        if self.state == 'default':
            if line and not line.endswith(');'):
                self.state = 'continue'

            self.lines.append(line)
        else:
            if line and line.endswith(');'):
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
    ...     FakeLine('quux', 0),
    ...     ]
    ...
    >>> class FakeFile:
    ...     strings = []
    ...
    ...     def write(self, s):
    ...         self.strings.append(s)
    ...
    >>> file = FakeFile()
    >>> print_lines_sorted(file, lines)
    >>> file.strings
    ['bar\n', 'baz\n', 'foo\n', '\n', 'quux\n']
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


# Copyright 2005 Canonical Ltd. All rights reserved.

"""Script to sort SQL dumps."""

__metaclass__ = type

import sys

from canonical.launchpad.scripts.sort_sql import Parser, Line, \
    print_lines_sorted

def main(argv):
    parser = Parser()

    for line in sys.stdin:
        parser.write_line(line[:-1])

    lines = [Line(line) for line in parser.lines]
    print_lines_sorted(sys.stdout, lines)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


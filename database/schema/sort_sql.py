# Copyright 2005 Canonical Ltd. All rights reserved.

"""Script to sort SQL dumps."""

__metaclass__ = type

import sys, os, os.path
sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), os.pardir, os.pardir, 'lib'))

from canonical.launchpad.scripts.sort_sql import Parser, Line, \
    print_lines_sorted

def main(argv):
    parser = Parser()

    if len(argv) > 1:
        inf = open(argv[1])
    else:
        inf = sys.stdin
    for line in inf:
        parser.write_line(line[:-1])

    lines = [Line(line) for line in parser.lines]
    print_lines_sorted(sys.stdout, lines)

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))


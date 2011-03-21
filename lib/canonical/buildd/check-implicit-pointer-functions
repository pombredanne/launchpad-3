#!/usr/bin/env python

#
# Copyright (c) 2004 Hewlett-Packard Development Company, L.P.
#       David Mosberger <davidm@hpl.hp.com>
# Copyright 2010 Canonical Ltd.
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

# Scan standard input for GCC warning messages that are likely to
# source of real 64-bit problems.  In particular, see whether there
# are any implicitly declared functions whose return values are later
# interpreted as pointers.  Those are almost guaranteed to cause
# crashes.
#
import re
import sys

implicit_pattern = re.compile(
    "([^:]*):(\d+):(\d+:)? warning: implicit declaration "
    "of function [`']([^']*)'")
pointer_pattern = re.compile(
    "([^:]*):(\d+):(\d+:)? warning: "
    + "("
    +  "(assignment"
    +  "|initialization"
    +  "|return"
    +  "|passing arg \d+ of `[^']*'"
    +  "|passing arg \d+ of pointer to function"
    +  ") makes pointer from integer without a cast"
    + "|"
    + "cast to pointer from integer of different size)")

def main():
    last_implicit_filename = ""
    last_implicit_linenum = -1
    last_implicit_func = ""

    errlist = ""

    in_line = False
    warn_only = False

    for arg in sys.argv[1:]:
        if arg == '--inline':
            in_line = True
        elif arg == '--warnonly':
            warn_only = True

    rv = 0
    while True:
        line = sys.stdin.readline()
        if in_line:
            sys.stdout.write(line)
            sys.stdout.flush()
        if line == '':
            break
        m = implicit_pattern.match(line)
        if m:
            last_implicit_filename = m.group(1)
            last_implicit_linenum = int(m.group(2))
            last_implicit_func = m.group(4)
        else:
            m = pointer_pattern.match(line)
            if m:
                pointer_filename = m.group(1)
                pointer_linenum = int(m.group(2))
                if (last_implicit_filename == pointer_filename
                    and last_implicit_linenum == pointer_linenum):
                    err = "Function `%s' implicitly converted to pointer at " \
                          "%s:%d" % (last_implicit_func, last_implicit_filename,
                                     last_implicit_linenum)
                    errlist += err+"\n"
                    print err
                    if not warn_only:
                        rv = 3

    if len(errlist):
        if in_line:
            print errlist
            print """

Our automated build log filter detected the problem(s) above that will
likely cause your package to segfault on architectures where the size of
a pointer is greater than the size of an integer, such as ia64 and amd64.

This is often due to a missing function prototype definition.

Since use of implicitly converted pointers is always fatal to the application
on ia64, they are errors.  Please correct them for your next upload.

More information can be found at:
http://wiki.debian.org/ImplicitPointerConversions

    """
    sys.exit(rv)

if __name__ == '__main__':
    main()

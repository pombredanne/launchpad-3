#!/usr/bin/env python2.3

# Ideas for extra features:
#
# * Press a key to split a single run into multiple text files
#   named in sequence.
#
# * Keep tcpwatch running all the time, but tell it to log just sometimes,
#   so you don't have to keep switching browser URLs.

import sys
import os
import tempfile
import StringIO
import textwrap

here = os.path.dirname(os.path.realpath(__file__))
listen_port = 9000
forward_port = 8085

EXIT_SYNTAX_ERROR = 2
EXIT_ERROR = 1
EXIT_OK = 0

def rm_dash_r(top):
    # Delete everything reachable from the directory named in 'top'.
    # CAUTION:  This is dangerous!  For example, if top == '/', it
    # could delete all your disk files.
    for root, dirs, files in os.walk(top, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(top)

def print_usage():
    scriptname = sys.argv[0]
    usage = """
        %(scriptname)s: make a pagetest and write it to the 'pagetests'
        directory.
        Usage: %(scriptname)s ([priority]) [name of test]

        'priority' is either ++, xx or two decimal digits such as 00, 45 or 99.
        When 'priority' is ++, the test's filename will start with '++', and
        so will not be committed to an arch archive.
        The 'priority' of 'xx' means "no priority" and is for tests that both
        have no dependents and do not depend on other tests.

        'name of test' should be a short description of the test, to appear
        in the test's filename.  Quoting the name of the test is optional,
        even if it contains spaces.

        To use, run %(scriptname)s with a suitable priority and filename.
        Ensure that launchpad is running and listening on port 8085.
        Using your browser, go to a URL on port 9000.  Use launchpad.
        When you have finished, press ctrl+c.  The pagetest will be written
        to the pagetests directory.

        See also lib/canonical/launchpad/pagetests/README.txt
        """ % {'scriptname': scriptname}
    usage = textwrap.dedent(usage)
    paras = usage.split('\n\n')
    print
    for para in paras:
        print textwrap.fill(para)
        print

def pathfromhere(path):
    if path.startswith(here):
        return os.path.join('.', path[len(here)+1:])

def main():
    pagetest_directory = os.path.join(
        here, 'lib', 'canonical', 'launchpad', 'pagetests'
        )

    args = sys.argv[1:]
    if not args:
        print_usage()
        return EXIT_SYNTAX_ERROR

    priority = 'xx-'  # The default priority.

    filename = '-'.join(args)

    if len(filename) > 2:
        if filename.startswith('++'):
            priority = '++'
            filename = filename[2:]
        elif filename.startswith('xx'):
            priority = 'xx-'
            filename = filename[2:]
        elif filename[:2].isdigit():
            priority = filename[:2] + '-'
            filename = filename[2:]
    if filename.startswith('-'):
        filename = filename[1:]

    if len(filename) < 2:
        print_usage()
        return EXIT_SYNTAX_ERROR

    # sanitize filename
    L = []
    for char in filename:
        if char == '-' or char.isalnum():
            L.append(char)
        else:
            L.append('_')
    filename = ''.join(L)

    filename = '%s%s.txt' % (priority, filename)
    fq_filename = os.path.join(pagetest_directory, filename)
    if os.path.exists(fq_filename):
        print "file exists:", pathfromhere(fq_filename)
        return EXIT_ERROR
    print "Writing to file '%s'" % pathfromhere(fq_filename)

    print "Starting tcpwatch.  Press ^c when finished."
    print

    # The necessary evil of munging the PYTHONPATH so that we can import
    # zope libraries, launchpad stuff, and tcpwatch.
    sys.path.append(os.path.join(here, 'lib'))
    sys.path.append(os.path.join(here, 'utilities', 'tcpwatch'))
    import tcpwatch
    import zope.app.tests.dochttp as dochttp

    tempdir = tempfile.mkdtemp(prefix='page-test.')
    original_stdout = sys.stdout
    sys.stdout = outputfile = StringIO.StringIO()
    try:
        tcpwatch.main(
            ['-L', '%s:%s' % (listen_port, forward_port), '-r', tempdir, '-s']
            )
        # At this point, tcpwatch waits for a KeyboardInterrupt before
        # continuing.

        # The default dochttp options remove the Accept-Language header from
        # the request; however, we want to keep it. Remove the option that
        # removes the header.
        new_defaults = list(dochttp.default_options)
        position_of_lang_header = new_defaults.index('Accept-Language')
        # Remove the 'Accept-Language' and the '-I' that is in the position
        # that precedes it.
        del new_defaults[position_of_lang_header-1:position_of_lang_header+1]

        # Remove stdout from tcpwatch from the output.
        outputfile.truncate(0)
        dochttp.dochttp(args=[tempdir], default=new_defaults)
        rm_dash_r(tempdir)
    finally:
        sys.stdout = original_stdout
        # Don't delete the tempdir if there was an error.  We may want to
        # forensically examine it.
        ##rm_dash_r(tempdir)

    print  # A blank line to separate tcpwatch output from what follows.

    output = outputfile.getvalue()
    if not output:
        print "Not writing a file because there was no output."
        return EXIT_ERROR
    else:
        # write the output into pagetests
        # We check to see if the file exists at the start of this function.
        # Let's check again now, and gracefully handle the case when the
        # file does already exist.  It would have had to be added while
        # tcpwatch was doing its stuff.
        copycount = 0
        orig_filename = fq_filename
        while os.path.exists(fq_filename):
            print "File exists:", pathfromhere(fq_filename)
            copycount += 1
            fq_filename = orig_filename + '.%s' % copycount
            print "Using file:", pathfromhere(fq_filename)
        print "Writing pagetest to file:", pathfromhere(fq_filename)
        outputfile = file(fq_filename, 'w')
        outputfile.write(output)
        outputfile.close()
        return EXIT_OK

if __name__ == '__main__':
    sys.exit(main())

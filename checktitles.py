
'''Check whether page templates are OK with regards to whether they provide a
title or not. Macros and portlets are excused from providing titles.'''

import os
import sys

templates_location = "lib/canonical/launchpad/templates"

def file_is_macro(path):
    '''Check whether a file is a page template macro.'''

    fh = file(path)

    line = fh.readline()

    fh.close()

    return line.startswith('<metal')

def file_is_portlet(path):
    '''Check whether a template file is a portlet.'''

    return os.path.split(path)[-1].startswith('portlet-')

def file_has_title(path):
    '''Check whether a template file provides a title.'''

    fh = file(path)

    for line in fh:
        if 'metal:fill-slot="title"' in line:
            fh.close()
            return 1

    fh.close()
    return 0

def check_file(path):
    '''Check whether a file is OK with regards to providing a title.'''

    return file_is_macro(path) or file_is_portlet(path) or file_has_title(path)

def find_templates(path):
    '''Find all the page templates in a given directory.'''

    stdout = os.popen("find '%s' -name '*.pt'" % path, 'r')

    return [ line[:-1] for line in stdout.readlines() ]

def check_directory(path):
    '''Check whether all the page templates in a directory are OK with regards
    to providing titles.'''

    for file in find_templates(path):
        if not check_file(file):
            return False

def summarise_directory(path):
    '''Print a summary of the bad files in a directory, or nothing if there
    are no bad files.'''

    bad = [ file for file in find_templates(path) if not check_file(file) ]

    if not bad:
        return True

    bad.sort()

    print
    print "The following page templates are not macros and have no title:"
    print

    for file in bad:
        print file

    return False

if __name__ == '__main__':
    if summarise_directory(templates_location):
        sys.exit(0)
    else:
        sys.exit(1)


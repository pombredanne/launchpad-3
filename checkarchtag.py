# Copyright 2004 Canonical Ltd.  All rights reserved.
"""Check source tree against the policy for using arch-tag.

Run with the argument 'create' to create an allowed-tags.txt file.

Run with the argument 'check' to check the tree against allowed-tags.txt

You can also call the is_tree_good() method to run a check in-process from
Python code.
"""

__metaclass__ = type

import os
import sys
import sets

def get_actual_tags():
    """Returns a mapping of tag->filename for all files in the tree."""
    tagdict = {}
    stdin, out, err = os.popen3("baz inventory -s --ids")
    dataout = out.readlines()
    for line in dataout:
        filename, tag = line.split()
        if tag.startswith('i_'):
            tagdict[tag[2:]] = filename
    return tagdict

def is_tree_good():
    if not os.path.exists('allowed-tags.txt'):
        print "There is no allowed-tags.txt file.  Run with 'create' option."
        return False
    allowed_tags = read_allowed_tags()
    actual_tags = get_actual_tags()
    return check_tags_dicts(allowed_tags, actual_tags)

def check_tags_dicts(allowed_tags, actual_tags):
    allowed_tags_set = sets.Set(allowed_tags.keys())
    actual_tags_set = sets.Set(actual_tags.keys())
    removed_tags = allowed_tags_set - actual_tags_set
    added_tags = actual_tags_set - allowed_tags_set
    changed_tags = sets.Set(
        [tag for tag, value in
            sets.Set(allowed_tags.items()) - sets.Set(actual_tags.items())
        ]) - removed_tags
    print
    print "Total number of files with implicit ids: %s" % len(actual_tags)
    print
    if added_tags:
        print "New tags have been added:"
        for tag in added_tags:
            print tag, actual_tags[tag]
        print "This will prevent merging into rocketfuel."
    if removed_tags:
        print "Tags have been removed:"
        for tag in removed_tags:
            print tag, allowed_tags[tag]
        if not added_tags:
            print "You should re-generate the allowed-tags file."
    if changed_tags:
        print "Tags have been changed:"
        for tag in changed_tags:
            print tag, allowed_tags[tag], '->', actual_tags[tag]
        if not added_tags:
            print "You need to re-generate the allowed-tags file."

    if not added_tags | removed_tags | changed_tags:
        print "There were no changed tags."

    if added_tags or changed_tags:
        return False
    else:
        return True

def read_allowed_tags():
    tagdict = {}
    for line in open('allowed-tags.txt').readlines():
        filename, tag = line.split()
        tagdict[tag] = filename
    return tagdict

def create_allowed_tags():
    """Create a file called allowed-tags.txt containing lines of the form

      filename archtag

    sorted by filename.
    """
    tags = get_actual_tags().items()

    # Schwartz transform to sort on filename.
    L = [(item[1], item) for item in tags]
    L.sort()
    tags = [item for sortkey, item in L]

    allowed_tags_file = open('allowed-tags.txt', 'w')
    for tag, filename in tags:
        print >>allowed_tags_file, '%s %s' % (filename, tag)
    allowed_tags_file.close()
    print "created allowed-tags.txt"

if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) == 1:
        command = args[0].lower()
        if command == 'create':
            create_allowed_tags()
            sys.exit(0)
        elif command == 'check':
            if is_tree_good():
                sys.exit(0)
            else:
                sys.exit(1)
    print "usage: python checkarchtag.py [ create | check ]"
    sys.exit(1)

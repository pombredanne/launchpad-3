#!/usr/bin/env python
# Copyright 2006 Canonical Ltd.  All rights reserved.

"""Helper to convert our schema.xml to a .ini file."""

__metaclass__ = type

from elementtree.ElementTree import ElementTree
from textwrap import dedent

def print_sectiontype(sectiontype):
    name = sectiontype.get('name')
    if name == 'canonical':
        name = 'DEFAULT'
    print '[%s]' % name
    first = True
    for key in sectiontype.findall('key'):
        for description in key.findall('description'):
            if not first:
                print
            description = dedent(description.text).split('\n')
            for line in description:
                if line.strip():
                    print '# %s' % line
        if key.get('default'):
            value = key.get('default')
        else:
            value = ''
        print '%s=%s' % (key.get('name'),value)
        first = False
    print


if __name__ == '__main__':
    tree = ElementTree(file='../lib/canonical/config/schema.xml')
    root = tree.getroot()

    sectiontypes = dict(
            (x.get('name'), x) for x in root.findall('sectiontype')
            )

    print_sectiontype(sectiontypes.pop('canonical'))
    print_sectiontype(sectiontypes.pop('launchpad'))
    
    for sectiontype in sectiontypes.values():
        print_sectiontype(sectiontype)


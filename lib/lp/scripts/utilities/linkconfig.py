# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Script that merge configuration from another directory.

It's used to merge the production configurations hosted in a separate branch
into the location expected by Launchpad.
"""

__metaclass__ = type
__all__ = []


import logging
import optparse
import os


log = logging.getLogger('link-config')


# XXX flacoste 2009/06/12 This code is copied and pasted from
# lazr-js/tools/build.py. Once lazr-js is buildoutified, it should be 
# shared.
def relative_path(from_file, to_file):
    """Return the relative path between from_file and to_file."""
    # Create a list of directories to each file.
    abs_from_path = os.path.split(
        os.path.abspath(from_file))[0].split(os.path.sep)
    abs_to_path = os.path.split(
        os.path.abspath(to_file))[0].split(os.path.sep)
    # Remove all the directories they have in common.
    while (abs_from_path and abs_to_path
           and abs_from_path[0] == abs_to_path[0]):
        del abs_from_path[0]
        del abs_to_path[0]

    # For each directory still in the from_path, we need to go up a level.
    rel_path = [os.path.pardir] * len(abs_from_path)
    rel_path.extend(abs_to_path)
    rel_path.append(os.path.basename(to_file))

    return os.path.join(*rel_path)


def link_configs(src_dir, target_dir):
    """Link all directories and files in src_dir into target_dir."""
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)
        # Only link configuration file or directories.
        if not filename.endswith('.conf') and not os.path.isdir(src_file):
            continue
        target = os.path.join(target_dir, filename)
        link = relative_path(target, src_file)
        if os.path.lexists(target):
            log.info('Removing existing link %s' % target)
            os.remove(target)
        log.info('Linking %s -> %s' % (link, target))
        os.symlink(link, target)



def main():
    """Script entry point.

    Expects two arguments on the command line: src_dir and target_dir.
    """
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    parser = optparse.OptionParser(
        usage="%prog <src_dir> <dst_dir>",
        description=(
            "Merge the src_dir configuration directory into dst_dir."
            ))
    options, args = parser.parse_args()
    if len(args) != 2:
        parser.error('missing arguments')
    src_dir, target_dir = args
    if not os.path.isdir(src_dir):
        parser.error("%s is not a valid directory" % src_dir)
    if not os.path.isdir(target_dir):
        parser.error("%s is not a valid directory" % target_dir)

    link_configs(src_dir, target_dir)

if __name__ == '__main__':
    main()

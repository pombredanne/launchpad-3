#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 98e9e89b-f2ca-4d21-8266-c5e088bc20bf
"""Directory sums.

This module implements a fairly inefficient, but none-the-less reliable,
method of determining whether two directories have identical content
(excluding stat changes).
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import md5


def calculate(path):
    """Calculate the MD5 sums of the contents of a directory.

    A dictionary containing an entry for each file and subdirectory will be
    returned.  File entries will have the hex md5sum of the file as their
    value, directory entries have the value None.
    """
    sums = {}

    for dirpath, dirnames, filenames in os.walk(path):
        subdir = dirpath[len(path):]
        while subdir[:1] == "/":
            subdir = subdir[1:]

        if len(subdir):
            sums[subdir] = None

        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            if os.path.islink(filepath):
                md5sum = "link:" + os.readlink(filepath)
            else:
                f = open(filepath, "r")
                md5sum = md5.new(f.read()).hexdigest()
                f.close()

            sums[os.path.join(subdir, filename)] = md5sum

    return sums

def calculate_from(path, iterable):
    """Calculate the MD5 sums of files returned by a list or iterable.

    The iteratable should return directory and file entries relative
    to path, optionally excluding the root element which will be
    ignored anyway.

    The return value is the same form as calculate().
    """
    sums = {}

    for filename in iterable:
        filepath = os.path.join(path, filename)
        if os.path.isdir(filepath):
            if len(filepath) and filepath != ".":
                sums[filename] = None

        elif os.path.islink(filepath):
            sums[filename] = "link:" + os.readlink(filepath)

        else:
            f = open(filepath, "r")
            md5sum = md5.new(f.read()).hexdigest()
            f.close()

            sums[filename] = md5sum

    return sums

def compare(sums1, sums2):
    """Compare two directory sums.

    This compares two directory sums and returns an integer to indicate
    whether they match or not.

    A return value of zero indicates that they match precisely.

    A negative return value indicates that some of the sums do not match,
    the number indicates how many didn't.

    A positive return value indicates that all the sums matched, but that
    some files were missing, the number indicates how many.  (A fuzzy match).
    """
    bad = 0
    missing = 0

    for filename in sums1.keys():
        if filename not in sums2:
            missing += 1

        elif sums1[filename] != sums2[filename]:
            bad += 1

    for filename in sums2.keys():
        if filename not in sums1:
            missing += 1

    if bad:
        return -bad
    else:
        return missing

def match(sums1, sums2):
    """Return whether two sums match identically."""
    return compare(sum1, sums2) == 0

def diff(sums1, sums2):
    """Compare two directory sums and return how to turn sums1 into sums2.

    This compares two directory sums like compare() does but instead of
    returning a code to indicate whether they match it returns how to turn
    sums1 into sums2.

    The tuple returned is: (changed, new, gone, moved)

    changed is a list of filenames in which the file from sums1 needs
    to be replaced by the file from sums2.

    new is a list of filenames which only exist in sums2, these need
    to be added.

    gone is a list of filenames which only exist in sums1, these need
    to be deleted.

    moved is a list of (file1, file2) for each file that has been moved
    rather than simply deleted.

    You should process gone before new to ensure that directories that
    change into files (and vice-versa) get handled.
    """
    changed = []
    new = []
    gone = []

    for filename in sums1.keys():
        if filename not in sums2:
            gone.append(filename)

        elif sums1[filename] != sums2[filename]:
            if not sums1[filename] or not sums2[filename]:
                gone.append(filename)
                new.append(filename)
            else:
                changed.append(filename)

    for filename in sums2.keys():
        if filename not in sums1:
            new.append(filename)

    moved = []
    for gonefile in list(gone):
        for newfile in list(new):
            if sums1[gonefile] and sums1[gonefile] == sums2[newfile]:
                gone.remove(gonefile)
                new.remove(newfile)
                moved.append((gonefile, newfile))
                break

    changed.sort()
    new.sort()
    gone.sort()
    moved.sort()

    return (changed, new, gone, moved)

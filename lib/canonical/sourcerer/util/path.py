#!/usr/bin/env python
# -*- coding: UTF-8 -*-
# arch-tag: 3e9ad404-ac5f-4e34-a0ef-91ac84ca0d5a
"""Path handling.

This module supplies useful functions for dealing with paths and
extracting useful information out of them.
"""

__copyright__ = "Copyright © 2004 Canonical Software."
__author__    = "Scott James Remnant <scott@canonical.com>"


import os
import re


# Regular expressions make things easy
version_ext = re.compile(r'[_-]v?([0-9][0-9a-z:.+]*'
                         r'(?:[-_](?:pre|rc|alpha|beta|test)[0-9a-z:.+]*)?)',
                         re.IGNORECASE)
patched_ext = re.compile(r'([._+-](orig|old|new|patch|patched)|~)$',
                         re.IGNORECASE)
seq_prefix = re.compile(r'^([0-9]+[a-z]?)[._+-]', re.IGNORECASE)


class FileFormat(object):
    """Known file formats.

    Constants:
      TAR       Tar file
      PATCH     Patch file
    """

    TAR    = "TAR"
    PATCH  = "PATCH"

class Compression(object):
    """Known compressions.

    Constants:
      GZIP      gzip
      BZIP2     bzip2
    """

    GZIP  = "gzip"
    BZIP2 = "bzip2"

class Extensions(object):
    """Extensions that map to file formats and compressions.

    Constants:
      FORMAT    Extensions that suggest a particular file format.
      COMPRESS  Extensions that suggest a particular compression.
      BOTH      Extensions that suggest both.
    """

    FORMAT = {
        ".tar":    FileFormat.TAR,
        ".patch":  FileFormat.PATCH,
        ".dpatch": FileFormat.PATCH,
        ".diff":   FileFormat.PATCH,
        }

    COMPRESS = {
        ".gz":  Compression.GZIP,
        ".bz2": Compression.BZIP2,
        }

    BOTH = {
        ".tgz":  ( FileFormat.TAR, Compression.GZIP ),
        ".tbz":  ( FileFormat.TAR, Compression.BZIP2 ),
        ".tbz2": ( FileFormat.TAR, Compression.BZIP2 ),
        }

class Directories(object):
    """Directory names that suggest formats for their contents.

    Constants:
      FORMAT    Directory names that suggest a particular file format.
    """

    FORMAT = {
        "tarballs": FileFormat.TAR,
        "tarfiles": FileFormat.TAR,
        "patches":  FileFormat.PATCH,
        }


def len_sort(_dict):
    """Return dictionary with keys reverse sorted by length.

    Reverse sorts the dictionary keys by length and for each returns
    a tuple of (key, value).
    """
    _list = [ (len(k), k, v) for k,v in _dict.items() ]
    _list.sort()
    _list.reverse()
    return [ k[1:] for k in _list ]

def split_path(path):
    """Split path into pieces and extract information from it.

    Returns a tuple of (dirname, name, ext, format, compress).
    """
    dirname = os.path.dirname(path)
    name = os.path.basename(path)
    path_ext = ""
    path_format = None
    path_compress = None

    # Check for version-control leaking
    dirname_w = dirname.split("/")
    for ignore in (".arch-ids", "{arch}", "CVS", ".svn"):
        if ignore in dirname_w:
            return (dirname, name, path_ext, path_format, path_compress)

    # Check combined extensions
    for ext, info in len_sort(Extensions.BOTH):
        if name.endswith(ext):
            name = name[:-len(ext)]
            path_ext = ext + path_ext
            (path_format, path_compress) = info
            break

    # Check compression extensions
    if path_compress is None:
        for ext, compress in len_sort(Extensions.COMPRESS):
            if name.endswith(ext):
                name = name[:-len(ext)]
                path_ext = ext + path_ext
                path_compress = compress
                break

    # Check format extensions
    if path_format is None:
        for ext, format in len_sort(Extensions.FORMAT):
            if name.endswith(ext):
                name = name[:-len(ext)]
                path_ext = ext + path_ext
                path_format = format
                break

    # Split the directory up
    dirname_w = path.split("/")
    dirname_w.reverse()

    # Check format directory names
    if path_format is None:
        for subdir in dirname_w:
            if subdir in Directories.FORMAT:
                path_format = Directories.FORMAT[subdir]
                break

    return (dirname, name, path_ext, path_format, path_compress)

def name(path):
    """Return the name prefix extracted from the path."""
    return split_path(path)[1]

def extension(path):
    """Return the extension extracted from the path."""
    return split_path(path)[2]

def format(path):
    """Return the file format extracted from the path."""
    return split_path(path)[3]

def compress(path):
    """Return the compression extracted from the path."""
    return split_path(path)[4]

def generalise_path(path):
    """Generalise the path given.

    The path is returned with information removed from each component
    so the path is more general and can be exactly matched against
    paths generalised in the same matter.

    Information removed includes version information, common patch
    suffixes, extensions, etc.
    """
    new_path = []
    for word in path.split("/"):
        word = name(word)
        word = patched_ext.sub("", word)
        word = version_ext.sub("", word)
        word = seq_prefix.sub("", word)
        new_path.append(word)

    return "/".join(new_path)

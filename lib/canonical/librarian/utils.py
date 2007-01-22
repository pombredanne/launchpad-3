# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['copy_and_close', 'sha1_from_path', 'filechunks']

import sha

MEGABYTE = 1024*1024


def filechunks(file, chunk_size=4*MEGABYTE):
    """Return an iterator which reads chunks of the given file."""
    return iter(lambda: file.read(chunk_size), '')


def copy_and_close(from_file, to_file):
    """Copy from_file to to_file and close both.

    It requires both arguments to be opened file-like objects.
    'filechunks' trick is used reduce the buffers memory demanded
    when handling large files.
    It's suitable to copy contents from ILibraryFileAlias instances to the
    local filesystem.
    Both file_descriptors are closed before return.
    """
    for chunk in filechunks(from_file):
        to_file.write(chunk)
    from_file.close()
    to_file.close()


def sha1_from_path(path):
    """Return the hexdigest SHA1 for the contents of the path."""
    the_file = open(path)
    the_hash = sha.new()

    for chunk in filechunks(the_file):
        the_hash.update(chunk)

    the_file.close()

    return the_hash.hexdigest()

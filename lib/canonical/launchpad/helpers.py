# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

import os
import tarfile
from StringIO import StringIO

from zope.component import getUtility

from canonical.launchpad.interfaces import ILaunchBag, IHasOwner, IGeoIP, \
    IRequestPreferredLanguages

def is_maintainer(hasowner):
    """Return True if the logged in user is an owner of hasowner.

    Return False if he's not an owner.

    The user is an owner if it either matches hasowner.owner directly or is a
    member of the hasowner.owner team.

    Raise TypeError is hasowner does not provide IHasOwner.
    """
    if not IHasOwner.providedBy(hasowner):
        raise TypeError, "hasowner doesn't provide IHasOwner"
    launchbag = getUtility(ILaunchBag)
    if launchbag.user is not None:
        return launchbag.user.inTeam(hasowner.owner)
    else:
        return False


def tar_add_file(tf, name, contents):
    """
    Convenience method for adding a file to a tar file.
    """

    tarinfo = tarfile.TarInfo(name)
    tarinfo.size = len(contents)

    tf.addfile(tarinfo, StringIO(contents))

def tar_add_files(tf, prefix, files):
    """Add a tree of files, represented by a dictionary, to a tar file."""

    # Keys are sorted in order to make test cases easier to write.

    names = files.keys()
    names.sort()

    for name in names:
        if isinstance(files[name], basestring):
            # Looks like a file.

            tar_add_file(tf, prefix + name, files[name])
        else:
            # Should be a directory.

            tarinfo = tarfile.TarInfo(prefix + name)
            tarinfo.type = tarfile.DIRTYPE
            tf.addfile(tarinfo)

            tar_add_files(tf, prefix + name + '/', files[name])

def make_tarfile(files):
    """Return a tar file as string from a dictionary."""

    sio = StringIO()

    tf = tarfile.open('', 'w', sio)

    tar_add_files(tf, '', files)

    tf.close()

    return sio.getvalue()

def join_lines(*lines):
    """Concatenate a list of strings, adding a newline at the end of each."""

    return ''.join([ x + '\n' for x in lines ])

def string_to_tarfile(s):
    """Convert a binary string containing a tar file into a tar file obj."""

    return tarfile.open('', 'r', StringIO(s))


def find_po_directories(tarfile):
    """Find all directories named 'po' in a tarfile."""

    return [
        member.name
        for member in tarfile.getmembers()
        if member.isdir()
        and os.path.basename(member.name.strip("/")) == 'po'
        ]

def examine_tarfile(tf):
    """Find POT and PO files within a tar file object.

    Return a tuple with the list of .pot files and the list of .po files
    found.

    Two methods of finding files are employed:

     1. Directories named 'po' are searched for in the tar file, and if there
        is exactly one non-empty such directory, it is searched for files
        ending in '.pot' and '.po'.

     2. Otherwise, files ending in '.pot' and '.po' are searched for directly.
     """

    # All files in the tarfile.

    names = tf.getnames()

    # Directories named 'po' in the tarfile.

    po_directories = find_po_directories(tf)

    if po_directories:
        # Look for interesting PO directories. (I.e. ones that contain POT or
        # PO files.)

        interesting = []

        for d in po_directories:
            for name in names:
                if name != d and name.startswith(d) and (
                    name.endswith('.pot') or name.endswith('.po')):
                    if d not in interesting:
                        interesting.append(d)

        # If there's exactly one interesting PO directory, get a list of all
        # the interesting files in it. Otherwise, use method 2.

        if len(interesting) == 1:
            directory = interesting[0]
            pot_files, po_files = [], []

            for name in names:
                if name.startswith(directory):
                    if name.endswith('.pot'):
                        pot_files.append(name)
                    elif name.endswith('.po'):
                        po_files.append(name)

            return (tuple(pot_files), tuple(po_files))

    # All files which look interesting.

    pot_files = [name for name in names if name.endswith('.pot')]

    po_files =  [name for name in names if name.endswith('.po')]

    return (tuple(pot_files), tuple(po_files))


def shortest(sequence):
    """Return a list with the shortest items in sequence.

    Return an empty list if the sequence is empty.
    """
    shortest_list = []

    for item in list(sequence):
        new_length = len(item)

        if not shortest_list:
            # First item.
            shortest_list.append(item)
            shortest_length = new_length
        elif new_length == shortest_length:
            # Same length than shortest item found, we append it to the list.
            shortest_list.append(item)
        elif min(new_length, shortest_length) != shortest_length:
            # Shorter than our shortest length found, discard old values.
            shortest_list = [item]
            shortest_length = new_length

    return shortest_list

def getRosettaBestBinaryPackageName(sequence):
    """Return the best binary package name from a list.

    It follows the Rosetta policy:

    We don't need a concrete value from binary package name, we use shortest
    function as a kind of heuristic to choose the shortest binary package
    name that we suppose will be the more descriptive one for our needs with
    PO templates. That's why we get always the first element.
    """
    return shortest(sequence)[0]

def getRosettaBestDomainPath(sequence):
    """Return the best path for a concrete .pot file from a list of paths.

    It follows the Rosetta policy for this path:

    We don't need a concrete value from domain_paths list, we use shortest
    function as a kind of heuristic to choose the shortest path if we have
    more than one, usually, we will have only one element.
    """
    return shortest(sequence)[0]

def getValidNameFromString(invalid_name):
    """Return a valid name based on a string.

    A name in launchpad has a set of restrictions that not all strings follow.
    This function converts any string in another one that follows our name
    restriction rules.

    To know more about all restrictions, please, look at valid_name function
    in the database.
    """
    # All chars should be lower case.
    name = invalid_name.lower()
    # Underscore is not a valid char.
    name = name.replace('_', '-')
    # Spaces is not a valid char for a name.
    name = name.replace(' ', '-')

    return name

def requestCountry(request):
    """Return the Country object from where the request was done.

    If the ipaddress is unknown or the country is not in our database,
    return None.
    """
    ipaddress = request.get('HTTP_X_FORWARDED_FOR')
    if ipaddress is None:
        ipaddress = request.get('REMOTE_ADDR')
    if ipaddress is None:
        return None
    return getUtility(IGeoIP).country_by_addr(ipaddress)

def browserLanguages(request):
    """Return a list of Language objects based on the browser preferences."""
    return IRequestPreferredLanguages(request).getPreferredLanguages()


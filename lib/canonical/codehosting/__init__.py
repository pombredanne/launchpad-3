# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""Launchpad code-hosting system."""

__metaclass__ = type
__all__ = ['branch_id_to_path']


def branch_id_to_path(branch_id):
    """Convert the given branch ID into NN/NN/NN/NN form, where NN is a two
    digit hexadecimal number.

    Some filesystems are not capable of dealing with large numbers of inodes.
    The supermirror, which can potentially have tens of thousands of branches,
    needs the branches split into several directories. The launchpad id is
    used in order to determine the splitting.
    """
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])

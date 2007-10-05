# Copyright 2006 Canonical Ltd.  All rights reserved.

def branchtarget(branchnum):
    """Convert a launchpad id into a directory structure.

    Some filesystems are not capable of dealing with large numbers of
    inodes. The supermirror, which can potentially have tens of thousands
    of branches, needs the branches split into several directories. The
    launchpad id is used in order to determine the splitting.
    """
    if branchnum == None:
        return None
    lp_hex_id = "%08x" % int(branchnum)
    return '%s/%s/%s/%s' % (
           lp_hex_id[:2], lp_hex_id[2:4], lp_hex_id[4:6], lp_hex_id[6:])

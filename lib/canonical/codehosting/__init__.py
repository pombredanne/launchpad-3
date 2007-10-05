# Copyright 2004-2007 Canonical Ltd.  All rights reserved.

"""The Launchpad Code hosting system."""

__metaclass__ = type
__all__ = ['branch_id_to_path']


def branch_id_to_path(branch_id):
    """Convert the given branch ID into NN/NN/NN/NN form, where NN is a two
    digit hexadecimal number.
    """
    h = "%08x" % int(branch_id)
    return '%s/%s/%s/%s' % (h[:2], h[2:4], h[4:6], h[6:])



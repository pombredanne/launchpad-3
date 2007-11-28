# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Validators for files associated with a ProductRelease."""

__metaclass__ = type
__all__ = ['productrelease_file_size_constraint']

from canonical.config import config
from canonical.launchpad.validators import LaunchpadValidationError

def productrelease_file_size_constraint(value):
    """Constraint for a bug attachment's file size.

    The file is not allowed to be empty.
    """
    size = len(value)
    max_size = config.launchpad.max_productrelease_file_size
    if size == 0:
        raise LaunchpadValidationError(u'Cannot upload empty file.')
    elif max_size > 0 and size > max_size:
        raise LaunchpadValidationError(
            u'Cannot upload files larger than %i bytes' % max_size)
    else:
        return True

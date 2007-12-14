# Copyright 2007 Canonical Ltd.  All rights reserved.

"""Validators for files associated with a ProductRelease."""

__metaclass__ = type
__all__ = [
    'productrelease_file_size_constraint',
    'productrelease_signature_size_constraint',
    ]

from canonical.config import config
from canonical.launchpad.validators import LaunchpadValidationError


def file_size_constraint(value, max_size):
    """Check constraints.

    The file cannot be empty and must be <= max_size.
    """
    size = len(value)
    if size == 0:
        raise LaunchpadValidationError(u'Cannot upload empty file.')
    elif max_size > 0 and size > max_size:
        raise LaunchpadValidationError(
            u'Cannot upload files larger than %i bytes' % max_size)
    else:
        return True


def productrelease_file_size_constraint(value):
    """Constraint for a product release file's size."""
    max_size = config.launchpad.max_productrelease_file_size
    return file_size_constraint(value, max_size)


def productrelease_signature_size_constraint(value):
    """Constraint for a product release signature's size."""
    max_size = config.launchpad.max_productrelease_signature_size
    return file_size_constraint(value, max_size)

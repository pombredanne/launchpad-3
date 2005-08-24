# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

"""Validators for bug attachments."""

__metaclass__ = type
__all__ = ['bug_attachment_size_constraint', 'BugAttachmentSizeError']

from zope.schema import ValidationError

from canonical.config import config


class BugAttachmentSizeError(ValidationError):
    """Raised if the file is empty or too big."""

    def doc(self):
        return self.args[0]


def bug_attachment_size_constraint(value):
    """Constraint for a bug attachment's file size.

    The file is not allowed to be empty.
    """
    size = len(value)
    max_size = config.launchpad.max_bug_attachment_size
    if size == 0:
        raise BugAttachmentSizeError(u'Cannot upload empty file.')
    elif max_size > 0 and size > max_size:
        raise BugAttachmentSizeError(
            u'Cannot upload files larger than %i bytes' % max_size)
    else:
        return True


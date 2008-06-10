# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Various utility functions."""

__metaclass__ = type
__all__ = [
    'safe_hasattr',
    ]


missing = object()


def safe_hasattr(ob, name):
    """hasattr() that doesn't hide exceptions."""
    return getattr(ob, name, missing) is not missing


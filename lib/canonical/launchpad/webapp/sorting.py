# Copyright 2006 Canonical Ltd.  All rights reserved.
"""This module contains sorting utility functions."""

__metaclass__ = type
__all__ = ['expand_numbers',
           'sorted_version_numbers',
           'sorted_dotted_numbers']

import re


def expand_numbers(unicode_text, fill_digits=4):
    """Return a copy of the string with numbers zero filled.

    >>> expand_numbers(u'hello world')
    u'hello world'
    >>> expand_numbers(u'0.12.1')
    u'0000.0012.0001'
    >>> expand_numbers(u'0.12.1', 2)
    u'00.12.01'
    >>> expand_numbers(u'branch-2-3.12')
    u'branch-0002-0003.0012'
    
    """
    assert(isinstance(unicode_text, unicode))
    def substitude_filled_numbers(match):
        return match.group(0).zfill(fill_digits)
    return re.sub(u'\d+', substitude_filled_numbers, unicode_text)


def _reversed_number_comparator(lhs_text, rhs_text):
    """Return comparison value reversed for numbers only.

    >>> _reversed_number_comparator('9.3', '2.4')
    -1
    >>> _reversed_number_comparator('world', 'hello')
    1
    >>> _reversed_number_comparator('hello world', 'hello world')
    0
    >>> _reversed_number_comparator('dev', 'development')
    -1
    >>> _reversed_number_comparator('bzr-0.13', 'bzr-0.08')
    -1
    
    """
    for left_char, right_char in zip(lhs_text, rhs_text):
        # if they are both digits, then switch the comparitor
        if left_char.isdigit() and right_char.isdigit():
            result = cmp(right_char, left_char)
            if result:
                return result
        else:
            result = cmp(left_char, right_char)
            if result:
                return result
    # if we get to here one of the strings is a substring of the other
    left_len = len(lhs_text)
    right_len = len(rhs_text)
    if left_len == right_len:
        return 0
    else:
        return (left_len > right_len) and 1 or -1


def _identity(x):
    return x


def sorted_version_numbers(sequence, key=_identity):
    """Return a new sequence where 'newer' versions appear before 'older' ones.

    >>> bzr_versions = [u'0.9', u'0.10', u'0.11']
    >>> for version in sorted_version_numbers(bzr_versions):
    ...   print version
    0.11
    0.10
    0.9
    >>> bzr_versions = [u'bzr-0.9', u'bzr-0.10', u'bzr-0.11']
    >>> for version in sorted_version_numbers(bzr_versions):
    ...   print version
    bzr-0.11
    bzr-0.10
    bzr-0.9

    >>> class series:
    ...   def __init__(self, name):
    ...     self.name = unicode(name)
    >>> bzr_versions = [series('0.9'), series('0.10'), series('0.11'),
    ...                 series('bzr-0.9'), series('bzr-0.10'),
    ...                 series('bzr-0.11'), series('foo')]
    >>> from operator import attrgetter
    >>> for version in sorted_version_numbers(bzr_versions,
    ...                                       key=attrgetter('name')):
    ...   print version.name
    0.11
    0.10
    0.9
    bzr-0.11
    bzr-0.10
    bzr-0.9
    foo
    
    """
    expanded_key = lambda x: expand_numbers(key(x))
    return sorted(sequence, key=expanded_key,
                  cmp=_reversed_number_comparator)


def sorted_dotted_numbers(sequence, key=_identity):
    """Sorts numbers inside strings numerically.

    There are times where numbers are used as part of a string
    normally separated with a delimiter, frequently '.' or '-'.
    The intent of this is to sort '0.10' after '0.9'.

    The function returns a new sorted sequence.

    >>> bzr_versions = [u'0.9', u'0.10', u'0.11']
    >>> for version in sorted_dotted_numbers(bzr_versions):
    ...   print version
    0.9
    0.10
    0.11
    >>> bzr_versions = [u'bzr-0.9', u'bzr-0.10', u'bzr-0.11']
    >>> for version in sorted_dotted_numbers(bzr_versions):
    ...   print version
    bzr-0.9
    bzr-0.10
    bzr-0.11

    >>> class series:
    ...   def __init__(self, name):
    ...     self.name = unicode(name)
    >>> bzr_versions = [series('0.9'), series('0.10'), series('0.11'),
    ...                 series('bzr-0.9'), series('bzr-0.10'),
    ...                 series('bzr-0.11'), series('foo')]
    >>> from operator import attrgetter
    >>> for version in sorted_dotted_numbers(bzr_versions,
    ...                                      key=attrgetter('name')):
    ...   print version.name
    0.9
    0.10
    0.11
    bzr-0.9
    bzr-0.10
    bzr-0.11
    foo
    
    """
    expanded_key = lambda x: expand_numbers(key(x))
    return sorted(sequence, key=expanded_key)

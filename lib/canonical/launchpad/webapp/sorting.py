# Copyright 2006 Canonical Ltd.  All rights reserved.
"""This module will contain sorting utility functions."""

__metaclass__ = type
__all__ = ['expand_numbers',
           'sorted_version_numbers',
           'sorted_dotted_numbers']

# leading _ indicates private to module
def _find_embedded_numbers(unicode_text):
    """Finds the locations of all the numbers in a string.

    Returns a list of tuples containing the start and end position
    of the numbers in the string value.

    >>> _find_embedded_numbers(u'hello')
    []
    >>> _find_embedded_numbers(u'0.10')
    [(0, 1), (2, 4)]
    >>> _find_embedded_numbers(u'dev-1.23.465')
    [(4, 5), (6, 8), (9, 12)]
    >>> _find_embedded_numbers(123)
    Traceback (most recent call last):
    ...
    TypeError: parameter must be a unicode string
    >>> _find_embedded_numbers('123')
    Traceback (most recent call last):
    ...
    TypeError: parameter must be a unicode string
    
    """ # check regex.find
    if not isinstance(unicode_text, unicode):
        raise TypeError("parameter must be a unicode string")
    
    result = []
    start = None
    for pos, char in enumerate(unicode_text):
        if char.isdigit():
            if start is None:
                start = pos
        else:
            if start is not None:
                result.append((start, pos))
                start = None
    if start is not None:
        result.append((start, pos+1))
    return result

def expand_numbers(unicode_text, fill_digits=4):
    """Any numbers in the unicode string are zero filled to fill_digits.

    >>> expand_numbers(u'hello world')
    u'hello world'
    >>> expand_numbers(u'0.12.1')
    u'0000.0012.0001'
    >>> expand_numbers(u'0.12.1', 2)
    u'00.12.01'
    >>> expand_numbers(u'branch-2-3.12')
    u'branch-0002-0003.0012'
    
    """
    positions = _find_embedded_numbers(unicode_text)
    # apply from back to front to keep values accurate
    result = unicode_text
    for start, finish in reversed(positions):
        result = (result[:start] + 
                  result[start:finish].zfill(fill_digits) +
                  result[finish:])

    return result

def _versioned_sort_comparitor(lhs_text, rhs_text):
    """Strings starting with numbers reversed, but normal text alphabetically.

    >>> _versioned_sort_comparitor('0.9', '0.8')
    -1
    >>> _versioned_sort_comparitor('0.9', 'hello')
    -1
    >>> _versioned_sort_comparitor('hello', '0.9')
    1
    >>> _versioned_sort_comparitor('hello', 'world')
    -1

    """
    if (lhs_text and lhs_text[0].isdigit() and
        rhs_text and rhs_text[0].isdigit()):
        return cmp(rhs_text, lhs_text)
    else:
        return cmp(lhs_text, rhs_text)
    

def sorted_version_numbers(sequence, key=None):
    """Have 'later' versions appear before 'older' ones.

    >>> bzr_versions = [u'0.9', u'0.10', u'0.11', u'0.12', u'0.13', u'bzr.dev']
    >>> for version in sorted_version_numbers(bzr_versions):
    ...   print version
    0.13
    0.12
    0.11
    0.10
    0.9
    bzr.dev

    >>> class series:
    ...   def __init__(self, name):
    ...     self.name = unicode(name)
    >>> bzr_versions = [series('0.9'), series('0.10'), series('0.11'),
    ...                 series('0.12'), series('0.13'), series('bzr.dev')]
    >>> from operator import attrgetter
    >>> for version in sorted_version_numbers(bzr_versions,
    ...                                       key=attrgetter('name')):
    ...   print version.name
    0.13
    0.12
    0.11
    0.10
    0.9
    bzr.dev

    
    """
    if key is None:
        expanded_key = expand_numbers
    else:
        expanded_key = lambda x: expand_numbers(key(x))
    return sorted(sequence, key=expanded_key, cmp=_versioned_sort_comparitor)



def sorted_dotted_numbers(sequence, key=None):
    """Sorts numbers inside strings numerically.

    There are times where numbers are used as part of a string
    normally separated with a delimiter, frequently '.' or '-'.
    The intent of this is to sort '0.10' after '0.9'.

    The function returns a new sorted sequence.

    >>> series = [u'trunk', u'dev', u'0.13', u'0.12.2', u'0.12.1', u'0.12',
    ...           u'0.11', u'0.10', u'0.9.1', u'0.9', u'0.8']
    >>> for version in sorted_dotted_numbers(series):
    ...   print version
    0.8
    0.9
    0.9.1
    0.10
    0.11
    0.12
    0.12.1
    0.12.2
    0.13
    dev
    trunk
    >>> series
    [u'trunk', u'dev', u'0.13', u'0.12.2', u'0.12.1', u'0.12', u'0.11',
    u'0.10', u'0.9.1', u'0.9', u'0.8']
    """
    if key is None:
        expanded_key = expand_numbers
    else:
        expanded_key = lambda x: expand_numbers(key(x))
    return sorted(sequence, key=expanded_key)

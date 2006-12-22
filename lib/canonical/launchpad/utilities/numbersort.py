# Copyright 2006 Canonical Ltd.  All rights reserved.

__metaclass__ = type
__all__ = ['expand_numbers',
           'sort_dotted_numbers']

import types

from string import digits

def find_embedded_numbers(value):
    """Finds the locations of all the numbers in a string.

    Returns a list of tuples containing the start and end position
    of the numbers in the string value.

    >>> find_embedded_numbers('hello')
    []
    >>> find_embedded_numbers('0.10')
    [(0, 1), (2, 4)]
    >>> find_embedded_numbers(u'dev-1.23.465')
    [(4, 5), (6, 8), (9, 12)]
    >>> find_embedded_numbers(123)
    Traceback (most recent call last):
    ...
    TypeError: value parameter must be a string or unicode
    
    """
    value_type = type(value)
    if value_type == types.StringType:
        DIGITS = digits
    elif type(value) == types.UnicodeType:
        DIGITS = unicode(digits)
    else:
        raise TypeError, "value parameter must be a string or unicode"

    result = []
    start = None
    for pos, char in enumerate(value):
        if char in DIGITS:
            if start is None:
                start = pos
        else:
            if start is not None:
                result.append((start,pos))
                start = None
    if start is not None:
        result.append((start, pos+1))
    return result

def expand_numbers(value, fill_digits=4):
    """Any numbers in the string are zero filled to fill_digits.

    >>> expand_numbers('hello world')
    'hello world'
    >>> expand_numbers('0.12.1')
    '0000.0012.0001'
    >>> expand_numbers('0.12.1', 2)
    '00.12.01'
    >>> expand_numbers('branch-2-3.12')
    'branch-0002-0003.0012'
    
    """
    positions = find_embedded_numbers(value)
    # apply from back to front to keep values accurate
    positions.reverse()
    for start, finish in positions:
        value = value[:start] + \
                value[start:finish].zfill(fill_digits) + \
                value[finish:]

    return value


def sort_dotted_numbers(sequence):
    """Sorts numbers inside strings numerically.

    There are times where numbers are used as part of a string
    normally separated with a delimiter, frequently '.' or '-'.
    The intent of this is to sort '0.10' after '0.9'.

    >>> series = ['trunk','dev','0.13','0.12.2','0.12.1','0.12','0.11',
    ...           '0.10','0.9.1','0.9','0.8']
    >>> sort_dotted_numbers(series)
    ['0.8', '0.9', '0.9.1', '0.10', '0.11', '0.12', '0.12.1', '0.12.2', '0.13', 'dev', 'trunk']
    """

    decorated_list = [(expand_numbers(item), item) for item in sequence]

    decorated_list.sort()

    return [item[1] for item in decorated_list]

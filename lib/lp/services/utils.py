# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


"""Implementations of the XML-RPC APIs for codehosting."""

__metaclass__ = type
__all__ = [
    'iter_split',
    ]


def iter_split(string, splitter):
    """Iterate over ways to split 'string' in two with 'splitter'.

    If 'string' is empty, then yield nothing. Otherwise, yield tuples like
    ('a/b/c', ''), ('a/b', 'c'), ('a', 'b/c') for a string 'a/b/c' and a
    splitter '/'.

    The tuples are yielded such that the first tuple has everything in the
    first tuple. With each iteration, the first element gets smaller and the
    second gets larger. It stops iterating just before it would have to yield
    ('', 'a/b/c').
    """
    if string == '':
        return
    tokens = string.split(splitter)
    for i in reversed(range(1, len(tokens) + 1)):
        yield splitter.join(tokens[:i]), splitter.join(tokens[i:])

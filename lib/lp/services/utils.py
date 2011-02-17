# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic Python utilities.

Functions, lists and so forth. Nothing here that does system calls or network
stuff.
"""

__metaclass__ = type
__all__ = [
    'AutoDecorate',
    'CachingIterator',
    'decorate_with',
    'docstring_dedent',
    'iter_split',
    'synchronize',
    'text_delta',
    'traceback_info',
    'value_string',
    ]

from itertools import tee
import sys
from textwrap import dedent
from types import FunctionType

from lazr.enum import BaseItem
from twisted.python.util import mergeFunctionMetadata
from zope.security.proxy import isinstance as zope_isinstance


def AutoDecorate(*decorators):
    """Factory to generate metaclasses that automatically apply decorators.

    AutoDecorate is a metaclass factory that can be used to make a class
    implicitly wrap all of its methods with one or more decorators.
    """

    class AutoDecorateMetaClass(type):
        def __new__(cls, class_name, bases, class_dict):
            new_class_dict = {}
            for name, value in class_dict.items():
                if type(value) == FunctionType:
                    for decorator in decorators:
                        value = decorator(value)
                        assert callable(value), (
                            "Decorator %s didn't return a callable."
                            % repr(decorator))
                new_class_dict[name] = value
            return type.__new__(cls, class_name, bases, new_class_dict)

    return AutoDecorateMetaClass


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


def synchronize(source, target, add, remove):
    """Update 'source' to match 'target' using 'add' and 'remove'.

    Changes the container 'source' so that it equals 'target', calling 'add'
    with any object in 'target' not in 'source' and 'remove' with any object
    not in 'target' but in 'source'.
    """
    need_to_add = [obj for obj in target if obj not in source]
    need_to_remove = [obj for obj in source if obj not in target]
    for obj in need_to_add:
        add(obj)
    for obj in need_to_remove:
        remove(obj)


def value_string(item):
    """Return a unicode string representing value.

    This text is special cased for enumerated types.
    """
    if item is None:
        return '(not set)'
    elif zope_isinstance(item, BaseItem):
        return item.title
    else:
        return unicode(item)


def text_delta(instance_delta, delta_names, state_names, interface):
    """Return a textual delta for a Delta object.

    A list of strings is returned.

    Only modified members of the delta will be shown.

    :param instance_delta: The delta to generate a textual representation of.
    :param delta_names: The names of all members to show changes to.
    :param state_names: The names of all members to show only the new state
        of.
    :param interface: The Zope interface that the input delta compared.
    """
    output = []
    indent = ' ' * 4

    # Fields for which we have old and new values.
    for field_name in delta_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        old_item = value_string(delta['old'])
        new_item = value_string(delta['new'])
        output.append("%s%s: %s => %s" % (indent, title, old_item, new_item))
    for field_name in state_names:
        delta = getattr(instance_delta, field_name, None)
        if delta is None:
            continue
        title = interface[field_name].title
        if output:
            output.append('')
        output.append('%s changed to:\n\n%s' % (title, delta))
    return '\n'.join(output)


class CachingIterator:
    """Remember the items extracted from the iterator for the next iteration.

    Some generators and iterators are expensive to calculate, like calculating
    the merge sorted revision graph for a bazaar branch, so you don't want to
    call them too often.  Rearranging the code so it doesn't call the
    expensive iterator can make the code awkward.  This class provides a way
    to have the iterator called once, and the results stored.  The results
    can then be iterated over again, and more values retrieved from the
    iterator if necessary.
    """

    def __init__(self, iterator):
        self.iterator = iterator

    def __iter__(self):
        # Teeing an iterator previously returned by tee won't cause heat
        # death. See tee_copy in itertoolsmodule.c in the Python source.
        self.iterator, iterator = tee(self.iterator)
        return iterator


def decorate_with(context_factory, *args, **kwargs):
    """Create a decorator that runs decorated functions with 'context'."""
    def decorator(function):
        def decorated(*a, **kw):
            with context_factory(*args, **kwargs):
                return function(*a, **kw)
        return mergeFunctionMetadata(function, decorated)
    return decorator


def docstring_dedent(s):
    """Remove leading indentation from a doc string.

    Since the first line doesn't have indentation, split it off, dedent, and
    then reassemble.
    """
    # Make sure there is at least one newline so the split works.
    first, rest = (s+'\n').split('\n', 1)
    return (first + '\n' + dedent(rest)).strip()


def traceback_info(info):
    """Set `__traceback_info__` in the caller's locals.

    This is more aesthetically pleasing that assigning to __traceback_info__,
    but it more importantly avoids spurious lint warnings about unused local
    variables, and helps to avoid typos.
    """
    sys._getframe(1).f_locals["__traceback_info__"] = info

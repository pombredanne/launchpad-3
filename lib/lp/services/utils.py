# Copyright 2009-2011 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Generic Python utilities.

Functions, lists and so forth. Nothing here that does system calls or network
stuff.
"""

__metaclass__ = type
__all__ = [
    'AutoDecorate',
    'base',
    'CachingIterator',
    'compress_hash',
    'decorate_with',
    'docstring_dedent',
    'file_exists',
    'iter_list_chunks',
    'iter_split',
    'obfuscate_email',
    're_email_address',
    'run_capturing_output',
    'synchronize',
    'text_delta',
    'traceback_info',
    'utc_now',
    'value_string',
    ]

from datetime import datetime
from itertools import tee
import os
import re
from StringIO import StringIO
import string
import sys
from textwrap import dedent
from types import FunctionType

from fixtures import (
    Fixture,
    MonkeyPatch,
    )
from lazr.enum import BaseItem
import pytz
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


def base(number, radix):
    """Convert 'number' to an arbitrary base numbering scheme, 'radix'.

    This function is based on work from the Python Cookbook and is under the
    Python license.

    Inverse function to int(str, radix) and long(str, radix)
    """
    if not 2 <= radix <= 62:
        raise ValueError("radix must be between 2 and 62: %s" % (radix,))

    if number < 0:
        raise ValueError("number must be non-negative: %s" % (number,))

    result = []
    addon = result.append
    if number == 0:
        addon('0')

    ABC = string.digits + string.ascii_letters
    while number:
        number, rdigit = divmod(number, radix)
        addon(ABC[rdigit])

    result.reverse()
    return ''.join(result)


def compress_hash(hash_obj):
    """Compress a hash_obj using `base`.

    Given an ``md5`` or ``sha1`` hash object, compress it down to either 22 or
    27 characters in a way that's safe to be used in URLs. Takes the hex of
    the hash and converts it to base 62.
    """
    return base(int(hash_obj.hexdigest(), 16), 62)


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


def iter_list_chunks(a_list, size):
    """Iterate over `a_list` in chunks of size `size`.

    I'm amazed this isn't in itertools (mwhudson).
    """
    for i in range(0, len(a_list), size):
        yield a_list[i:i+size]


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


def file_exists(filename):
    """Does `filename` exist?"""
    return os.access(filename, os.F_OK)


class CapturedOutput(Fixture):
    """A fixture that captures output to stdout and stderr."""

    def __init__(self):
        super(CapturedOutput, self).__init__()
        self.stdout = StringIO()
        self.stderr = StringIO()

    def setUp(self):
        super(CapturedOutput, self).setUp()
        self.useFixture(MonkeyPatch('sys.stdout', self.stdout))
        self.useFixture(MonkeyPatch('sys.stderr', self.stderr))


def run_capturing_output(function, *args, **kwargs):
    """Run ``function`` capturing output to stdout and stderr.

    :param function: A function to run.
    :param args: Arguments passed to the function.
    :param kwargs: Keyword arguments passed to the function.
    :return: A tuple of ``(ret, stdout, stderr)``, where ``ret`` is the value
        returned by ``function``, ``stdout`` is the captured standard output
        and ``stderr`` is the captured stderr.
    """
    with CapturedOutput() as captured:
        ret = function(*args, **kwargs)
    return ret, captured.stdout.getvalue(), captured.stderr.getvalue()


def traceback_info(info):
    """Set `__traceback_info__` in the caller's locals.

    This is more aesthetically pleasing that assigning to __traceback_info__,
    but it more importantly avoids spurious lint warnings about unused local
    variables, and helps to avoid typos.
    """
    sys._getframe(1).f_locals["__traceback_info__"] = info


def utc_now():
    """Return a timezone-aware timestamp for the current time."""
    return datetime.now(tz=pytz.UTC)


# This is a regular expression that matches email address embedded in
# text. It is not RFC 2821 compliant, nor does it need to be. This
# expression strives to identify probable email addresses so that they
# can be obfuscated when viewed by unauthenticated users. See
# http://www.email-unlimited.com/stuff/email_address_validator.htm

# localnames do not have [&?%!@<>,;:`|{}()#*^~ ] in practice
# (regardless of RFC 2821) because they conflict with other systems.
# See https://lists.ubuntu.com
#     /mailman/private/launchpad-reviews/2007-June/006081.html

# This verson of the re is more than 5x faster that the orginal
# version used in ftest/test_tales.testObfuscateEmail.
re_email_address = re.compile(r"""
    \b[a-zA-Z0-9._/="'+-]{1,64}@  # The localname.
    [a-zA-Z][a-zA-Z0-9-]{1,63}    # The hostname.
    \.[a-zA-Z0-9.-]{1,251}\b      # Dot starts one or more domains.
    """, re.VERBOSE)              # ' <- font-lock turd


def obfuscate_email(text_to_obfuscate):
    """Obfuscate an email address.

    The email address is obfuscated as <email address hidden>.

    The pattern used to identify an email address is not 2822. It strives
    to match any possible email address embedded in the text. For example,
    mailto:person@domain.dom and http://person:password@domain.dom both
    match, though the http match is in fact not an email address.
    """
    text = re_email_address.sub(
        r'<email address hidden>', text_to_obfuscate)
    text = text.replace(
        "<<email address hidden>>", "<email address hidden>")
    return text

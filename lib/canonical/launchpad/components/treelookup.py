# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Construct and search simple tree structures.

A tree contains multiple branches. To find something in a tree, one or
more keys are passed in. The second and subsequent keys are used if a
branch off the tree leads to another tree... which breaks the analogy
somewhat, but you get the picture :)

For a given key, each branch in the tree is checked, in order, to see
if it contains that key. If it does, the branch result is looked
at.

If the result is a tree, it is searched in the same way, but using the
next key that was originally passed in.

If the result is any other object, it is returned as the result of the
search.

Two things arise from this:

 * There can be more than one path through the tree to the same
   result.

 * A search of the tree may return a result without consuming all of
   the given keys.

It is also possible to specify a default branch. This is done by
creating a branch with no keys. This must be the last branch in the
tree, because it would not make sense for it to appear in any other
position.
"""

__metaclass__ = type
__all__ = [
    'LookupTree',
    'LookupBranch',
    ]

import string


class LookupTree(tuple):
    """A searchable tree."""

    def __new__(cls, *args):
        """Flatten and/or promote the given arguments into `LookupBranch`s.

        The constructor arguments must be manipulated here, just
        before the instance is actually made, because tuples are
        read-only.

        :param args: `LookupBranch`s, `LookupTree`s, or iterables to
          be attached to this tree. Iterable arguments will be
          promoted to `LookupBranch` by calling it with all the values
          from the iterator as positional arguments.
        """
        branches = []
        for arg in args:
            if isinstance(arg, LookupTree):
                # Extend this tree with the branches from the given
                # tree.
                branches.extend(arg)
            elif isinstance(arg, LookupBranch):
                # Append this branch.
                branches.append(arg)
            else:
                # Promote a tuple or other iterable into a branch. The
                # last value from the iterable is the result of the
                # branch, and all the preceeding values are keys.
                branches.append(cls._create_branch(arg))
        return super(LookupTree, cls).__new__(cls, branches)

    def __init__(self, *branches):
        """See `__new__`.

        As an extra step, the tree is verified by calling `_verify`.
        """
        super(LookupTree, self).__init__()
        self._verify()

    @staticmethod
    def _create_branch(args):
        """Promote arg to a `LookupBranch`.

        :param args: An iterable suitable for passing, expanded, to
          the `LookupBranch` constructor.
        """
        return LookupBranch(*args)

    def _verify(self):
        """Check the validity of the tree.

        Every branch in the tree must be an instance of
        `LookupBranch`. In addition, only one default branch can
        exist, and it must be the last branch.

        :raises TypeError: If the tree is invalid.
        """
        default = False
        for branch in self:
            if not isinstance(branch, LookupBranch):
                raise TypeError('Not a LookupBranch: %r' % (branch,))
            if default:
                raise TypeError('Default branch must be last.')
            default = branch.is_default

    def __call__(self, key, *more):
        """Search this tree.

        Searches in the tree for `key`. If the result is another tree,
        it searches down that tree, using the first value of `more` as
        `key`. Once it gets to a leaf, whether or not all the keys
        (i.e. `key` + `more`) have been consumed, the result is
        returned.

        :raises KeyError: If a result is not found.
        """
        for branch in self:
            if key in branch or branch.is_default:
                if branch.is_leaf:
                    return branch.result
                elif len(more) >= 1:
                    try:
                        return branch.result(*more)
                    except KeyError, ex:
                        raise KeyError((key,) + ex.args)
                else:
                    raise KeyError(key)
        raise KeyError(key)

    def flatten(self):
        """Generate a flat representation of this tree.

        Generate tuples. The last element in the tuple is the
        result. The previous elements are tuples of possible keys.

        This can be useful for generating documentation, because it is
        a compact, flat representation of the tree.
        """
        for branch in self:
            if branch.is_leaf:
                yield branch, branch.result
            else:
                for path in branch.result.flatten():
                    yield (branch,) + path

    @property
    def min_depth(self):
        """The minimum distance to a leaf."""
        return min(len(path) for path in self.flatten()) - 1

    @property
    def max_depth(self):
        """The maximum distance to a leaf."""
        return max(len(path) for path in self.flatten()) - 1

    def describe(self, _level=1):
        """A representation of this tree, formatted for human consumption.

        The representation of each branch in this tree is indented
        corresponding to `_level`, which indicates the position we are
        at within the tree that is being represented.

        When asking each branch for a representation, the next level
        is passed to `describe`, so that sub-trees will be indented
        more.

        This is mainly intended as an aid to development.
        """
        indent = '    ' * _level
        format = indent + '%s'
        return 'tree(\n%s\n%s)' % (
            '\n'.join(format % branch.describe(_level + 1)
                      for branch in self),
            indent)

    def __repr__(self):
        """A machine-readable representation of this tree."""
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join(repr(branch) for branch in self))


class LookupBranch(tuple):
    """A branch point during a lookup, containing keys and a result."""

    def __new__(cls, *args):
        """Split out the keys from the result.

        The last argument specified is the result of this branch, and
        all the other arguments are keys. The keys are stored as tuple
        elements (and are therefore passed to the superclass).
        """
        # Only pass the first len(args)-1 elements to the superclass,
        # because args[-1] is the result of this branch.
        return super(LookupBranch, cls).__new__(cls, args[:-1])

    def __init__(self, *args):
        """See `__new__`."""
        super(LookupBranch, self).__init__()
        # The last arg is the result of this branch.
        self.result = args[-1]

    @property
    def is_leaf(self):
        """Whether or not this is a leaf.

        If the result of this branch is not a `LookupTree`, then this
        is a leaf... as well as a branch... the terminology is a
        little confused :)
        """
        return not isinstance(self.result, LookupTree)

    @property
    def is_default(self):
        """Whether or not this is a default branch.

        If there are no keys for this branch, then this is a default
        branch.
        """
        return len(self) == 0

    def describe(self, _level=1):
        """A representation of this branch.

        If the result of this branch is a `LookupTree` instance, it's
        asked for a representation at a specific `_level`, which
        corresponds to its position in the tree. This allows for
        pretty indentation to aid human comprehension.

        If the result is any other object, `_describe_result` is used.

        Keys are formatted using `_describe_key`.

        This is mainly intended as an aid to development.
        """
        format = 'branch(%s => %%s)'
        if self.is_default:
            format = format % '*'
        else:
            format = format % ', '.join(
                self._describe_key(key) for key in self)
        if self.is_leaf:
            return format % self._describe_result(self.result)
        else:
            return format % self.result.describe(_level)

    _describe_key_chars = set(string.letters + string.digits + '-_+=*')

    def _describe_key(self, key):
        """Return a pretty representation of a simple key.

        If the key, as a string, contains only characters from a small
        selected set, it is returned without quotes. Otherwise, the
        result of `repr` is returned.
        """
        as_string = str(key)
        if self._describe_key_chars.issuperset(as_string):
            return as_string
        else:
            return repr(key)

    def _describe_result(self, result):
        """Return a pretty representation of the branch result.

        By default, return the representation as returned by `repr`.
        """
        return repr(result)

    def __repr__(self):
        """A machine-readable representation of this branch."""
        return '%s(%s)' % (
            self.__class__.__name__,
            ', '.join(repr(item) for item in (self + (self.result,))))

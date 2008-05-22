# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tree lookups."""

__metaclass__ = type
__all__ = [
    'LookupTree',
    'LookupNode',
    ]


class LookupTree:
    """A searchable tree."""

    def __init__(self, *nodes):
        self.nodes = nodes
        self.verify()

    def search(self, key, *more):
        """Search this tree.

        It searches for a match in the tree for `key`. If the match is
        another tree, it searches down that tree, using the first
        value of `more` as `key`. Once it gets to a leaf, whether or
        not all the keys (i.e. `key` + `more`) have been consumed.

        Raises `KeyError` if a result is not found.
        """
        for node in self.nodes:
            if key in node:
                if node.is_leaf:
                    return node.next
                elif len(next) >= 1:
                    try:
                        return node.next.search(*more)
                    except KeyError, ex:
                        raise KeyError((key,) + ex.args)
                else:
                    raise KeyError(key)
        raise KeyError(key)

    @property
    def walker(self):
        """Generates a flat representation of this tree by walking the tree.

        Generates tuples. The last element in the tuple is the
        result. The previous elements are tuples of possible keys.

        This can be useful for generating documentation, because it is
        a compact, flat representation of the tree.
        """
        for node in self.nodes:
            if node.is_leaf:
                yield node.keys, node.next
            else:
                for path in node.next.walker:
                    yield (node.keys,) + path

    @property
    def min_depth(self):
        """The minimum distance to a leaf node."""
        return min(len(path) for path in self.walker) - 1

    @property
    def max_depth(self):
        """The maximum distance to a leaf node."""
        return max(len(path) for path in self.walker) - 1

    def verify(self):
        """Check the validity of the tree."""
        keys = set()
        for node in self.nodes:
            if not isinstance(node, LookupNode):
                raise TypeError('Not a LookupNode: %r' % (node,))
            seen = keys.intersection(node.keys)
            if len(seen) > 0:
                raise TypeError('Key(s) already seen: %r' % (seen,))


class LookupNode:
    """A node point during a lookup, containing keys and a next step."""

    def __init__(self, *args):
        """All but the last argument are keys; the last is the next step."""
        self.keys = args[:-1]
        self.next = args[-1]

    def __contains__(self, key):
        """True if the key is in the keys on this node."""
        return key in self.keys

    @property
    def is_leaf(self):
        """If the next step is not a `LookupTree`, this is a leaf."""
        return not isinstance(self.next, LookupTree)

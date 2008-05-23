# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Tree lookups."""

__metaclass__ = type
__all__ = [
    'LookupTree',
    'LookupNode',
    ]


class LookupTree(tuple):
    """A searchable tree."""

    def __new__(cls, *nodes):
        def conv(node):
            if isinstance(node, LookupNode):
                return node
            else:
                return LookupNode(*node)
        return super(LookupTree, cls).__new__(
            cls, (conv(node) for node in nodes))

    def __init__(self, *nodes):
        self.verify()

    def search(self, key, *more):
        """Search this tree.

        It searches for a match in the tree for `key`. If the match is
        another tree, it searches down that tree, using the first
        value of `more` as `key`. Once it gets to a leaf, whether or
        not all the keys (i.e. `key` + `more`) have been consumed.

        Raises `KeyError` if a result is not found.
        """
        for node in self:
            if key in node or node.is_default:
                if node.is_leaf:
                    return node.next
                elif len(more) >= 1:
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
        for node in self:
            if node.is_leaf:
                yield node, node.next
            else:
                for path in node.next.walker:
                    yield (node,) + path

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
        default = False
        for node in self:
            if default:
                raise TypeError('Default node must be last')
            default = node.is_default
            if not isinstance(node, LookupNode):
                raise TypeError('Not a LookupNode: %r' % (node,))
            seen = keys.intersection(node)
            if len(seen) > 0:
                raise TypeError('Key(s) already seen: %r' % (seen,))

    def __repr__(self, level=1):
        indent = '    ' * level
        format = indent + '%s'
        return 'lookup(\n%s\n%s)' % (
            '\n'.join(format % node.__repr__(level + 1) for node in self),
            indent)


class LookupNode(tuple):
    """A node point during a lookup, containing keys and a next step."""

    def __new__(cls, *args):
        return super(LookupNode, cls).__new__(cls, args[:-1])

    def __init__(self, *args):
        """All but the last argument are keys; the last is the next step."""
        self.next = args[-1]

    @property
    def is_leaf(self):
        """If the next step is not a `LookupTree`, this is a leaf."""
        return not isinstance(self.next, LookupTree)

    @property
    def is_default(self):
        return len(self) == 0

    def __repr__(self, level=1):
        format = 'node(%s => %%s)' % (
            ', '.join(str(node) for node in self))
        if isinstance(self.next, LookupTree):
            return format % self.next.__repr__(level)
        else:
            return format % repr(self.next)

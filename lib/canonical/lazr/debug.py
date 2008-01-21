# Copyright 2008 Canonical Ltd.  All rights reserved.

"""Module docstring goes here."""

__metaclass__ = type
__all__ = [
    "debug_proxy"
    "typename"
    ]


from cStringIO import StringIO
import zope.proxy

from zope.security.checker import getChecker, Checker, CheckerPublic, Proxy


def typename(obj):
    """Return the typename of an object."""
    t = type(obj)
    if t.__module__ == '__builtin__':
        return t.__name__
    else:
        return "%s.%s" % (t.__module__, t.__name__)


def default_proxy_formatter(proxy):
    """Formatter that simply returns the proxy's type name"""
    return typename(proxy)


def get_permission_mapping(checker):
    """Return a list of permission, names protected by a checker.

    Permission used to check for attribute setting have (set) appended.
    """
    permission_to_names = {}
    for name, permission in checker.get_permissions.items():
        if permission is CheckerPublic:
            permission = 'public'
        permission_to_names.setdefault(permission, []).append(name)
    for name, permission in checker.set_permissions.items():
        if permission is CheckerPublic:
            permission = 'public'
        set_permission = "%s (set)" % permission
        permission_to_names.setdefault(set_permission, []).append(name)
    return sorted(permission_to_names.items())


def security_proxy_formatter(proxy):
    """Also includes information about the checker used by the proxy."""
    checker = getChecker(proxy)
    output = ["%s (using %s)" % (typename(proxy), typename(checker))]
    if type(checker) is Checker:
        for permission, names in get_permission_mapping(checker):
            output.append('%s: %s' % (permission, ", ".join(sorted(names))))
    return "\n    ".join(output)


proxy_formatters= {Proxy: security_proxy_formatter}


def debug_proxy(obj):
    """Return informative text about the proxies wrapping obj.

    Usually used like print debug_proxy(obj).
    """
    if not zope.proxy.isProxy(obj):
        return "%r doesn't have any proxies." % obj
    buf = StringIO()
    for proxy in zope.proxy.ProxyIterator(obj):
        if not zope.proxy.isProxy(proxy):
            break
        printer = proxy_formatters.get(type(proxy), default_proxy_formatter)
        print >>buf, printer(proxy)
    return buf.getvalue()


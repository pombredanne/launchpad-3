# Copyright (c) 2006 Canonical Ltd.
# Author: David Allouche <david@allouche.net>

"""Experimental mock object utilities."""

__metaclass__ = type

__all__ = ['MockDecorator', 'StubDecorator']


def has_method(obj, name):
    try:
        unused = getattr(obj, name)
    except AttributeError:
        return False
    else:
        return True    


def checkOverride(obj, name):
    assert has_method(obj, name), (
        "Tried to override undefined name: %r" % (name,))


def checkDefine(obj, name):
    assert not has_method(obj, name), (
        "Tried to define already defined name: %r" % (name,))


class MockDecorator:
    """Mocking individual methods of an existing object and monitor calls.

    A MockDecorator is used to decorate an existing object with the `override`
    and `define` methods. The return values of the mock methods are defined by
    calling the `setReturnValues` method. After the test is complete, the
    `calls` instance variable, and the `checkCall` and `checkCallCount`
    methods, can be used to check the order and parameters of calls to mock
    methods.

    :ivar calls: Calls to mock methods. List of of tuples (name, args, kwargs),
        where name is a method name, args is the tuple of positional arguments
        and kwargs is the dictionnary of keyword arguments.
    """

    def __init__(self):
        self._return_values = {}
        self.calls = []
        self._method_names = set()

    def override(self, obj, names):
        """Install mock methods on an object.

        Each name must be specified exactly once and must match an existing
        attribute in `obj`.

        :param obj: object to decorate with mock methods
        :param names: names of methods to override, as an iterable of strings.
        """
        assert not isinstance(names, basestring)
        for name in names:
            checkOverride(obj, name)
            self._installMockMethod(obj, name)

    def define(self, obj, names):
        """Like override, but fails if the attribute is defined.

        While `override` is meant for use on 'real' objects, and fails when
        using a name that does not match an existing attribute, `define` is
        meant for populating stub objects, and fails when the name matches an
        existing attribute.
        """
        assert not isinstance(names, basestring)
        for name in names:
            checkDefine(obj, name)
            self._installMockMethod(obj, name)

    def _installMockMethod(self, obj, name):
        method = self._makeMockMethod(obj, name)
        assert name not in self._method_names, (
            "Already mock method: %r" % (name,))
        setattr(obj, name, method)
        self._method_names.add(name)

    def _makeMockMethod(self, obj, name):
        def mockMethod(*args, **kwargs):
            self.calls.append((name, args, kwargs))
            if name not in self._return_values:
                return None
            assert len(self._return_values[name]) > 0, (
                'no further return value for %s in %r' % (name, obj))
            return self._return_values[name].pop(0)
        return mockMethod

    def setReturnValues(self, return_values):
        """Specify the return values for mock methods.

        Fail if any provided method name has not has been previously set with
        the `override` or `define` methods. Must be called at most once for
        each mock method name.

        If a mock method has no specified return value, it will return None.

        :param return_values: Return values for mocked methods. Dictionnary
            whose keys are mock method name and whose values are sequence of
            objects returned by the successive calls of this method.
        """
        for name, values in return_values.iteritems():
            assert name not in self._return_values, (
                "already specified return values for %r" % (name,))
            assert name in self._method_names, (
                "specified return values for a not mock method name: %r"
                % (name,))
            self._return_values[name] = values

    def checkCall(self, tester, index, name, *args, **kwargs):
        """Check the arguments of a specific method call by sequence.

        :param tester: unittest.TestCase instance to use for the check
        :param index: sequence index of the call to check
        :param name: expected method name
        """
        tester.assertTrue(name in self._method_names,
            "not name of mock method, cannot check call: %r" % (name,))
        tester.assertEqual(self.calls[index], (name, args, kwargs))

    def checkCallCount(self, tester, count):
        """Check that exactly `count` calls to mock methods were recorded.

        That should typically be used after checking the individual calls. If
        more than `count` mock method calls were recorded, the extraneous calls
        are reported in the failure message.
        """
        tester.assertFalse(len(self.calls) < count,
            "fewer mock methods calls than expected")
        tester.assertFalse(len(self.calls) > count,
            "extraneous mock methods calls: %r" % (self.calls[count:],))


class StubDecorator:
    """Stub individual methods of an existing object.

    A MockDecorator is used to decorate an existing object with the 'override'
    and `define` methods.
    """

    def override(self, obj, name_values):
        """Install stub methods on an object in place of existing methods."""
        for name, return_value in name_values.items():
            checkOverride(obj, name)
            self._installStubMethod(obj, name, return_value)

    def define(self, obj, name_values):
        """Install stub methods on an object without clobbering."""
        for name, return_value in name_values.items():
            checkDefine(obj, name)
            self._installStubMethod(obj, name, return_value)

    def _installStubMethod(self, obj, name, return_value):
        method = self._makeStubMethod(return_value)
        setattr(obj, name, method)

    def _makeStubMethod(self, return_value):
        def stubMethod(*args, **kwargs):
            return return_value
        return stubMethod

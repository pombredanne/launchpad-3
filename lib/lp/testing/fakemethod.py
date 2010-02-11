# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

__metaclass__ = type
__all__ = [
    'FakeMethod',
    ]


class FakeMethod:
    """Catch any function or method call, and record the fact.

    Use this for easy stubbing.  The call operator can return a fixed
    value, or raise a fixed exception object.

    This is useful when unit-testing code that does things you don't
    want to integration-test, e.g. because it wants to talk to remote
    systems.

    >>> class RealActualClass:
    ...     "A class that's hard to test."
    ...     def impossibleMethod(self, argument, more=None):
    ...         do_something_you_cant_test(argument, more)
    ...         return 99
    ...     def testableMethod(self, argument):
    ...         print argument
    ...     def realActualMethod(self):
    ...         outcome = impossibleMethod(1, more=2)
    ...         self.testableMethod("This part does work.")
    ...         print outcome

    >>> real_actual_object = RealActualClass()

You want to unit-test realActualMethod, but it calls impossibleMethod
which you want to bypass for this test.  Just replace impossibleMethod
with a FakeMethod.

    >>> real_actual_object.impossibleMethod = FakeMethod(result=66)

Initially, the fake method has not been called.

    >>> print real_actual_object.impossibleMethod.call_count
    0

Now you can test realActualMethod.  It works fine, except instead of
calling impossibleMethod, it got its result from your fake method.

    >>> real_actual_object.realActualMethod(8, more=9)
    This part does work.
    66

The fake method has recorded the call.

    >>> print real_actual_object.impossibleMethod.call_count
    1

You can also make a FakeMethod raise an exception instead of returning
a value.

    >>> ouch = AssertionError("Ouch!")
    >>> real_actual_object.impossibleMethod = FakeMethod(failure=ouch)
    >>> real_actual_object.testableMethod(7)
    Traceback:
    """

    # How many times has this fake method been called?
    call_count = 0

    def __init__(self, result=None, failure=None):
        """Set up a fake function or method.

        :param result: Value to return.
        :param failure: Exception to raise.
        """
        self.result = result
        self.failure = failure

    def __call__(self, *args, **kwargs):
        """Catch an invocation to the method.  Increment `call_count`.

        Accepts any and all parameters.  Raises the failure passed to
        the constructor, if any; otherwise, returns the result value
        passed to the constructor.
        """
        self.call_count += 1

        if self.failure is None:
            return self.result
        else:
            raise self.failure

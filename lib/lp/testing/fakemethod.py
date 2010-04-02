# Copyright 2009, 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

# pylint: disable-msg=E0702


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
            # pylint thinks this raises None, which is clearly not
            # possible.  That's why this test disables pylint message
            # E0702.
            raise self.failure

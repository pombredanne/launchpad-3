# Copyright 2004-2005 Canonical Ltd.  All rights reserved.

__metaclass__ = type

class SystemError:
    """Default exception error view

    Returns a 500 response instead of 200
    """

    def __call__(self, *args, **kw):
        self.request.response.setStatus(500)
        return self.index(*args, **kw)


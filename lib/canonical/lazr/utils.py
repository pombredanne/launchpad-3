# Copyright 2008 Canonical Ltd.  All rights reserved.

# Re-import code from lazr.restful until it can be refactored into a
# utility module.

# pylint: disable-msg=W0401
try:
    from lazr.restful.utils import *
    from lazr.restful.utils import __all__ as _utils_all
    __all__ = []
    __all__.extend(_utils_all)
except ImportError:
    pass

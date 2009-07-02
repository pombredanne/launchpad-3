# Copyright 2008-2009 Canonical Ltd.  All rights reserved.

# Re-import code from lazr.restful until it can be refactored into a
# utility module.
__all__ = []
import lazr.restful.testing.layers
__all__.extend(lazr.restful.testing.layers.__all__)
from lazr.restful.testing.layers import *

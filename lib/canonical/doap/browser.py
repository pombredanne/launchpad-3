#
# Copyright 2004 Canonical Ltd
#
# arch-tag: 4863ce15-110a-466d-a1fc-54fa8b17d360
#
class DOAPApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


#
# A View Class for Product
# This has moved to launchpad.browser(product.py)

#
# Copyright 2004 Canonical Ltd
#
class DOAPApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request


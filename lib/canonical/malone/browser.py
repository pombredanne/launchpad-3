# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

class MaloneApplicationView(object):
    def __init__(self, context, request):
        self.context = context
        self.request = request

    name = 'Malone'


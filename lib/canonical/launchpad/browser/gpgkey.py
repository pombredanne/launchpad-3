# Copyright 2004 Canonical Ltd


class GPGKeyView(object):

    def __init__(self, context, request):
        self.request = request
        self.context = context

    def show(self):
        self.request.response.setHeader('Content-Type', 'text/plain')
        return self.context.gpg.pubkey


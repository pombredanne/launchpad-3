
class POTemplateSubsetView(object):

    def __init__(self, context, request):
        self.context = context
        self.request = request

    def __call__(self):
        # We are not using this context directly, only for traversals.
        return self.request.response.redirect('../+translations')


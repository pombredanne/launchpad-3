__metaclass__ = type

class ProductMilestoneAddView:
    def create(self, *args, **kw):
        """Inject the product ID into the kw args."""
        kw['product'] = self.context.id
        return self._factory(*args, **kw)

    def add(self, content):
        """Skipping 'adding' this content to a container, because
        this is a placeless system."""
        return content

    def nextURL(self):
        return '.'

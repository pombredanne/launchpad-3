# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Data model objects for the LAZR example web service."""

__metaclass__ = type
__all__ = ['Cookbook',
           'CookbookServiceRootResource',
           'CookbookSet',
           'CookbookWebServiceObject',
           'CookbookServiceRootAbsoluteURL']

from datetime import date

from zope.interface import implements
from zope.traversing.browser.interfaces import IAbsoluteURL
from zope.component import adapts, getUtility
from zope.publisher.interfaces.browser import IDefaultBrowserLayer
from zope.schema.interfaces import IBytes

from canonical.lazr.rest import ServiceRootResource

from canonical.lazr.interfaces.rest import (
    IByteStorage, IEntry, IServiceRootResource, ITopLevelEntryLink,
    IWebServiceConfiguration)
from canonical.lazr.rest.example.interfaces import (
    AlreadyNew, Cuisine, ICookbook, ICookbookSet, IDish, IDishSet,
    IRecipe, IRecipeSet, IHasGet, NameAlreadyTaken)



#Entry classes.
class CookbookWebServiceObject:
    """A basic object published through the web service."""

class SimpleByteStorage(CookbookWebServiceObject):
    """A simple IByteStorage implementation"""
    implements(IByteStorage)
    adapts(IEntry, IBytes)

    def __init__(self, entry, field):
        self.entry = entry
        self.field = field
        self.is_stored = getattr(
            self.entry, field.__name__, None) is not None
        if self.is_stored:
            self.filename = getattr(self.entry, field.__name__).filename
        else:
            self.filename = field.__name__

        # AbsoluteURL implementation.
        self.__parent__ = self.entry.context
        self.__name__ = self.field.__name__

    @property
    def alias_url(self):
        return 'http://librarian.dev/files/%s' % self.filename

    def createStored(self, mediaType, representation, filename=None):
        self.representation = representation
        if filename is not None:
            self.filename = filename
        setattr(self.entry, self.field.__name__, self)

    def deleteStored(self):
        setattr(self.entry, self.field.__name__, None)


class Cookbook(CookbookWebServiceObject):
    """An object representing a cookbook"""
    implements(ICookbook)
    def __init__(self, name, description, cuisine, copyright_date,
                 confirmed=False):
        self.name = name
        self.cuisine = cuisine
        self.description = description
        self.recipes = []
        self.copyright_date = copyright_date
        self.confirmed = confirmed
        self.cover = None

    @property
    def __name__(self):
        return self.name

    @property
    def __parent__(self):
        return getUtility(ICookbookSet)

    def get(self, name):
        """See `IHasGet`."""
        match = [recipe for recipe in self.recipes
                 if recipe.dish.name == name]
        if len(match) > 0:
            return match[0]
        return None

    def find_recipes(self, search):
        """See `ICookbook`."""
        recipes = []
        for recipe in self.recipes:
            if search in recipe.dish.name:
                recipes.append(recipe)
        return recipes

    def make_more_interesting(self):
        """See `ICookbook`."""
        if self.name.find("The New ") == 0:
            raise AlreadyNew(
                "The 'New' trick can't be used on this cookbook "
                "because its name already starts with 'The New'.")
        self.name = "The New " + self.name


class Dish(CookbookWebServiceObject):
    implements(IDish)

    def __init__(self, name):
        self.name = name
        self.recipes = []

    @property
    def __name__(self):
        return self.name

    @property
    def __parent__(self):
        return getUtility(IDishSet)


class Recipe(CookbookWebServiceObject):
    implements(IRecipe)

    def __init__(self, id, cookbook, dish, instructions, private=False):
        self.id = id
        self.dish = dish
        self.dish.recipes.append(self)
        self.cookbook = cookbook
        self.cookbook.recipes.append(self)
        self.instructions = instructions
        self.private = private
        self.prepared_image = None

    @property
    def __name__(self):
        return str(self.id)

    @property
    def __parent__(self):
        return getUtility(IRecipeSet)


# Top-level objects.
class CookbookTopLevelObject(CookbookWebServiceObject):
    """An object published at the top level of the web service."""

    @property
    def __parent__(self):
        return getUtility(IServiceRootResource)

    @property
    def __name__(self):
        raise NotImplementedError()


class FeaturedCookbookLink(CookbookTopLevelObject):
    """A link to the currently featured cookbook."""
    implements(ITopLevelEntryLink)

    @property
    def __parent__(self):
        return getUtility(ICookbookSet)

    __name__ = "featured"

    link_name = "featured_cookbook"
    entry_type = ICookbook


class CookbookSet(CookbookTopLevelObject):
    """The set of all cookbooks."""
    implements(ICookbookSet)

    __name__ = "cookbooks"

    def __init__(self, cookbooks=None):
        if cookbooks is None:
            cookbooks = COOKBOOKS
        self.cookbooks = list(cookbooks)
        self.featured = self.cookbooks[0]

    def getCookbooks(self):
        return self.cookbooks

    def get(self, name):
        match = [c for c in self.cookbooks if c.name == name]
        if len(match) > 0:
            return match[0]
        return None

    def find_recipes(self, search):
        recipes = []
        for cookbook in self.cookbooks:
            recipes.extend(cookbook.find_recipes(search))
        return recipes

    def find_for_cuisine(self, cuisine):
        """See `ICookbookSet`"""
        cookbooks = []
        for cookbook in self.cookbooks:
            if cookbook.cuisine == cuisine:
                cookbooks.append(cookbook)
        return cookbooks

    def create(self, name, description, cuisine, copyright_date):
        for cookbook in self.cookbooks:
            if cookbook.name == name:
                raise NameAlreadyTaken(
                    'A cookbook called "%s" already exists.' % name)
        cookbook = Cookbook(name, description, cuisine, copyright_date)
        self.cookbooks.append(cookbook)
        return cookbook


class DishSet(CookbookTopLevelObject):
    """The set of all dishes."""
    implements(IDishSet)

    __name__ = "dishes"

    def __init__(self, dishes=None):
        if dishes is None:
            dishes = DISHES
        self.dishes = list(dishes)

    def getDishes(self):
        return self.dishes

    def get(self, name):
        match = [d for d in self.dishes if d.name == name]
        if len(match) > 0:
            return match[0]
        return None


class RecipeSet(CookbookTopLevelObject):
    """The set of all recipes."""
    implements(IRecipeSet)

    __name__ = "recipes"

    def __init__(self, recipes=None):
        if recipes is None:
            recipes = RECIPES
        self.recipes = list(recipes)

    def getRecipes(self):
        return self.recipes

    def get(self, id):
        id = int(id)
        match = [r for r in self.recipes if r.id == id]
        if len(match) > 0:
            return match[0]
        return None


# Define some globally accessible sample data.
def year(year):
    """Turn a year into a datetime.date object."""
    return date(year, 1, 1)

C1 = Cookbook(u"Mastering the Art of French Cooking", "", Cuisine.FRANCAIS,
              year(1961))
C2 = Cookbook(u"The Joy of Cooking", "", Cuisine.GENERAL, year(1995))
C3 = Cookbook(u"James Beard's American Cookery", "", Cuisine.AMERICAN,
              year(1972))
C4 = Cookbook(u"Everyday Greens", "", Cuisine.VEGETARIAN, year(2003))
C5 = Cookbook(u"I'm Just Here For The Food", "", Cuisine.GENERAL, year(2002))
C6 = Cookbook(u"Cooking Without Recipes", "", Cuisine.GENERAL, year(1959))
C7 = Cookbook(u"Construsions un repas", "", Cuisine.FRANCAIS, year(2007))
COOKBOOKS = [C1, C2, C3, C4, C5, C6, C7]

D1 = Dish("Roast chicken")
C1_D1 = Recipe(1, C1, D1, u"You can always judge...")
C2_D1 = Recipe(2, C2, D1, u"Draw, singe, stuff, and truss...")
C3_D1 = Recipe(3, C3, D1, u"A perfectly roasted chicken is...")

D2 = Dish("Baked beans")
C2_D2 = Recipe(4, C2, D2, "Preheat oven to...")
C3_D2 = Recipe(5, C3, D2, "Without doubt the most famous...", True)

D3 = Dish("Foies de voilaille en aspic")
C1_D3 = Recipe(6, C1, D3, "Chicken livers sauteed in butter...")

DISHES = [D1, D2, D3]
RECIPES = [C1_D1, C2_D1, C3_D1, C2_D2, C3_D2, C1_D3]


# Define classes for the service root.
class CookbookServiceRootResource(ServiceRootResource):
    """A service root for the cookbook web service.

    Traversal to top-level resources is handled with the get() method.
    The top-level objects are stored in the top_level_names dict.
    """
    implements(IHasGet)

    @property
    def top_level_names(self):
        """Access or create the list of top-level objects."""
        return {'cookbooks': getUtility(ICookbookSet),
                'dishes' : getUtility(IDishSet),
                'recipes' : getUtility(IRecipeSet)}

    def get(self, name):
        """Traverse to a top-level object."""
        obj = self.top_level_names.get(name)
        return obj


class CookbookServiceRootAbsoluteURL:
    """A basic implementation of IAbsoluteURL for the root object."""
    implements(IAbsoluteURL)
    adapts(CookbookServiceRootResource, IDefaultBrowserLayer)

    HOSTNAME = "http://cookbooks.dev/"

    def __init__(self, context, request):
        """Initialize with respect to a context and request."""
        self.version = getUtility(
            IWebServiceConfiguration).service_version_uri_prefix

    def __str__(self):
        """Return the semi-hard-coded URL to the service root."""
        return self.HOSTNAME + self.version

    __call__ = __str__

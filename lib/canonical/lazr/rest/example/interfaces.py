# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface objects for the LAZR example web service."""

__metaclass__ = type
__all__ = ['AlreadyNouvelle',
           'ICookbook',
           'ICookbookSet',
           'IDish',
           'IDishSet',
           'IHasGet',
           'IRecipe',
           'IRecipeSet',
           'NameAlreadyTaken']

from zope.interface import Interface
from zope.schema import Bool, Date, Int, TextLine, Text

from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.interfaces.rest import ITopLevelEntryLink
from canonical.lazr.rest.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_as_webservice_entry, export_factory_operation,
    export_read_operation, export_write_operation, exported,
    operation_parameters, operation_returns_collection_of, webservice_error)


class AlreadyNouvelle(Exception):
    """A cookbook's cuisine prohibits the cheap 'Nouvelle' trick."""
    webservice_error(400)


class NameAlreadyTaken(Exception):
    """The name given for a cookbook is in use by another cookbook."""
    webservice_error(409)


class WhitespaceStrippingTextLine(TextLine):
    """A TextLine that won't abide leading or trailing whitespace."""

    def set(self, object, value):
        """Strip whitespace before setting."""
        if value is not None:
            value = value.strip()
        super(WhitespaceStrippingTextLine, self).set(object, value)


class IHasGet(Interface):
    """A marker interface objects that implement traversal with get()."""
    def get(name):
        """Traverse to a contained object."""


class IDish(Interface):
    """A dish, annotated for export to the web service."""
    export_as_webservice_entry(plural_name='dishes')
    name = exported(TextLine(title=u"Name", required=True))
    recipes = exported(CollectionField(
            title=u"Recipes in this cookbook",
            value_type=Reference(schema=Interface)))


class IRecipe(Interface):
    """A recipe, annotated for export to the web service."""
    export_as_webservice_entry()
    id = exported(Int(title=u"Unique ID", required=True))
    dish = exported(Reference(title=u"Dish", schema=IDish))
    cookbook = exported(Reference(title=u"Cookbook", schema=Interface))
    instructions = exported(Text(title=u"How to prepare the recipe",
                                 required=True))
    private = exported(Bool(title=u"Whether the public can see this recipe.",
                       default=False))


class ICookbook(IHasGet):
    """A cookbook, annotated for export to the web service."""
    export_as_webservice_entry()
    name = exported(TextLine(title=u"Name", required=True))
    copyright_date = exported(Date(title=u"Copyright Date", readonly=True))
    cuisine = exported(WhitespaceStrippingTextLine(
            title=u"Cuisine", required=False, default=None))
    recipes = exported(CollectionField(title=u"Recipes in this cookbook",
                                       value_type=Reference(schema=IRecipe)))

    @operation_parameters(
        search=TextLine(title=u"String to search for in recipe name."))
    @operation_returns_collection_of(IRecipe)
    @export_read_operation()
    def find_recipes(search):
        """Search for recipes in this cookbook."""

    @export_write_operation()
    def make_more_interesting():
        """Alter a cookbook to make it seem more interesting."""


# Resolve dangling references
IDish['recipes'].value_type.schema = IRecipe
IRecipe['cookbook'].schema = ICookbook


class IFeaturedCookbookLink(ITopLevelEntryLink):
    """A marker interface."""


class ICookbookSet(IHasGet):
    """The set of all cookbooks, annotated for export to the web service."""
    export_as_webservice_collection(ICookbook)

    @collection_default_content()
    def getCookbooks():
        """Return the list of cookbooks."""

    @operation_parameters(
        search=TextLine(title=u"String to search for in recipe name."))
    @operation_returns_collection_of(IRecipe)
    @export_read_operation()
    def find_recipes(search):
        """Search for recipes across cookbooks."""

    @export_factory_operation(ICookbook, ['name', 'cuisine', 'copyright_date'])
    def create(name, cuisine, copyright_date):
        """Create a new cookbook."""


class IDishSet(IHasGet):
    """The set of all dishes, annotated for export to the web service."""
    export_as_webservice_collection(IDish)

    @collection_default_content()
    def getDishes():
        """Return the list of dishes."""


class IRecipeSet(IHasGet):
    """The set of all recipes, annotated for export to the web service."""
    export_as_webservice_collection(IRecipe)

    @collection_default_content()
    def getRecipes():
        """Return the list of recipes."""

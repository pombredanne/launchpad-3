# Copyright 2009 Canonical Ltd.  All rights reserved.
# pylint: disable-msg=E0211,E0213

"""Interface objects for the LAZR example web service."""

__metaclass__ = type
__all__ = ['ICookbook',
           'ICookbookSet',
           'IDish',
           'IDishSet',
           'IHasGet',
           'IRecipe']

from zope.interface import Interface
from zope.schema import Int, TextLine, Text

from canonical.lazr.fields import CollectionField, Reference
from canonical.lazr.rest.declarations import (
    collection_default_content, export_as_webservice_collection,
    export_as_webservice_entry, exported)


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
    #private = exported(Bool(title=u"Whether the public can see this recipe.",
    #                   default=False))


class ICookbook(Interface):
    """A cookbook, annotated for export to the web service."""
    export_as_webservice_entry()
    name = exported(TextLine(title=u"Name", required=True))
    cuisine = exported(
        TextLine(title=u"Cuisine", required=False, default=None))
    recipes = exported(CollectionField(title=u"Recipes in this cookbook",
                                       value_type=Reference(schema=IRecipe)))


# Resolve dangling references
IDish['recipes'].value_type.schema = IRecipe
IRecipe['cookbook'].schema = ICookbook


class IHasGet(Interface):
    """A marker interface objects that implement traversal with get()."""
    def get(name):
        """Traverse to a contained object."""

class ICookbookSet(IHasGet):
    """The set of all cookbooks, annotated for export to the web service."""
    export_as_webservice_collection(ICookbook)

    @collection_default_content()
    def getCookbooks():
        """Return the list of cookbooks."""

class IDishSet(IHasGet):
    """The set of all dishes, annotated for export to the web service."""
    export_as_webservice_collection(IDish)

    @collection_default_content()
    def getDishes():
        """Return the list of dishes."""

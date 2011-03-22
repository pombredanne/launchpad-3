# Copyright 2009 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).

"""Helpers to patch circular import shortcuts for the webservice.

Many of the exports for the webservice entries deliberately set various
types to `Interface` because using the real types cause circular import
problems.

The only current option is to later patch the types to the correct value.
The helper functions in this file make that easy.
"""

__metaclass__ = type

__all__ = [
    'patch_entry_return_type',
    'patch_choice_parameter_type',
    'patch_choice_vocabulary',
    'patch_collection_property',
    'patch_collection_return_type',
    'patch_plain_parameter_type',
    'patch_list_parameter_type',
    'patch_reference_property',
    ]


from zope.schema import getFields

from lazr.restful.declarations import LAZR_WEBSERVICE_EXPORTED


def patch_entry_return_type(exported_class, method_name, return_type):
    """Update return type for a webservice method that returns entries.

    :param exported_class: The class containing the method.
    :param method_name: The method name that you need to patch.
    :param return_type: The new return type for the method.
    """
    exported_class[method_name].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)['return_type'].schema = return_type


def patch_collection_return_type(exported_class, method_name, return_type):
    """Update return type for a webservice method that returns a collection.

    :param exported_class: The class containing the method.
    :param method_name: The method name that you need to patch.
    :param return_type: The new return type for the method.
    """
    collection = exported_class[method_name].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)
    collection['return_type'].value_type.schema = return_type


def patch_list_parameter_type(exported_class, method_name, param_name,
        param_type):
    """Update a list parameter type for a webservice method.

    :param exported_class: The class containing the method.
    :param method_name: The method name that you need to patch.
    :param param_name: The name of the parameter that you need to patch.
    :param param_type: The new type for the parameter.
    """
    method = exported_class[method_name]
    params = method.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)['params']
    params[param_name].value_type = param_type


def patch_plain_parameter_type(exported_class, method_name, param_name,
                               param_type):
    """Update a plain parameter type for a webservice method.

    :param exported_class: The class containing the method.
    :param method_name: The method name that you need to patch.
    :param param_name: The name of the parameter that you need to patch.
    :param param_type: The new type for the parameter.
    """
    exported_class[method_name].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)['params'][param_name].schema = param_type


def patch_choice_parameter_type(exported_class, method_name, param_name,
                                choice_type):
    """Update a `Choice` parameter type for a webservice method.

    :param exported_class: The class containing the method.
    :param method_name: The method name that you need to patch.
    :param param_name: The name of the parameter that you need to patch.
    :param choice_type: The new choice type for the parameter.
    """
    param = exported_class[method_name].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)['params'][param_name]
    param.vocabulary = choice_type


def patch_reference_property(exported_class, property_name, property_type):
    """Set the type of the given property on the given class.

    :param exported_class: The class containing the property.
    :param property_name: The name of the property whose type you need
        to patch.
    :param property_type: The new type for the property.
    """
    exported_class[property_name].schema = property_type


def patch_collection_property(exported_class, property_name,
                              collection_type):
    """Set the collection type of the given property on the given class.

    :param exported_class: The class containing the property.
    :param property_name: The name of the property whose type you need
        to patch.
    :param collection_type: The `Collection` type.
    """
    exported_class[property_name].value_type.schema = collection_type


def patch_choice_vocabulary(exported_class, method_name, param_name,
                            vocabulary):
    """Set the `Vocabulary` for a `Choice` parameter for a given method.

    :param exported_class: The class containing the property.
    :param property_name: The name of the property whose type you need
        to patch.
    :param vocabulary: The `Vocabulary` type.
    """
    exported_class[method_name].queryTaggedValue(
        LAZR_WEBSERVICE_EXPORTED)[
            'params'][param_name].vocabulary = vocabulary


def patch_entry_explicit_version(interface, version):
    """Make it look as though an entry definition used as_of.

    This function should be phased out in favor of actually using as_of.
    This function patches the entry's fields as well as the entry itself.
    """
    tagged = interface.getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    versioned = tagged.dict_for_name(version) or tagged.dict_for_name(None)
    if versioned is None:
        import pdb; pdb.set_trace()
    versioned['_as_of_was_used'] = True

    # Now tag the fields.
    for name, field in getFields(interface).items():
        tagged = field.queryTaggedValue(LAZR_WEBSERVICE_EXPORTED)
        if tagged is None:
            continue
        versioned = tagged.dict_for_name(version) or tagged.dict_for_name(None)
        if versioned is None:
            # This field is first published in some other version.
            continue
        else:
            versioned['_as_of_was_used'] = True


def patch_operation_explicit_version(interface, method_name, version):
    """Make it look like operation's first tag was @operation_for_version.

    This function should be phased out in favor of actually using
    @operation_for_version.
    """
    tagged = interface[method_name].getTaggedValue(LAZR_WEBSERVICE_EXPORTED)
    try:
        tagged.rename_version(None, version)
    except Exception, e:
        # i guess it's ok?
        pass

# Copyright 2009 Canonical Ltd.  All rights reserved.

"""Metaclass to automatically decorate methods."""

from types import FunctionType


__metaclass__ = type
__all__ = ['AutoDecorate']


def AutoDecorate(*decorators):
    """Factory to generate metaclasses that automatically apply decorators."""

    class AutoDecorateMetaClass(type):
        def __new__(cls, class_name, bases, class_dict):
            new_class_dict = {}
            for name, value in class_dict.items():
                if type(value) == FunctionType:
                    for decorator in decorators:
                        value = decorator(value)
                        assert callable(value), (
                            "Decorator %s didn't return a callable."
                            % repr(decorator))
                new_class_dict[name] = value
            return type.__new__(cls, class_name, bases, new_class_dict)

    return AutoDecorateMetaClass

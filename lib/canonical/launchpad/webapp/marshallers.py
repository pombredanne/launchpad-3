# Copyright 2010 Canonical Ltd.  This software is licensed under the
# GNU Affero General Public License version 3 (see the file LICENSE).


__metaclass__ = type
__all__ = [
    'ChoiceErrorMarshaller'
    ]


from lazr.restful.marshallers import SimpleFieldMarshaller


class ChoiceErrorMarshaller(SimpleFieldMarshaller):

    def __init__(self, field, request, vocabulary=None):
        raise ValueError("You exported %s as an IChoice based on an "
                "SQLObjectVocabularyBase, you should use "
                "lazr.restful.fields.ReferenceChoice instead."
                % field.__name__)

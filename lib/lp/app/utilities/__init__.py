from lp.registry.enums import PUBLIC_INFORMATION_TYPES


def json_dump_information_types(cache, information_types):
    """Dump a dict of the data in the types requsted."""
    dump = {}
    for term in information_types:
        dump[term.name] = {
            'value': term.name,
            'description': term.description,
            'name': term.title,
            'is_private': (term not in PUBLIC_INFORMATION_TYPES), 'description_css_class': 'choice-description',
        }

    cache.objects['information_type_data'] = dump

# Copyright 2004 Canonical Ltd
#
# arch-tag: FA3333EC-E6E6-11D8-B7FE-000D9329A36C

#
# XXX this is vestigial... remove if not missed after 15/10/04

def xxx_is_allowed_filename(value):
    if '/' in value: # Path seperator
        return False
    if '\\' in value: # Path seperator
        return False
    if '?' in value: # Wildcard
        return False
    if '*' in value: # Wildcard
        return False
    if ':' in value: # Mac Path seperator, DOS drive indicator
        return False
    return True


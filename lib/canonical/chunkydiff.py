# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Chunky diffs.

Useful for page tests that have elisions.
"""

import re

__metaclass__ = type

def elided_source(tested, actual, debug=False, show=False):
    if debug:
        import pdb; pdb.set_trace()
    chunks = tested.split('...')

    previous_chunk = None
    chunk = None
    Unknown = None
    currentpos = 0
    results = []
    for next_chunk in chunks + [None]:
        if chunk is None:
            chunk = next_chunk
            continue
        if chunk != '':
            if previous_chunk is None:
                chunk_starts_with_ellipsis = False
            else:
                chunk_starts_with_ellipsis = True
            if next_chunk is None:
                chunk_ends_with_ellipsis = False
            else:
                chunk_ends_with_ellipsis = True

            result = find_chunk(
                chunk, actual[currentpos:],
                anchor_start=not chunk_starts_with_ellipsis,
                anchor_end=not chunk_ends_with_ellipsis,
                debug=debug, show=show)
            if result is None:
                results.append(None)
            else:
                string, startofremainder = result
                currentpos += startofremainder
                # XXX: off by one.  should be += startofremainder+1
                results.append(ResultChunk(string, currentpos))
        previous_chunk, chunk = chunk, next_chunk

    starts_with_ellipsis = chunks[0] == ''
    ends_with_ellipsis = chunks[-1] == ''

    resultsummary = ''.join(
        [mnemonic_for_result(result) for result in results]
        )
    if re.match('^N+$', resultsummary):
        # If all results are None...
        output = actual
    elif re.match('^S+$', resultsummary):
        # If no results are None...
        output = '...'.join([result.text for result in results])
        if starts_with_ellipsis:
            output = '...' + output
        if ends_with_ellipsis:
            output = output + '...'
    elif re.match('^S+N+$', resultsummary) and ends_with_ellipsis:
        # Where there are one or more None values at the end of results,
        # and ends_with_ellipsis, we can end without an ellipsis while
        # including the remainder of 'actual' from the end of the last
        # matched chunk.

        # Find last non-None result.
        for result in reversed(results):
            if result is not None:
                break
        # Get the remainder value from it.
        if starts_with_ellipsis:
            output = '...'
        else:
            # XXX: test this code path!
            output = ''
        last_result = None
        for result in results:
            if result is not None:
                output += result.text
                last_result = result
            else:
                output += actual[last_result.remainderpos:]
                break

    else:
        raise ValueError("mixed output: %s" % resultsummary)

    return output

class ResultChunk:

    def __init__(self, text, remainderpos):
        self.text = text
        self.remainderpos = remainderpos


def reversed(seq):
    L = list(seq)
    L.reverse()
    return L

def mnemonic_for_result(result):
    """Returns 'N' if result is None, otherwise 'S'."""
    if result is None:
        return 'N'
    else:
        return 'S'

def find_chunk(chunk, actual, anchor_start=False, anchor_end=False,
               debug=False, show=False):
    if debug:
        import pdb; pdb.set_trace()
    if not anchor_start:
        # Find the start of the chunk.
        beginning = ''
        manyfound = False
        for char in chunk:
            beginning += char
            numfound = actual.count(beginning)
            if numfound == 0:
                if manyfound:
                    beginning = manyfound_beginning
                    if anchor_end:
                        beginning_pos = actual.rfind(beginning)
                    else:
                        beginning_pos = actual.find(beginning)
                    break
                else:
                    return None
            elif numfound == 1:
                beginning_pos = actual.find(beginning) + len(beginning)
                break
            else:
                manyfound = True
                manyfound_beginning = beginning
        else:
            if manyfound:
                if anchor_end:
                    beginning_pos = actual.rfind(beginning)
                else:
                    beginning_pos = actual.find(beginning)
            else:
                return None
    else:
        beginning_pos = 0
        beginning = ''

    # Find the end of the chunk.
    end = ''
    chunk_with_no_beginning = chunk[len(beginning):]
    if not chunk_with_no_beginning:
        end_pos = beginning_pos
    elif not anchor_end:
        # Remove the beginning from the chunk.
        reversed_chunk = list(chunk_with_no_beginning)
        reversed_chunk.reverse()
        manyfound = False
        for char in reversed_chunk:
            end = char + end
            numfound = actual.count(end)
            if numfound == 0:
                # None found this time around.  If we previously found more
                # than one match, then choose the closest to the beginning.
                if manyfound:
                    end = manyfound_end
                    end_pos = actual.find(end, beginning_pos)
                    break
                else:
                    return None
            elif numfound == 1:
                end_pos = actual.rfind(end)
                break
            else:
                manyfound = True
                manyfound_end = end
        else:
            return None
    else:
        end_pos = len(actual)
        end = ''

    chunk_equivalent = actual[beginning_pos:end_pos]
    if show:
        output = '[%s]%s[%s]' % (beginning, chunk_equivalent, end)
    else:
        output = '%s%s%s' % (beginning, chunk_equivalent, end)
    return (output, end_pos+1)

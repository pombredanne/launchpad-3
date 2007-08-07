# Copyright 2004-2005 Canonical Ltd.  All rights reserved.
"""Chunky diffs.

Useful for page tests that have elisions.
"""

import re

__metaclass__ = type

def elided_source(tested, actual, debug=False, show=False,
                  normalize_whitespace=False):
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
                debug=debug, show=show,
                normalize_whitespace=normalize_whitespace)
            if result is None:
                results.append(None)
            else:
                string, startofremainder = result
                currentpos += startofremainder
                # XXX: ddaa 2005-03-25:
                # Off by one. Should be += startofremainder + 1
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
            # XXX: ddaa 2005-03-25: Test this code path!
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
        # XXX: ddaa 2005-03-25: Test this code path!
        output = actual

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
               debug=False, show=False, normalize_whitespace=False):
    if debug:
        import pdb; pdb.set_trace()
    if not anchor_start:
        # Find the start of the chunk.
        beginning = ''
        beginning_for_regex = ''
        manyfound = False
        for char in chunk:
            if normalize_whitespace and char.isspace():
                if beginning_for_regex[-2:] != r'\s':
                    beginning_for_regex += r'\s'
            else:
                beginning_for_regex += re.escape(char)
            beginning += char
            numfound = len(re.findall(beginning_for_regex, actual))
            #numfound = actual.count(beginning)
            if numfound == 0:
                if manyfound:
                    beginning = manyfound_beginning
                    beginning_for_regex = manyfound_beginning_for_regex
                    if anchor_end:
                        beginning_pos = list(re.finditer(
                            beginning_for_regex, actual))[-1].start()
                        #beginning_pos = actual.rfind(beginning)
                    else:
                        beginning_pos = re.search(
                            beginning_for_regex, actual).start()
                        # XXX ddaa 2005-03-25: This should be .span()[1]. 
                        # Needs a test.
                        #beginning_pos = actual.find(beginning)
                    break
                else:
                    beginning = ''
                    beginning_for_regex = ''
                    beginning_pos = 0
                    break
            elif numfound == 1:
                beginning_pos = re.search(
                    beginning_for_regex, actual).span()[1]
                #beginning_pos = actual.find(beginning) + len(beginning)
                break
            else:
                manyfound = True
                manyfound_beginning = beginning
                manyfound_beginning_for_regex = beginning_for_regex
        else:
            if manyfound:
                if anchor_end:
                    beginning_pos = list(re.finditer(
                        beginning_for_regex, actual))[-1].start()
                    #beginning_pos = actual.rfind(beginning)
                else:
                    beginning_pos = re.search(
                        beginning_for_regex, actual).start()
                    # XXX ddaa 2005-03-25: This should be .span()[1]. 
                    # Needs a test.
                    #beginning_pos = actual.find(beginning)
            else:
                return None
    else:
        beginning_pos = 0
        beginning = ''
        beginning_for_regex = ''

    # Find the end of the chunk.
    end = ''
    end_for_regex = ''
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
            if normalize_whitespace and char.isspace():
                if end_for_regex[:2] != r'\s':
                    end_for_regex = r'\s' + end_for_regex
            else:
                end_for_regex = re.escape(char) + end_for_regex
            numfound = len(re.findall(end_for_regex, actual))
            #numfound = actual.count(end)
            if numfound == 0:
                # None found this time around.  If we previously found more
                # than one match, then choose the closest to the beginning.
                if manyfound:
                    end = manyfound_end
                    end_for_regex = manyfound_end_for_regex
                    end_pos = re.search(end_for_regex, actual).start()
                    #end_pos = actual.find(end, beginning_pos)
                    # XXX: ddaa 2005-03-25:
                    #      This was wrong -- shouldn't be beginning_pos as
                    #      we've already chopped off the beginning!
                    #      Or is it?  We chopped the beginning of the chunk,
                    #      not the actual stuff. So, using beginning_pos
                    #      still holds. Need to chop that off and add on
                    #      its length.
                    break
                else:
                    return None
            elif numfound == 1:
                end_pos = re.search(end_for_regex, actual).start()
                #end_pos = actual.rfind(end)
                # XXX: ddaa 2005-03-25: Only one found, so why not use find()?
                break
            else:
                manyfound = True
                manyfound_end = end
                manyfound_end_for_regex = end_for_regex
        else:
            if manyfound:
                end_pos = re.search(end_for_regex, actual).start()
            else:
                return None
    else:
        end_pos = len(actual)
        end = ''
        end_for_regex = ''

    chunk_equivalent = actual[beginning_pos:end_pos]
    if show:
        output = '[%s]%s[%s]' % (beginning, chunk_equivalent, end)
    else:
        output = '%s%s%s' % (beginning, chunk_equivalent, end)
    # XXX: ddaa 2005-03-25: end_pos+1 is the end of chunk_equivalent, not end.
    return (output, end_pos+1)

# (c) Canonical Software Ltd. 2004, all rights reserved.
#
# arch-tag: fbcb5758-d345-4610-8e57-8cc664a376bc

def prefix_multi_line_string(str, prefix, include_blank_lines=0):
    """Utility function to split an input string and prefix each line
    with a token or tag. Can be used for quoting text etc"""
    out = ""
    for line in str.split('\n'):
        line = line.strip()
        if line or include_blank_lines:
            out += "%s%s\n" % (prefix, line)
    # Strip trailing new line
    if out:
        out = out[:-1]
    return out


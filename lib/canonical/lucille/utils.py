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

def extract_component_from_section(section, default_component = "main"):
    component = ""
    if section.find("/") != -1:
        component,section = section.split("/")
    else:
        component = default_component

    return (section,component)

from canonical.lucille.TagFiles import ChangesParseError

def build_file_list(tagfile, is_dsc = False, default_component = "main" ):
    files = {}
    
    if "files" not in tagfile:
        raise ValueError("No Files section in supplied tagfile")

    format = tagfile["format"]

    format = float(format)

    if not is_dsc and (format < 1.5 or format > 2.0):
        raise ValueError("Unsupported format '%s'" % tagfile["format"])

    for line in tagfile["files"].split("\n"):
        if not line:
            break

        tokens = line.split()

        section = priority = ""

        try:
            if is_dsc:
                (md5, size, name) = tokens
            else:
                (md5, size, section, priority, name) = tokens
        except ValueError:
            raise ChangesParseError(line)

        if section == "":
            section = "-"
        if priority == "":
            priority = "-"

        (section, component) = extract_component_from_section(section)

        files[name] = {
            "md5sum": md5,
            "size": size,
            "section": section,
            "priority": priority,
            "component": component
            }
        
    return files

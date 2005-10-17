set client_min_messages=ERROR;

-- First we make sure all shipping requests have a recipientdisplayname
-- and it's an ascii string.
CREATE OR REPLACE FUNCTION generate_recipientdisplayname() RETURNS integer AS '
    from htmlentitydefs import codepoint2name

    def unicode_to_unaccented_str(text):
        """Converts a unicode string into an ascii-only str, converting accented
        characters to their plain equivalents.

        >>> unicode_to_unaccented_str(u"")
        ""
        >>> unicode_to_unaccented_str(u"foo bar 123")
        "foo bar 123"
        >>> unicode_to_unaccented_str(u"viva S\xe3o Carlos!")
        "viva Sao Carlos!"
        """
        L = []
        for char in text:
            charnum = ord(char)
            codepoint = codepoint2name.get(charnum)
            if codepoint is not None:
                strchar = codepoint[0]
            else:
                try:
                    strchar = char.encode("ascii")
                except UnicodeEncodeError:
                    strchar = ""
            L.append(strchar)
        return "".join(L).encode("ASCII")

    def extract_suitable_name(familyname, givenname, displayname):
        """Try to extract a name that is suitable for being exported from the
        three given names.

        This suitable name must be less than 20 characaters long.
        """
        if not (familyname and givenname):
            if len(displayname) <= 20:
                return displayname
            else:
                displaynames = displayname.split()
                if len(displaynames) < 2:
                    return displayname[:20]

                first, last = displaynames[0], displaynames[-1]
                if len(first + last) < 20:
                    return "%s %s" % (first, last)
                else:
                    return last[:20]
                    
        if len(givenname + familyname) < 20:
            return "%s %s" % (givenname, familyname)
        givennames = sorted(givenname.split(), key=len, reverse=True)
        familynames = sorted(familyname.split(), key=len, reverse=True)
        finalname = ""
        for familyname in familynames:
            for givenname in givennames:
                if len(familyname + givenname) < 20:
                    finalname = "%s %s" % (givenname, familyname)
                    break
            else:
                continue
            break
        else:
            finalname = familynames[0][:20]
        return finalname

    requests = plpy.execute("""
        SELECT ShippingRequest.id, ShippingRequest.recipient,
               Person.familyname, Person.givenname, Person.displayname
            FROM ShippingRequest, Person
            WHERE ShippingRequest.recipientdisplayname IS NULL AND
                  Person.id = ShippingRequest.recipient
        """)

    num = 0
    for row in requests:
        name = extract_suitable_name(
            (row["familyname"] or "").decode("UTF-8"),
            (row["givenname"] or "").decode("UTF-8"),
            (row["displayname"] or "").decode("UTF-8"))
        name = unicode_to_unaccented_str(name)
        p = plpy.prepare("""
            UPDATE ShippingRequest 
                SET recipientdisplayname = $1
                WHERE id = $2
            """, ["text", "numeric"])
        plpy.execute(p, [name.encode("ASCII"), row["id"]])
        num += 1
    return num
' LANGUAGE plpythonu;

SELECT generate_recipientdisplayname();

DROP FUNCTION generate_recipientdisplayname();

INSERT INTO LaunchpadDatabaseRevision VALUES (25, 34, 0);



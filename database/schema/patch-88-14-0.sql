SET client_min_messages=ERROR;

-- For each bug report that has Web links, append a blank line to the
-- description, and then the title and URL of each bug link.

CREATE AGGREGATE concat (
    BASETYPE = text,
    SFUNC = textcat,
    STYPE = text,
    INITCOND = ''
);

CREATE TEMPORARY TABLE links_as_text (
    bug integer primary key,
    links text
);

INSERT INTO links_as_text (bug, links)
    SELECT bug, concat('\n' || title || ': ' || url)
        FROM bugexternalref
        GROUP BY bug
        ORDER BY bug;

UPDATE bug
    SET description = bug.description || '\n' || links_as_text.links
    FROM links_as_text WHERE bug.id = links_as_text.bug;

-- Once all the links are migrated, clean up, and abolish the Web links table.

DROP AGGREGATE concat(text);
DROP TABLE bugexternalref;

INSERT INTO LaunchpadDatabaseRevision VALUES (88, 14, 0);

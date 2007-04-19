SET client_min_messages=ERROR;

-- Fix timeouts
create index branch__product__id__idx on branch(product,id);

INSERT INTO LaunchpadDatabaseRevision VALUES (79, 0, 2);


SET client_min_messages TO error;

/* Place to store what package or revision we should use as 'canonical'
for cscvs file-id lookups. Not a join into the database as this may not
be in the database yet. */
ALTER TABLE SourceSource ADD COLUMN fileidreference text;


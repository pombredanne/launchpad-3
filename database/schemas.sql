/*
  Schemas
*/



/*
  1. Manifest Entry Types
*/
INSERT INTO Schema ( name, title, description, owner ) VALUES ( 'manifestentrytype', 'Manifest Entry Type', 'A set of types of manifest entries.', 5 );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 1, 'tar', 'Tar File', 'A Tar File' );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 1, 'patch', 'Patch File', 'A Patch File' );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 1, 'copy', 'Copied Source', 'Source checked out from an archive and copied into the source package without being tarred or diffed.' );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 1, 'dir', 'Directory', 'A directory to be created during the assembly process, with no associated code or archive.' );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 1, 'ignore', 'Ignore', 'A file or directory which should not be treated as a branch.' );


/*
  2. Packaging Types
*/
INSERT INTO Schema ( name, title, description, owner ) VALUES ( 'packaging', 'Product Packaging', 'The relationship between Product and Sourcepackage', 1 );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 2, 'packaged', 'Packaged', 'This product is directly packaged in that Sourcepackage.' );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 2, 'included', 'Included', 'This product is included in that Sourcepackage.' );


/*
  3. Arch Branch Relationship
*/
INSERT INTO Schema ( name, title, description, owner ) VALUES ( 'archbranchrel', 'Arch Branch Relationship', 'The Relationship in Arch terms between two Branches', 6 );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 3, 'continuation', 'Branch Continuation', 'The source branch was tagged off the destination branch.' );


/*
  4. Sourcerer Branch Relationship
*/
INSERT INTO Schema ( name, title, description, owner ) VALUES ( 'sourcererbranchrel', 'Sourcerer Branch Relationship', 'The relationship between two branches in Sourcerer terms.', 5 );
INSERT INTO Label ( schema, name, title, description ) VALUES ( 4, 'tracks', 'Tracking Branch', 'The source branch tracks the changes made to the destination branch.' );



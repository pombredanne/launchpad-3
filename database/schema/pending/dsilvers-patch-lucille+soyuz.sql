SET client_min_messages TO error;

/*
 * A few more cleanups regarding Soyuz and Lucille
 */

-- sourcepackageupload had a grotty pkey; clean it up...
ALTER TABLE sourcepackagepublishing DROP CONSTRAINT sourcepackageupload_pkey;

ALTER TABLE sourcepackagepublishing
   ALTER COLUMN id SET NOT NULL;

ALTER TABLE sourcepackagepublishing 
   ADD CONSTRAINT sourcepackagepublishing_pkey
     PRIMARY KEY (id);


-- SourcepackageRelease needs a section column...

ALTER TABLE sourcepackagerelease
   ADD COLUMN section integer;
   
ALTER TABLE sourcepackagerelease
   ADD CONSTRAINT sourcepackagerelease_section
     FOREIGN KEY (section) REFERENCES section(id);

ALTER TABLE sourcepackagerelease
   ALTER COLUMN section SET NOT NULL;

COMMENT ON COLUMN SourcepackageRelease.section IS 'This integer field references the Section which the source package claims to be in';


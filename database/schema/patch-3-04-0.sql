SET client_min_messages TO error;

ALTER TABLE DistroRelease ADD COLUMN shortdesc text;
UPDATE Distrorelease SET shortdesc = description;
ALTER TABLE DistroRelease ALTER COLUMN shortdesc SET NOT NULL;

/*
 * The Upload Queue mechanism for Lucille
 */
 
CREATE TABLE DistroReleaseQueue (
    id serial NOT NULL PRIMARY KEY,
    status integer NOT NULL DEFAULT 0,
    distrorelease integer NOT NULL 
        CONSTRAINT distroreleasequeue_distrorelease_fk
        REFERENCES DistroRelease(id)
);

/*
 * Convenience index to improve performance when the DistroQueue table gets
 * bigger and we need to get the queue for a given distribution
 */
CREATE INDEX distroreleasequeue_distrorelease_key
    ON DistroReleaseQueue(distrorelease);

CREATE TABLE DistroReleaseQueueSource (
    id serial NOT NULL PRIMARY KEY,
    distroreleasequeue integer NOT NULL
        CONSTRAINT distroreleasequeuesource_distroreleasequeue_fk
        REFERENCES DistroReleaseQueue(id),
    sourcepackagerelease integer NOT NULL
        CONSTRAINT distroreleasequeuesource_sourcepackagerelease_fk
        REFERENCES SourcepackageRelease(id)
);

CREATE TABLE DistroReleaseQueueBuild (
    id serial NOT NULL PRIMARY KEY,
    distroreleasequeue integer NOT NULL
        CONSTRAINT distroreleasequeuebuild_distroreleasequeue_fk
        REFERENCES DistroReleaseQueue(id),
    build integer NOT NULL
        CONSTRAINT distroreleasequeuebuild_build_fk
        REFERENCES Build(id)
);


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



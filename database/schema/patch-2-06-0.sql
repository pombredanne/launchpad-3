SET client_min_messages TO error;

/* Indexes for soyuz performance */

CREATE INDEX packagepublishing_binarypackage_key ON 
    packagepublishing (binarypackage);
/* 
This one shouldn't be needed, as we already have a 
UNIQUE(binarypackagename,version). However, Kiko's testing shows otherwise.
TODO: Confirm on a database with real data if this is necessary.
*/
CREATE INDEX binarypackage_binarypackagename_key2 ON
    binarypackage (binarypackagename); 

/*
This one is needed, even though (distrorelease, sourcepackagerelease)
is the primary key to speed searches just matching on sourcepackagerelease
*/
CREATE INDEX sourcepackageupload_sourcepackagerelease_key ON
    sourcepackageupload (sourcepackagerelease);

CREATE INDEX sourcepackagerelease_sourcepackage_key ON
    sourcepackagerelease (sourcepackage);
CREATE INDEX sourcepackage_sourcepackagename_key ON
    sourcepackage (sourcepackagename);


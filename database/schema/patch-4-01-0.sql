SET client_min_messages TO fatal;

/* Index requests from kiko */

CREATE INDEX sourcepackagepublishing_distrorelease_key 
    ON sourcepackagepublishing (distrorelease);

CREATE INDEX sourcepackagepublishing_status_key
    ON sourcepackagepublishing (status);



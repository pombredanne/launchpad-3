SET client_min_messages=ERROR;

/* Note that this column has to allow NULL as a value or else we cannot
   create a distribution (due to the circular reference between distribution
   and distrorelease
 */
ALTER TABLE Distribution ADD COLUMN primarydistrorelease integer  
    CONSTRAINT distribution_primarydistrorelease_fk REFERENCES distrorelease;

UPDATE Distribution SET primarydistrorelease=distrorelease.id
    FROM DistroRelease
    WHERE Distribution.id = DistroRelease.distribution
    AND releasestate=4;

ALTER TABLE DistroRelease ADD COLUMN primarydistroarchrelease integer
    CONSTRAINT distrorelease_primarydistroarchrelease_fk
    REFERENCES distroarchrelease;

UPDATE DistroRelease SET primarydistroarchrelease=distroarchrelease.id
    FROM DistroArchRelease
    WHERE DistroRelease.id = DistroArchRelease.distrorelease
    AND architecturetag='i386';


CREATE OR REPLACE FUNCTION check_primarydistrorelease(int,int) RETURNS boolean
AS '
    # check_primarydistrorelease(distribution, distrorelease)
    # Returns true if the distrorelease is linked to the given
    # distribition

    if args[1] is None:
        return 1
    rv = plpy.execute("""
        SELECT count(*) AS x FROM distrorelease
        WHERE distribution = %d AND id = %d
        """ % (args[0], args[1])
        )
    count = rv[0]["x"]
    if count == 0:
       return 0
    else:
       return 1
' LANGUAGE plpythonu;

ALTER TABLE Distribution ADD CONSTRAINT check_primarydistrorelease
CHECK (check_primarydistrorelease(id, primarydistrorelease));

CREATE OR REPLACE FUNCTION check_primarydistroarchrelease(int,int)
RETURNS boolean AS '
    # check_primarydistroarchrelease(distrorelease, distroarchrelease)
    # Returns true if the distroarchrelease is linked to the given
    # distrorelease

    if args[1] is None:
        return 1
    rv = plpy.execute("""
        SELECT count(*) AS x FROM distroarchrelease
        WHERE distrorelease = %d AND id = %d
        """ % (args[0], args[1])
        )
    count = rv[0]["x"]
    if count == 0:
       return 0
    else:
       return 1
' LANGUAGE plpythonu;

ALTER TABLE DistroRelease ADD CONSTRAINT check_primarydistroarchrelease
CHECK (check_primarydistroarchrelease(id, primarydistroarchrelease));



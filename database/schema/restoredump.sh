# This shell script can be used to restore a production database dump
#

DMP=launchpad_prod.20050207.pg_dump
DBNAME=rest

pg_restore -l ${DMP} \
    | grep -v SEQUENCE \
    | grep -v TABLE \
    | grep -v ACL \
    | grep -v INDEX \
    | grep -v CONSTRAINT \
    | grep -v VIEW \
    | grep -v TRIGGER \
    | grep -v COMMENT \
    | grep -v ACL \
    | grep -v BLOBS \
    > r.listing
pg_restore -l ${DMP} | grep TABLE >> r.listing
pg_restore -l ${DMP} | grep VIEW >> r.listing
pg_restore -l ${DMP} | grep INDEX >> r.listing
pg_restore -l ${DMP} | grep CONSTRAINT >> r.listing
pg_restore -l ${DMP} | grep TRIGGER >> r.listing
pg_restore -l ${DMP} | grep SEQUENCE >> r.listing
pg_restore -l ${DMP} | grep COMMENT >> r.listing
pg_restore -l ${DMP} | grep BLOBS >> r.listing
pg_restore -l ${DMP} | grep ACL >> r.listing


dropdb ${DBNAME}
createdb -E UNICODE ${DBNAME}
pg_restore -U postgres --no-acl --no-owner -L r.listing -d rest -v ${DMP} 2>&1 | grep -v NOTICE
env LP_DBNAME=${DBNAME} python security.py

#!/bin/sh

#
# Add extra JVM options here
#
OPTS="-Xms64m -Xmx256m"
if [ "$SMARTSPRITES_EXT" = "" ]; then
    echo "Missing SMARTSPRITES_EXT env var" >&2
    echo " (normally smartsprites_branch/lib)"
    exit 1
fi

java $OPTS -Djava.ext.dirs="$SMARTSPRITES_EXT" \
    org.carrot2.labs.smartsprites.SmartSprites \
    "$@"

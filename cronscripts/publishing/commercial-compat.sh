#!/bin/bash

# This script munges the partner component into a commercial pocket arrangement
# for backwards compatibility with dapper, edgy and feisty.
#
# After running, <distroseries>-commercial will appear under dists.

# LPCONFIG will come from the environment so this script can run unaltered
# on dogfood.
#
# Authors:
# Written by Fabio M Di Nitto, amended by Julian Edwards for production
# and dogfood compatibility.
#

if [ -z $LPCONFIG ]; then
    echo LPCONFIG must be set to run this script.
    exit 1
fi

# Exit immediately on errors.
set -e

# Config goes here.
PRODUCTION_CONFIG=ftpmaster
if [ "$LPCONFIG" = "$PRODUCTION_CONFIG" ]; then
    archiveurl=/srv/launchpad.net/ubuntu-archive/ubuntu-partner
else
    archiveurl=/srv/launchpad.net/ppa/ubuntu-partner
fi
compatreleases="dapper edgy feisty"

# Fix up a release file so it refers to packages in the -commercial pocket.
fixrelease() {
    in="$1"
    out="$2"

    descr=$(cat "$in" |grep ^Version: | sed -e 's#Version: ##g')

    # Add -commercial suffix where required, force the component to main,
    # and set Origin: and Label: to Canonical.
    cat "$in" | sed \
        -e 's#^Archive:.*#&-commercial#g' \
        -e 's#^Component:.*#Component: main#g' \
        -e 's#^Origin:.*#Origin: Canonical#g' \
        -e 's#^Label:.*#Label: Canonical#g' \
        -e 's#^Suite:.*#&-commercial#g' \
        -e 's#^Codename:.*#&-commercial#g' \
        -e 's#^Components:.*#Components: main#g' \
        -e 's#^Description:.*#Description: Ubuntu '"$descr"' Commercial Software#g' \
        -e 's#partner/#main/#g' \
        > "$out"
}

# Fix the topmost Release file so that its referenced Release file sizes and
# checksums are correct.
fixtoprelease() {
    in="$1"
    out="$2"
    release="$3"

    hash=""
    blank=""

    # Here we read in a line, see what type of hash is being used, and then
    # the line ending in "Release" is re-written.  Comments cannot go
    # inside {} blocks so the four commands are explained here:
    #   filename= : this will get the filename relative to the top level.
    #   sum=      : this will calculate the new checksum according to which
    #               one we're processing at the moment.
    #   size=     : get the file's size.
    #   printf    : output to the new Release file in the right format.
    #
    cat "$in" | { while read line; do
        case "$line" in
            MD5Sum:)
                hash=md5
                blank=" "
                echo "MD5Sum:"
            ;;
            SHA1:)
                hash=sha1
                blank=" "
                echo "SHA1:"
            ;;
            SHA256:)
                hash=sha256
                blank=" "
                echo "SHA256:"
            ;;
            *Release)
                filename=$(echo $line | awk '{print $3}')
                sum="$(echo $(gpg --print-md $hash $i-commercial/$filename | cut -d ":" -f 2 | tr [A-Z] [a-z]) | sed -e 's/ //g')"
                size="$(ls -ls $i-commercial/$filename | awk '{print $6}')"
                printf " %s %*d %s\n" "$sum" 16 "$size" "$filename"
            ;;
            *)
                echo "$blank$line"
            ;;
        esac
    done; } > "$out"
}

# cd into the real archive or die.
cd "$archiveurl/dists/" || exit 1

# We do this only for distroseries that we need to process.
for i in $compatreleases; do
    if [ -d "$i" ]; then
        # Nuke the old commercial pocket.
        rm -rf "$i-commercial"
        # Clone with the new one to import all the Packages and dir structure.
        cp -rp "$i" "$i-commercial"
        # Nuke the old signature that would be invalid anyway.
        rm -f "$i-commercial/Release.gpg"
        # Rename section from partner to main.
        mv $i-commercial/partner $i-commercial/main
        # Fix all Release files.
        find "$i-commercial" -name "Release" | { while read line; do
            fixrelease $line $line.new
            mv $line.new $line
        done; }
        # Top level needs more love (*sums, file size)
        fixtoprelease "$i-commercial/Release" "$i-commercial/Release.new" "$i"
        mv "$i-commercial/Release.new" "$i-commercial/Release"
        # Sign the Release file
        gpg --armour --output "$i-commercial/Release.gpg" --detach-sign "$i-commercial/Release"
    fi
done

exit 0

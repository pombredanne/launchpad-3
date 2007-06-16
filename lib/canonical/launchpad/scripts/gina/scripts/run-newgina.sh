#!/bin/sh

SRV=/home/debonzi/Warthogs/projects

cd $SRV

LOG=$SRV/logs

DATE=`date "+%Y%m%d%H%M%S"`

LPL=$SRV/branches/gina/launchpad/lib

GINA=$LPL/canonical/launchpad/scripts/gina

export LP_DBNAME=launchpad_dev
export LP_DBHOST=localhost
export LP_DBUSER=launchpad

#($GINA/scripts/reload-katie.example 2>&1) > $LOG/katie-reload.$DATE

(PYTHONPATH=$LPL python -u $GINA/gina.py \
                           --distro=ubuntu \
                           --distroseries=hoary \
                           --arch=i386 \
                           --components=main \
                           --keyrings=/home/debonzi/Warthogs/keyring.ubuntu.com/keyrings \
                           --root=/home/debonzi/Warthogs/mirror \
                           --run) | tee $LOG/gina.$DATE

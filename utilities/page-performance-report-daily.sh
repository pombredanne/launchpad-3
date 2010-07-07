#!/bin/sh
#TZ=UTC # trace logs are still BST - blech

logs=`find /x/launchpad.net-logs/production \
    -maxdepth 2 -ctime -14 -name launchpad-trace\* | xargs -x`

report () {
    type=$1
    from=$2
    until=$3

    local root
    root=${HOME}/public_html/ppr/lpnet

    local dir
    dir=${root}/${type}

    local repname
    repname="${from}_${until}.html"

    mkdir -p ${dir}/all
    mkdir -p ${dir}/categories
    mkdir -p ${dir}/pageids

    local ppr
    ppr="./page-performance-report.py -v --from=$from --until=$until"

    $ppr --no-pageids    $logs > ${dir}/categories/${repname}
    $ppr --no-categories $logs > ${dir}/pageids/${repname}
    $ppr                 $logs > ${dir}/all/${repname}

    ln -sf ${dir}/categories/${repname} ${root}/latest-${type}-categories.html
    ln -sf ${dir}/pageids/${repname} ${root}/latest-${type}-pageids.html
    ln -sf ${dir}/all/${repname} ${root}/latest-${type}-all.html

    return 0
    }

fmt='+%Y-%m-%d'

# Store dates in case this takes a while.
# 'now' is actually 2 days ago, because we need to wait until the logs
# have been synced.
now=`date -d '2 days ago' $fmt`
yesterday=`date -d '3 days ago'  $fmt`
last_week=`date -d '9 days ago'  $fmt`
last_month=`date -d '32 days ago' $fmt`

report daily   $yesterday  $now
report weekly  $last_week  $now
## We don't seem to have a months worth of tracelogs. If we enable this,
## change the -ctime in the logs= find command.
##report monthly $last_month $now


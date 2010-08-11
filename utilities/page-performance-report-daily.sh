#!/bin/sh

#TZ=UTC # trace logs are still BST - blech

category_report() {
    max_log_age=$1
    type=$2
    from=$3
    until=$4
    category=$5
    log_root=$6

    local logs
    logs=`find ${log_root} \
        -maxdepth 2 -type f -mtime -${max_log_age} -name launchpad-trace\* \
        | sort | xargs -x`

    local root
    root=${HOME}/public_html/ppr/${category}

    local dir
    dir=${root}/${type}_${from}_${until}

    mkdir -p ${dir}

    echo Generating report from $from until $until into $dir `date`

    ./page-performance-report.py -v --from=$from --until=$until \
        --directory=${dir} $logs

    ln -sf ${dir}/categories.html ${root}/latest-${type}-categories.html
    ln -sf ${dir}/pageids.html    ${root}/latest-${type}-pageids.html
    ln -sf ${dir}/combined.html   ${root}/latest-${type}-combined.html
    ln -sf ${dir}/timeout-candidates.html   ${root}/latest-${type}-timeout-candidates.html

    return 0
    }

report() {
    category_report $* edge /srv/launchpad.net-logs/edge
    category_report $* lpnet /srv/launchpad.net-logs/production
    return 0
}

fmt='+%Y-%m-%d'

now=`date $fmt`

report  3 daily `date -d yesterday $fmt` $now

if [ `date +%a` = 'Sat' ]; then
    report 9 weekly `date -d 'last week' $fmt` $now
fi

# We don't seem to have a months worth of tracelogs, but we will
# generate what we can.
if [ `date +%d` = '01' ]; then
    report 32 monthly `date -d 'last month' $fmt` $now
fi

# One off reports to populate history.
## report 40 monthly `date -d '1 june 2010' $fmt` `date -d '1 july 2010' $fmt`
## report 23 weekly `date -d '19 june 2010' $fmt` `date -d '26 june 2010' $fmt`
## report 16 weekly `date -d '26 june 2010' $fmt` `date -d '3 july 2010' $fmt`


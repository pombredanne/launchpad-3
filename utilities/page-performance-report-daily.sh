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
        --top-urls=200 --directory=${dir} $logs

    ln -sf ${dir}/categories.html ${root}/latest-${type}-categories.html
    ln -sf ${dir}/pageids.html    ${root}/latest-${type}-pageids.html
    ln -sf ${dir}/combined.html   ${root}/latest-${type}-combined.html
    ln -sf ${dir}/top200.html   ${root}/latest-${type}-top200.html
    ln -sf ${dir}/timeout-candidates.html   \
        ${root}/latest-${type}-timeout-candidates.html

    return 0
    }

report() {
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



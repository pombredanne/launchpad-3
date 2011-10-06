#!/bin/sh

#TZ=UTC # trace logs are still BST - blech

CATEGORY=lpnet
LOGS_ROOTS="/srv/launchpad.net-logs/production /srv/launchpad.net-logs/edge"
OUTPUT_ROOT=${HOME}/public_html/ppr/lpnet
DAY_FMT="+%Y-%m-%d"

find_logs() {
    from=$1
    until=$2

    end_mtime_switch=
    days_to_end="$(expr `date +%j` - `date -d $until +%j` - 1)"
    if [ $days_to_end -gt 0 ]; then
        end_mtime_switch="-daystart -mtime +$days_to_end"
    fi

    find ${LOGS_ROOTS} \
        -maxdepth 2 -type f -newermt "$from - 1 day" $end_mtime_switch \
        -name launchpad-trace\* \
        | sort | xargs -x
}

# Find all the daily stats.pck.bz2 $from $until
find_stats() {
    from=$1
    until=$2

    # Build a string of all the days within range.
    local dates
    local day
    day=$from
    while [ $day != $until ]; do
        dates="$dates $day"
        day=`date $DAY_FMT -d "$day + 1 day"`
    done

    # Use that to build a regex that will be used to select
    # the files to use.
    local regex
    regex="daily_(`echo $dates |sed -e 's/ /|/g'`)"

    find ${OUTPUT_ROOT} -name 'stats.pck.bz2' | egrep $regex
}

report() {
    type=$1
    from=$2
    until=$3
    link=$4

    local files
    local options
    if [ "$type" = "daily" ]; then
        files=`find_logs $from $until`
        options="--from=$from --until=$until"
    else
        files=`find_stats $from $until`
        options="--merge"
    fi

    local dir
    dir=${OUTPUT_ROOT}/`date -d $from +%Y-%m`/${type}_${from}_${until}
    mkdir -p ${dir}

    echo Generating report from $from until $until into $dir `date`

    ./page-performance-report.py -v  --top-urls=200 --directory=${dir} \
        $options $files

    # Only do the linking if requested.
    if [ "$link" = "link" ]; then
        ln -sf ${dir}/partition.html \
            ${OUTPUT_ROOT}/latest-${type}-partition.html
        ln -sf ${dir}/categories.html \
            ${OUTPUT_ROOT}/latest-${type}-categories.html
        ln -sf ${dir}/pageids.html \
            ${OUTPUT_ROOT}/latest-${type}-pageids.html
        ln -sf ${dir}/combined.html \
            ${OUTPUT_ROOT}/latest-${type}-combined.html
        ln -sf ${dir}/metrics.dat ${OUTPUT_ROOT}/latest-${type}-metrics.dat
        ln -sf ${dir}/top200.html ${OUTPUT_ROOT}/latest-${type}-top200.html
        ln -sf ${dir}/timeout-candidates.html   \
            ${OUTPUT_ROOT}/latest-${type}-timeout-candidates.html
    fi

    return 0
}

local link
if [ "$3" = "-l" ]; then
    link="link"
fi

if [ "$1" = '-d' ]; then
    report daily `date -d $2 $DAY_FMT` `date -d "$2 + 1 day" $DAY_FMT` $link
elif [ "$1" = '-w' ]; then
    report weekly `date -d $2 $DAY_FMT` `date -d "$2 + 1 week" $DAY_FMT` $link
elif [ "$1" = '-m' ]; then
    report monthly `date -d $2 $DAY_FMT` `date -d "$2 + 1 month" $DAY_FMT` $link
else
    # Default invocation used from cron to generate latest one.
    now=`date $DAY_FMT`
    report daily `date -d yesterday $DAY_FMT` $now link

    if [ `date +%a` = 'Sun' ]; then
        report weekly `date -d 'last week' $DAY_FMT` $now link
    fi

    if [ `date +%d` = '01' ]; then
        report monthly `date -d 'last month' $DAY_FMT` $now link
    fi
fi

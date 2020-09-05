#!/bin/bash
#########################################################################
# File Name: start.sh
# Author: zioer
# mail: xiaoyu0720@gmail.com
# Created Time: 2020年08月26日 星期三 14时44分12秒
#########################################################################

. ~/.bashrc


venv_name="spider"
workdir=./
cd $workdir

{

    for tmpdir in "running" "chrome_profile" "log"
    do
        if [ ! -r $tmpdir ] ; then
            mkdir $tmpdir
        fi
    done

    conda activate $venv_name

    if [ "$1" = "cron" ] ; then
        # 执行调度任务
        cmd="${workdir}/scheduler.py"
    else
        # 单任务执行
        cmd="${workdir}/spider_free_proxy.py $@"
    fi

    if ps -ef |grep "$cmd" |grep -v vi | grep -v grep
    then
        echo "command [$cmd] is already started!"
    else
        echo "start to run command [$cmd]"
        nohup python -u $cmd  >/dev/null 2>&1 &
    fi
    conda deactivate
}

#!/bin/bash
#########################################################################
# File Name: start.sh
# Author: zioer
# mail: xiaoyu0720@gmail.com
# Created Time: 2020年08月26日 星期三 14时44分12秒
#########################################################################

. /apps/config/myprofile

usage(){
cat <<END

------------------------------
使用说明:
    `basename $0` cron [ -c check_seconds| -p proxy_minutes]
            启动'scheduler.py'调度器，可设置检测器调度周期'check_seconds'秒(默认30秒), 代理提取器 调度周期为 'proxy_minutes' 分钟(默认10分钟)

    `basename $0` -c [all|ss|ssr|v2ray]
            启动 'spider_free_proxy.py'代理检测器

    `basename $0` -p [all|ss|ssr|v2ray]
            启动 'spider_free_proxy.py'代理提取器-执行全部爬虫(包括'pyppeteer'和'requests')

    `basename $0` -r [all|ss|ssr|v2ray]
            注意:用于第一次安装无代理时运行, 启动'spider_free_proxy.py'代理提取器-使用'requests'方法爬虫

-----------------------
END
}

if [ "$1" = ""  -o "$1" = "-h" ] ; then
    usage
    exit 0
fi

venv_name="spider"
workdir=.
cd $workdir



run_cmd()
{
    cmd="$1"
    params="$2"
    echo "run_cmd: cmd=[$cmd], params=[$params]"
    if ps -ef |grep "$cmd" |grep -v vi | grep -v grep
    then
        echo "command [$cmd] is already started!"
    else
        echo "start to run command [$cmd]"
        nohup $cmd $params  >/dev/null 2>&1 &
    fi
}
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
        shift 1
        cmd="${workdir}/scheduler.py"
        params="$@"
        run_cmd "$cmd" "$params"
    else
        # 单任务执行
        cmd="${workdir}/spider_free_proxy.py $@"
        run_cmd "$cmd"
    fi

    conda deactivate
}

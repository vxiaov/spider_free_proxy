#!/usr/bin/env bash
#########################################################################
# File Name: start.sh
# Author: zioer
# mail: xiaoyu0720@gmail.com
# Created Time: 2020年08月26日 星期三 14时44分12秒
#########################################################################

. ~/.bashrc
usage(){
cat <<END

------------------------------
使用说明:
    `basename $0` -c [all|ss|ssr|v2ray]
            启动 'spider_free_proxy.py'代理检测器

    `basename $0` -p [all|ss|ssr|v2ray]
            启动 'spider_free_proxy.py'代理提取器-执行全部爬虫(包括'pyppeteer'和'requests')

-----------------------
END
}

if [ "$1" = ""  -o "$1" = "-h" ] ; then
    usage
    exit 0
fi

workdir=/path/to/spider_free_proxy
cd $workdir

conf_file="./conf/config.ini"


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

# 单任务执行
cmd="${workdir}/bin/spider_free_proxy.py --init ${conf_file} $@"
run_cmd "$cmd"
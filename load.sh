#!/bin/bash
########################################################################
# File Name: load.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年06月18日 星期五 11时43分40秒
########################################################################

tmp_file=./log/expdata.txt

# 导出历史代理列表数据
./bin/exp_log.sh ${1:-"log/proxy_checker.log"}*  > $tmp_file

# 导入到Redis数据库中回收利用
./bin/load.py -i $tmp_file -t table


mv $tmp_file $tmp_file.`date +%Y%m%d`

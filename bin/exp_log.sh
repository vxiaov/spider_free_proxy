#!/bin/bash
########################################################################
# File Name: bin/exp_log.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年01月15日 星期五 23时42分22秒
########################################################################

# 导出日志中的历史代理记录(比如主机断网导致代理被删除后的数据恢复)
# 导出结果保存到文件中，再使用`load.py`脚本导入到`redis`中
#
#  ./bin/exp_log.sh log/proxy*.log  > all.txt
#  ./bin/load.py -i all.txt -t table   # 将all.txt中所有代理导入到对应的xxx_table中
#

awk '/INFO/ && /del/ && /start_check_socks5/ { split($12,stype, "_"); split($16, server, ":"); printf("%s %s:%s", stype[1],server[2], server[3]); for(i=19;i<NF;i++) printf(" %s", $i); printf("\n"); }' $* |sort -u



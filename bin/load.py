#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年10月25日 星期日 16时50分24秒
# Brief:
###############################################################################

import os
import sys
import argparse
from redis import StrictRedis


# 导入数据文件
datafile = sys.argv[1] if len(sys.argv) >= 2 else "all.txt"

redis_uri = "redis://localhost:6379/1"
redis = StrictRedis.from_url(redis_uri)


def load_data(init_file, table="history"):
    '''
    导入代理信息
    '''
    if not redis:
        print("无法连接到Redis")
        return 1
    with open(init_file) as f:
        datalist = f.readlines()
    for data in datalist:
        _ = data.strip().split(" ", maxsplit=2)
        stable = _[0] + "_" + table
        sserver = _[1]
        sdetail = _[2]
        ret = redis.hset(stable, sserver, sdetail)
        print("redis ret:", ret, "server:", sserver, "detail: ", sdetail)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('socks5代理信息导入工具')

    parser.add_argument('-i', '--init', default='all.txt',
                        help='设置导入文件路径')
    parser.add_argument('-t', '--ttype', default='history',
                        choices=['history', 'table'], help='设置表类型')
    parse_result = parser.parse_args()
    init_file = parse_result.init
    ttype = parse_result.ttype

    if not os.path.exists(init_file):
        print(init_file, "doesn't exist!")
        exit(1)
    load_data(init_file, ttype)
#


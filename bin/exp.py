#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年10月25日 星期日 16时50分24秒
# Brief:
###############################################################################

import argparse
from redis import StrictRedis


redis_uri = "redis://localhost:6379/1"
redis = StrictRedis.from_url(redis_uri)


def exp_data(stype="ss", file_name="all.txt"):
    '''
    导出代理信息
    '''
    if not redis:
        print("无法连接到Redis")
        return 1
    ttable = stype + "_table"
    stable = stype + "_working"
    result = redis.hgetall(stable)
    with open(file_name, 'w') as f:
        for key in list(result):
            res = redis.hget(ttable, result[key])
            f.write("{} {} {}\n".format(stype, result[key].decode(), res.decode()))
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser('socks5代理信息导入工具')

    parser.add_argument('-f', '--file', default='all.txt',
                        help='设置导出文件路径')
    parser.add_argument('-s', '--stype', default='ss',
                        choices=['ss', 'ssr', 'v2ray'], help='设置代理类型')
    parse_result = parser.parse_args()
    file_name = parse_result.file
    stype = parse_result.stype

    print(stype, file_name)
    exp_data(stype, file_name)
#

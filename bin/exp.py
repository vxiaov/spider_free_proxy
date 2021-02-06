#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年10月25日 星期日 16时50分24秒
# Brief:
###############################################################################

import os
import argparse
from redis import StrictRedis


redis_uri = "redis://localhost:6379/1"
redis = StrictRedis.from_url(redis_uri)


def exp_data(stype="ss", file_name="data.exp.list", max_num=5):
    '''
    导出代理信息
    '''
    if not redis:
        print("无法连接到Redis")
        return 1
    exp_list = []
    if stype == 'all':
        exp_list = ['ss', 'ssr', 'v2ray']
    else:
        exp_list = [stype,]
    
    if os.path.exists(file_name):
        # 文件已经存在，先删除
        os.remove(file_name)
    
    for _stype in exp_list:
        ttable = _stype + "_table"
        stable = _stype + "_working"
        result = redis.hgetall(stable)
        count = 0
        with open(file_name, 'a') as f:
            for key in list(result):
                if count < max_num:
                    count += 1
                    res = redis.hget(ttable, result[key])
                    f.write("{} {} {}\n".format(
                        _stype, result[key].decode(), res.decode()))
                else:
                    break
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser('socks5代理信息导入工具')

    parser.add_argument('-f', '--file', default='data.exp.list',
                        help='设置导出文件路径')
    parser.add_argument('stype', type=str, \
        choices=['ss', 'ssr', 'v2ray', 'all'], help='设置导出代理类型')
    parser.add_argument('-n', '--num', default=5, help='最大提取条数')
    parse_result = parser.parse_args()
    file_name = parse_result.file
    stype = parse_result.stype
    max_num = parse_result.num

    print(stype, file_name)
    exp_data(stype, file_name, max_num)
#

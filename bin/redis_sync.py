#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年06月21日 星期一 23时41分00秒
# Brief:
###############################################################################
import argparse
from redis import StrictRedis


def exp_data(stype, db_uri):
    '''
    导出代理信息
    '''
    redis = StrictRedis.from_url(db_uri)
    if not redis:
        print("无法连接到Redis: ", db_uri)
        return None
    exp_list = []
    if stype == 'all':
        exp_list = ['ss', 'ssr', 'v2ray']
    else:
        exp_list = [stype, ]

    result = {}
    for _stype in exp_list:
        stable = _stype + "_table"
        result[_stype] = redis.hgetall(stable)
        print("stype:", _stype, ", len:", len(result[_stype]))
    return result


def load_data(db_src, table, db_dst):
    '''
    导入代理信息
    '''
    redis_dst = StrictRedis.from_url(db_dst)
    if not redis_dst:
        print("无法连接到Redis:", db_dst)
        return None
    data_src = exp_data("all", db_src)
    if not data_src:
        return None
    for stype in list(data_src):
        stable = stype + "_" + table
        data = data_src[stype]
        for k in list(data):
            v = data[k]
            ret = redis_dst.hset(stable, k, v)
            print("redis ret:", ret, "server:", k.decode(), "detail: ", v.decode())
    return


if __name__ == '__main__':
    parser = argparse.ArgumentParser('socks5代理信息同步工具')

    parser.add_argument('-i', '--src', required=True,  # default='redis://localhost:6379/0',
                        help='设置Redis数据源URI')
    parser.add_argument('-d', '--dst', required=True,  # default='redis://localhost:6379/1',
                        help='设置Redis数据目标URI,格式示例:redis://localhost:6379/0')
    parser.add_argument('-t', '--ttype', default='table',
                        choices=['history', 'table'], help='设置表类型')
    parse_result = parser.parse_args()
    db_src = parse_result.src
    db_dst = parse_result.dst
    ttype = parse_result.ttype

    load_data(db_src, ttype, db_dst)
#

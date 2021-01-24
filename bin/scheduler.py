#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年09月03日 星期四 16时23分56秒
# Brief: 异步任务调度器
###############################################################################

import os
import argparse
import asyncio
import logging
import logging.config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from spider_free_proxy import load_config
from redis import StrictRedis


def load_data(init_file, redis_uri=None):
    '''
    导入代理信息:
        代理格式: proxy_type socket_pair proxy_json_info
        代理示例: ss 1.1.1.1:4 {"server": "1.1.1.1", "password": "xx"}
    '''
    redis = StrictRedis.from_url(redis_uri)
    if not redis:
        print("无法连接到Redis")
        return 1
    with open(init_file) as f:
        datalist = f.readlines()
    for data in datalist:
        _ = data.strip().split(" ", maxsplit=2)
        stable = _[0] + "_table"
        sserver = _[1]
        sdetail = _[2]
        ret = redis.hset(stable, sserver, sdetail)
        print("redis ret:", ret, "server:", sserver, "detail: ", sdetail)


def exec_shell(fn_name):
    '''Shell脚本或命令执行器'''
    return os.system(fn_name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser('代理爬取调度器')
    parser.add_argument('-p', '--proxy', default=6, choices=range(1, 30),
                        help='代理提取器执行周期(单位:分钟)')
    parser.add_argument('-c', '--check', default=30, choices=range(1, 120),
                        help='代理检测器执行周期(单位:分钟),常住内存模式,如果异常退出就启动一下')
    parser.add_argument('-f', '--conf', default='config.ini', help='代理配置文件')
    parser.add_argument('-i', '--init', help='设置初始化倒入代理信息')

    parse_result = parser.parse_args()
    check = parse_result.check
    proxy = parse_result.proxy
    init_file = parse_result.init
    conf_file = parse_result.conf

    config = load_config(conf_file)
    # logging config
    logging.config.fileConfig(config['log_conf'])
    scheduler_log = logging.getLogger('scheduler')

    if init_file:
        # 批量导入代理配置信息
        if not os.path.exists(init_file):
            print(init_file, "doesn't exist!")
            exit(1)
        load_data(init_file, config['redis_uri'])
        exit(0)

    scheduler_log.info(f'scheduler_info: proxy:{proxy}, check:{check}')

    scheduler = AsyncIOScheduler({
        'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': '10'
        },
        'apscheduler.executors.processpool': {
            'type': 'processpool',
            'max_workers': '5'
        },
        'apscheduler.job_defaults.coalesce': 'false',
        'apscheduler.job_defaults.max_instances': '3',
        'apscheduler.timezone': 'UTC',
    },
        logger=scheduler_log
    )
    exec_shell('sh ./start.sh -p all')
    exec_shell('sh ./start.sh -c all')
    # trigger-触发器对象:  interval-间隔时间, date-按日期, cron-根据cron规则
    scheduler.add_job(exec_shell, trigger='interval', minutes=proxy,
                      id='job_getter_001', args=['sh ./start.sh -p all', ])
    scheduler.add_job(exec_shell, trigger='interval', minutes=check,
                      id='job_checker_001', args=['sh ./start.sh -c all', ])

    scheduler.start()
    try:
        # keeps the main thread alive
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年09月03日 星期四 16时23分56秒
# Brief: 异步任务调度器
###############################################################################

import os
import asyncio
import logging
import logging.config
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from spider_free_proxy import spider_proxy
from spider_free_proxy import load_config


def exec_shell(fn_name):
    '''Shell脚本或命令执行器'''
    return os.system(fn_name)


if __name__ == '__main__':

    config = load_config('./config.ini')
    # logging config
    logging.config.fileConfig(config['log_conf'])
    scheduler_log = logging.getLogger('scheduler')

    scheduler = AsyncIOScheduler({
        'apscheduler.executors.default': {
            'class': 'apscheduler.executors.pool:ThreadPoolExecutor',
            'max_workers': '20'
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
    spider = spider_proxy(config=config)
    # trigger-触发器对象:  interval-间隔时间, date-按日期, cron-根据cron规则
    scheduler.add_job(spider.start, trigger='interval', minutes=10,
                      id='job_getter_001', args=['all', ])
    scheduler.add_job(exec_shell, trigger='interval', seconds=120,
                      id='job_checker_001', args=['sh ./start.sh -c all', ])

    scheduler.start()
    try:
        # keeps the main thread alive
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()

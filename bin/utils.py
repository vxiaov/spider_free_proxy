#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年02月05日 星期五 12时16分41秒
# Brief:
###############################################################################
import sys
import logging
import logging.config
import time
import os
import multiprocessing as mp

DEBUG = "DEBUG"
INFO = "INFO"
ERROR = "ERROR"
WARNING = "WARNING"
EXECPTION = "EXECPTION"

def log_exc(log_level: str, _msg: str):
    try:
        raise Exception
    except:
        f = sys.exc_info()[2].tb_frame.f_back
        fmt_prefix = '{}-{}:{}:{}:{}'.format(
            mp.current_process().name, os.getpid(), os.path.basename(
                f.f_code.co_filename), f.f_code.co_name, f.f_lineno)
        return (fmt_prefix, log_level.upper(), _msg)


def log_process(log_queue, log_conf, log_name, sleep_seconds=1):
    '''日志处理模块'''
    # logging config
    logging.config.fileConfig(log_conf)
    logger = logging.getLogger(log_name)
    while True:
        if log_queue.empty():
            log_queue.put(log_exc(DEBUG, "日志队列为空!休息一下！"))
            time.sleep(sleep_seconds)
        else:
            log_prefix, log_level, _msg = log_queue.get()
            str_msg = "{} {} {}".format(log_prefix, log_level, _msg)
            if log_level == INFO:
                logger.info(str_msg)
            elif log_level == DEBUG:
                logger.debug(str_msg)
            elif log_level == ERROR:
                logger.debug(str_msg)
            elif log_level == WARNING:
                logger.warning(str_msg)
            elif log_level == EXECPTION:
                logger.exception(str_msg)


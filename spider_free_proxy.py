#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: xiaoyu0720@gmail.com
# Created Time: 2020年08月29日 星期六 23时50分36秒
# Brief:
###############################################################################
# 无头模式，通过JS屏蔽`webdriver`检测

import json
import base64
import os
import re
import sys
import time
import logging
import logging.config
import socket
import argparse
import signal
import asyncio
import requests
from pyppeteer import launch
from lxml import etree
from urllib.parse import urlparse, parse_qs
from multiprocessing.dummy import Pool as ThreadPool
import multiprocessing as mp
from redis import StrictRedis
import configparser
import traceback


ua = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
js0 = '''() =>{Object.defineProperty(navigator, 'webdriver', {get: () => undefined });}'''


def b64pading(enc):
    '''base64补充等号填充方法'''
    if (len(enc) % 4) != 0:
        enc += '=' * (4 - (len(enc) % 4))
    return enc


def decode_ssr_uri(ssr_uri_string):
    '''
    decode shadowsocksR uri string , format like ssr://aldkfaldkfdlwofdfj...dfa=
    '''
    ssr_prefix = "ssr://"
    ssr_prefix_len = len(ssr_prefix)
    ssr_encode_string = ""
    ssr_decode_string = ""
    conf_json = dict()
    ssr_uri_string = ssr_uri_string.strip()
    if ssr_uri_string.startswith(ssr_prefix):
        ssr_encode_string = ssr_uri_string[ssr_prefix_len:]
    # split different part of params ###
    ssr_split_array = ssr_encode_string.split('_')
    if len(ssr_split_array) == 2:
        i1_ssr = base64.b64decode(b64pading(ssr_split_array[0])).decode()
        i2_ssr = base64.b64decode(b64pading(ssr_split_array[1])).decode()
        if i2_ssr.startswith('obfsparam='):
            ssr_decode_string = "{0}?{1}".format(i1_ssr, i2_ssr)
        else:
            ssr_decode_string = "{0}?obfsparam={1}".format(i1_ssr, i2_ssr)
    else:
        # print('ssr_encode_string:', b64pading(ssr_encode_string).encode())
        ssr_decode_string = base64.b64decode(b64pading(ssr_encode_string)).decode()
    ssr_decode_string = ssr_prefix + ssr_decode_string
    ssr_params = parse_qs(urlparse(ssr_decode_string).query)
    result = urlparse(ssr_decode_string).netloc
    # SSR格式：ssr://server:server_port:method:protocol:obfs:base64-encode-password/?obfsparam=base64-encode-string&protoparam=base64-encode-string&remarks=base64-encode-string&group=base64-encode-string
    # 服务端信息设置
    server_info = result.rsplit(':', maxsplit=5)
    # print(f'result:{result}, server_info:{server_info}')
    server_ip, server_port, protocol, method, obfs, password = server_info[0], server_info[1], server_info[2], server_info[3], server_info[4], base64.b64decode(b64pading(server_info[5])).decode()
    server_port = int(server_port)
    # 参数设置
    for i in ['obfs_param', 'protocol_param']:
        if i in ssr_params:
            conf_json[i] = base64.b64decode(b64pading(ssr_params[i][0])).decode()
        else:
            conf_json[i] = ""
    conf_json['group'] = 'ssr'
    conf_json['server'] = server_ip
    conf_json['server_port'] = server_port
    conf_json['method'] = method
    conf_json['password'] = password
    conf_json['protocol'] = protocol
    conf_json['obfs'] = obfs
    return conf_json


def decode_ss_uri(ss_uri):
    '''
    解析ss_uri , 只返回元组信息,字段位置可能不固定
    params:
        ss_uri : 以 ss://开头的字符串
    '''
    if ss_uri.startswith('ss://'):
        ss_info = base64.b64decode(b64pading(ss_uri[5:])).decode()
        s1 = ss_info.split(':', maxsplit=1)
        s2 = s1[1].rsplit(':', maxsplit=1)
        s3 = s2[0].rsplit('@', maxsplit=1)  # 避免密码中含有特殊的@或:符号
        return (s1[0], s3[0], s3[1], s2[1])


def decode_vmess_uri(vmess_uri):
    '''
    解析vmess_uri
    params:
        vmess_uri : 以 vmess://开头的字符串
    return:
        dict 配置字典 key=[server, server_port, network, path, tls]
    '''
    vmess = {}
    if vmess_uri.startswith('vmess://'):
        dec_info = base64.b64decode(b64pading(vmess_uri[8:])).decode()
        dec_info = json.loads(dec_info)
        # print(dec_info)
        addr = dec_info.get('addr', None)
        if addr is None:
            addr = dec_info.get('add', None)
        if addr is None:
            return None
        vmess['server'] = addr
        vmess['server_port'] = int(dec_info['port'])
        vmess['uid'] = dec_info['id']
        vmess['network'] = dec_info.get('net', "")
        vmess['path'] = dec_info.get('path', "")
        vmess['tls'] = dec_info.get('tls', "")
        return vmess


def load_config(conf_file):
    '''配置文件读取'''
    config = configparser.ConfigParser()
    ret = config.read(conf_file)
    conf = {}
    if len(ret) == 0:
        print(f'config_file:{conf_file} read error!')
        return None
    conf['conf_dir'] = config['socks_client']['conf_dir']
    conf['ss_cmd'] = config['socks_client']['ss_cmd']
    conf['ssr_cmd'] = config['socks_client']['ssr_cmd']
    conf['v2ray_cmd'] = config['socks_client']['v2ray_cmd']
    conf['port_start'] = int(config['socks_client']['port_start'])
    conf['port_num'] = int(config['socks_client']['port_num'])

    conf['v2ray_template'] = config['template']['v2ray_template']
    conf['redis_uri'] = config['database']['redis_uri']

    conf['use_proxy'] = config['proxy']['use_proxy'] or False
    conf['use_proxy'] = True if conf['use_proxy'] == 'True' else False
    conf['proxy'] = config['proxy']['proxy']
    conf['check_url'] = config['check']['check_url']
    conf['max_proc'] = config['check']['max_proc']
    conf['profile'] = config['proxy']['profile']

    conf['log_conf'] = config['logging']['log_conf']
    return conf


class spider_proxy(object):
    '''
    proxy spider: 爬取类型:  ss/ssr/v2ray/socks4/socks5/http
    '''
    def __init__(self, config=None):
        '''设置初始参数'''
        self.stable = {}
        self.rtable = {}
        self.prog = {}
        self.port = {}
        redis_uri = config['redis_uri']
        self.redis = StrictRedis.from_url(redis_uri)
        self.max_num = config['port_num']
        self.port_start = config['port_start']

        # ptype: 直接提供的服务: http/socks4/socks5
        for ptype in ['ss', 'ssr', 'v2ray', 'proxy']:
            self.stable[ptype] = ptype + '_table'
            self.rtable[ptype] = ptype + '_working'
            if ptype == 'ss':
                self.prog[ptype] = config['ss_cmd']
                self.port[ptype] = self.port_start
            elif ptype == 'ssr':
                self.prog[ptype] = config['ssr_cmd']
                self.port[ptype] = self.port_start + self.max_num
            elif ptype == 'v2ray':
                self.prog[ptype] = config['v2ray_cmd']
                self.port[ptype] = self.port_start + self.max_num * 2
        self.check_url = config['check_url']
        self.max_proc = int(config['max_proc'])
        self.timeout = 12  # requests 请求超时时间
        self.headers = {
            'user-agent': 'Mozilla/5.0 (NT; Windows x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36'
        }
        # pyppeteer config
        self.profile = config['profile']
        self.socks_server = config['proxy']
        self.use_proxy = config['use_proxy']
        self.conf_dir = config['conf_dir']
        with open(config['v2ray_template'], 'r') as f:
            self.v2ray_template = json.loads(f.read())

        # logging config
        logging.config.fileConfig(config['log_conf'])
        self.logger = logging.getLogger('proxy')

    def set_ss(self, server, server_port, method, password):
        '''设置ss参数信息'''
        ss = {}
        ss['server'] = server
        ss['server_port'] = int(server_port)
        ss['method'] = method
        ss['password'] = password
        return ss

    def set_v2ray(self, server, server_port, uid, network="", path="", tls=""):
        '''设置ss基本信息'''
        v2ray = {}
        v2ray['server'] = server
        v2ray['server_port'] = int(server_port)
        v2ray['uid'] = uid
        v2ray['network'] = network
        v2ray['path'] = path
        v2ray['tls'] = tls
        return v2ray

    def set_v2ray_conf(self, conf, v2ray_conf):
        conf['inbound']['port'] = int(v2ray_conf['local_port'])
        conf['outbound']['settings']['vnext'][0]['address'] = v2ray_conf['server']
        conf['outbound']['settings']['vnext'][0]['port'] = v2ray_conf['server_port']
        conf['outbound']['settings']['vnext'][0]['users'][0]['id'] = v2ray_conf['uid']
        conf['outbound']['streamSettings']['network'] = v2ray_conf['network']
        conf['outbound']['streamSettings']['wsSettings']['path'] = v2ray_conf['path']
        conf['outbound']['streamSettings']['security'] = v2ray_conf['tls'] if v2ray_conf['tls'] != "" else "none"
        return conf

    def get_cmd(self, ptype, local_port):
        '''获取程序启动命令'''
        conffile = self.conf_dir + str(local_port) + '_' + ptype + '.conf'
        prog = self.prog[ptype]
        if ptype in ['ssr']:
            res = f'{prog} -d -c {conffile}'
        elif ptype in ['ss']:
            res = f'{prog} -c {conffile}'
        elif ptype == 'v2ray':
            res = f'{prog} -c {conffile}'
        return res

    def gen_config(self, params, ptype='ss'):
        '''
        `代理客户端`的配置文件和启动命令的生成
        参数信息:
            params:  dict, 运行程序需要的参数信息
            ptype :  string, ss/ssr/v2ray
        '''
        conf = {}
        conffile = self.conf_dir + str(params['local_port']) + '_' + ptype + '.conf'
        if ptype == 'v2ray':
            conf = self.set_v2ray_conf(self.v2ray_template, params)
        else:
            if ptype in ['ss', 'ssr']:
                conf['server'] = params['server']
                conf['server_port'] = int(params['server_port'])
                conf['local_port'] = int(params['local_port'])
                conf['password'] = params['password']
                conf['method'] = params['method']
                conf['timeout'] = '300'
            if ptype == 'ssr':
                conf['obfs'] = params.get('obfs', "")
                conf['obfs_param'] = params.get('obfs_param', "")
                conf['protocol_param'] = params.get('protocol_param', "")
        with open(conffile, 'w') as f:
            f.write(json.dumps(conf, sort_keys=True, indent=4))

        res = self.get_cmd(ptype=ptype, local_port=params['local_port'])
        if ptype in ['ss', 'v2ray']:
            # v2ray 命令无守护模式
            res = f'nohup {res} >/dev/null 2>&1 &'
        return res

    def check_tcp_connect(self, host):
        '''
        TCP端口连通性检测
        params:
            host : 格式 ip:port
        返回值:
            IP, port , status
            status 为True时表示TCP端口可以连接，但并不代表socks5服务就可用
        '''
        socket.setdefaulttimeout(3)
        addr = host.rsplit(':', maxsplit=1)
        port = addr[1]
        sock = None
        ip = ""
        status = None
        try:
            ip = socket.getaddrinfo(addr[0], None)[0][4][0]
            if ':' in ip:
                inet = socket.AF_INET6
            else:
                inet = socket.AF_INET
            sock = socket.socket(inet)
            status = sock.connect_ex((ip, int(port)))
            sock.close()
        except Exception as e:
            self.logger.warning(f'{host}, exception: {str(e)}')
            if sock:
                sock.close()
            return [addr[0], addr[0], port, False]
        if ip is None:
            ip = addr[0]
        return [addr[0], ip, port, status == 0]

    def check_proxy(self, proxy):
        '''
        代理可用性检测
        params:
            proxy : dict 字典类型
            必要的Key:
                ptype 为代理类型, 可以是: 'http', 'https', 'socks4', 'socks5', 'socks4h', 'socks5h'
                host : 代理地址,格式为 server:server_port
            可选的key:
                timeout: 超时检测时间,默认为`self.timeout`秒
        return:
            True: 有效
            False: 无效
        '''

        ptype = proxy.get('ptype', None)
        host = proxy.get('host', None)
        timeout = proxy.get('timeout', self.timeout)

        if not ptype or not host:
            self.logger.debug(f'传入proxy参数key缺失: ptype={ptype}, host={host}')
            return (host, False)
        if ptype not in ['http', 'https', 'socks4', 'socks5', 'socks4h', 'socks5h']:
            return (host, False)
        proxies = {
            'http': f'{ptype}://{host}',
            'https': f'{ptype}://{host}'
        }
        url = self.check_url
        try:
            resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=timeout)
            if resp.status_code == 200:
                return (host, True)
        except requests.exceptions.ConnectionError:
            self.logger.error(str(e))
        except Exception as e:
            self.logger.exception(str(e))
        return (host, False)

    def check_pool(self, check_func, param_list, maxn=10):
        '''
        检测代理有效性
        params:
            check_func: 检测方法
            param_list: 检测方法的参数的列表
        '''
        pool = ThreadPool(maxn)
        results = []
        try:
            # 多任务处理
            results = pool.map(check_func, param_list)
        except Exception as e:
            print(str(e))
        pool.close()
        pool.join()
        return results

    def start_check_proxy(self):
        '''
        检查远程客户端类型的http/socks5代理可用性
        params:
            ptype: proxy
        '''
        ptype = 'proxy'
        redis = self.redis   # 有效代理{ local_port: server:server_port}
        stable = self.stable[ptype]  # 所有代理信息hash表
        rtable = self.rtable[ptype]  # 运行中的hash表
        # 1.可用性检测-validition
        host_list = [json.loads(_.decode()) for _ in redis.hgetall(stable).values()]
        check_list = [{'host': _['server'] + ':' + _['server_port'], 'ptype': _['ptype']} for _ in host_list]
        self.logger.info(f'开始 {ptype} 代理可用性检测: {stable} len={len(host_list)}')
        check_results = self.check_pool(self.check_proxy, check_list, maxn=self.max_proc)
        # 检测结果: 删除失效端口
        for _ in check_results:
            socks, status = _
            if not status:
                # 代理已失效, 替换端口进程
                sdel = redis.hdel(stable, socks)
                rdel = redis.srem(rtable, socks)
                log_str = f'{socks} invalid, {stable} del: {sdel} , {rtable} del: {rdel}.'
                self.logger.info(log_str)
            else:
                if not redis.sismember(rtable, socks):
                    redis.sadd(rtable, socks)
        return

    def start_check_socks5(self, ptype='ss'):
        '''
        检查socks5代理
        params:
            ptype: ss/ssr
        '''
        ctx = mp.get_context('forkserver')
        redis = self.redis   # 有效代理{ local_port: server:server_port}
        port_num = self.port[ptype]
        stable = self.stable[ptype]  # 所有代理信息hash表
        rtable = self.rtable[ptype]  # 运行中的hash表
        prog = self.prog[ptype]
        # 1.可用性检测-validition
        port_list = [_.decode() for _ in redis.hkeys(rtable)]
        self.logger.info(f'开始 {ptype} 代理TCP握手检测: {rtable} len={len(port_list)}')
        sock_list = ['127.0.0.1:'+str(_) for _ in port_list]
        check_tcp_results = self.check_pool(self.check_tcp_connect, sock_list, maxn=self.max_proc)
        for _ in check_tcp_results:
            orig_ip, ip, port, status = _
            if not status:
                self.logger.debug(f' SERVICE_ERROR, 服务[{ip}:{port}]已经不可访问, 可能服务进程异常终止了.')
                redis.hdel(rtable, port)
        # 检查代理可用性
        port_list = [_.decode() for _ in redis.hkeys(rtable)]
        self.logger.info(f'开始 {ptype} 代理 socks 可用性检测: {rtable} len={len(port_list)}')
        sock_list = [{'host': '127.0.0.1:'+str(_), 'ptype': 'socks5'} for _ in port_list]
        check_socks_results = self.check_pool(self.check_proxy, sock_list, maxn=self.max_proc)
        # 检测结果: 删除失效端口
        for _ in check_socks_results:
            socks, status = _
            local_port = socks.split(':')[1]
            # 已经启动了, 直接检测是否有效代理
            if not status:
                # 代理已失效, 替换端口进程
                server = redis.hget(rtable, local_port)
                server_info = redis.hget(stable, server)
                # kill process
                run_cmd = self.get_cmd(ptype, local_port)
                kill_cmd = f'pkill -f "{run_cmd}"'
                self.logger.debug(kill_cmd)
                os.system(kill_cmd)
                rdel = redis.hdel(rtable, local_port)
                sdel = redis.hdel(stable, server)
                log_str = f'local_port: {local_port} invalid, {stable} del: {sdel} , {rtable} del: {rdel} , server:{server.decode()} ] serverinfo: {server_info.decode()} ]'
                self.logger.info(log_str)
            else:
                if redis.hget(rtable, local_port) is None:
                    '''非当前进程运行的服务,可能中途重启过'''
                    redis.hset(rtable, local_port, 'valid_proxy')

        # 2.可用代理启动-runing
        socks_list = redis.hgetall(stable)
        self.logger.info(f'开始 {ptype} 启动可用代理: {stable} len={len(socks_list)}, port_start:{port_num}, port_num:{self.max_num}')
        proxies = [v.decode() for v in redis.hgetall(rtable).values()]
        using_ports = [v.decode() for v in redis.hgetall(rtable).keys()]
        for _ in list(socks_list):
            socks = json.loads(socks_list[_].decode())
            socks_id = _.decode()
            if socks_id in proxies:
                self.logger.debug(f'{ptype} proxy : {socks_id} 已经运行中.')
                continue
            local_port = -1
            for idx in range(port_num, port_num + self.max_num):
                '''循环找到可用端口'''
                if str(idx) not in using_ports:
                    local_port = idx
                    self.logger.debug(f'找到可用端口:{local_port} , 准备启动服务...')
                    break
            if local_port < 0:
                self.logger.info(f'无可用端口: 当前服务数量: {len(proxies)}')
                break
            socks['local_port'] = local_port
            cmd = self.gen_config(params=socks, ptype=ptype)
            self.logger.debug('运行命令: ' + cmd)

            p = ctx.Process(name=_.decode(), target=os.system(cmd))
            p.start()
            if p:
                time.sleep(0.4)  # 等待服务启动过程 #
                socks = '127.0.0.1:' + str(local_port)
                socks_proxy = {'host': socks, 'ptype': 'socks5'}
                host, status = self.check_proxy(socks_proxy)
                if not status:
                    # kill process
                    run_cmd = self.get_cmd(ptype, local_port)
                    kill_cmd = f'pkill -f "{run_cmd}"'
                    self.logger.debug(kill_cmd)
                    os.system(kill_cmd)
                    sdel = redis.hdel(stable, socks_id)
                    rdel = redis.hdel(rtable, local_port)
                    self.logger.debug(f'新启动代理无效: 端口: {local_port} server: {socks_id}, {stable} delete {sdel} , {rtable} delete {rdel}.')
                else:
                    # 有效代理
                    self.logger.info(f'SUCCESS: 端口: {local_port} 代理运行成功: {socks_id}')
                    redis.hset(rtable, local_port, socks_id)
            else:
                self.logger.error("启动进程返回结果异常!")
        return

    def start_check(self, ptype='ss'):
        '''
        检查所有代理可用性
        params:
            ptype: ss/ssr/v2ray/proxy
        '''
        ptype_list = [ptype, ]
        if ptype == 'all':
            ptype_list = ['ss', 'ssr', 'v2ray', 'proxy']
        while True:
            for ptype in ptype_list:
                if ptype == 'proxy':
                    self.start_check_proxy()
                else:
                    self.start_check_socks5(ptype)
            time.sleep(30)
        return

    def save_to_redis(self, data_list, ptype='ss'):
        '''
        代理信息存储:
        params:
            ptype: ss/ssr/proxy

            proxy : http/https/socks4/socks5
        '''
        if ptype in ['ssr', 'ss', 'v2ray', 'proxy']:
            htable = self.stable[ptype]
        else:
            self.logger.debug(f'invalid ptype:{ptype}')
            return

        total, doer, count, invalid = 0, 0, 0, 0

        pr_list = [ss['server'] + ':' + str(ss['server_port']) for ss in data_list if ss['server'].count(':') == 0]
        pr_dict = {ss['server'] + ':' + str(ss['server_port']): ss for ss in data_list if ss['server'].count(':') == 0}

        results = self.check_pool(self.check_tcp_connect, pr_list, maxn=self.max_num)
        for item in results:
            total += 1
            orig_ip, ip, port, status = item
            if not status:
                invalid += 1
                continue
            k = orig_ip + ':' + port
            v = pr_dict[k]
            k = ip + ':' + port
            v['server'] = ip    # 替换域名, 存储IP地址
            v = json.dumps(v)
            if self.redis.hexists(htable, k):
                doer += 1
                continue
            self.redis.hset(htable, k, v)
            count += 1

        # 入库日志
        self.logger.info(f"redis ptype: {ptype}: total: {total} :loaded: {count} :doer {doer} :invalid {invalid}")
        return True

    async def get_browser(self, headless=True, use_proxy=False, autoClose=True):
        '''获取浏览器页面对象'''
        # browser_args = ['--disable-infobars', '--no-sandbox', '--disable-setuid-sandbox']
        browser_args = ['--disable-infobars']
        if self.use_proxy:
            proxy_server = "--proxy-server=" + config['proxy']
            browser_args.append(proxy_server)
        self.logger.debug(browser_args)
        # headless参数设为False，则变成有头模式
        user_dir = self.profile
        browser = await launch(headless=headless, args=browser_args, logLevel='DEBUG', userDataDir=user_dir, autoClose=autoClose)
        self.logger.debug(browser)
        pages = await browser.pages()
        page = pages[0]
        # 设置页面视图大小
        await page.setViewport(viewport={'width': 1280, 'height': 800})
        await page.setUserAgent(ua)
        await page.evaluateOnNewDocument(js0)
        return page

    async def get_proxy_ss_freess(self, page):
        '''
        SS proxy spider SS_JSON: main_url = "https://free-ss.site/"
        '''
        main_url = "https://free-ss.site/"
        await page.goto(main_url)
        await page.waitForXPath(r'//table[@id="tbss"]/tbody/tr')
        page_text = await page.content()
        # 解析章节列表
        tree = etree.HTML(page_text)
        tr_list = tree.xpath('//table[@id="tbss"]/tbody/tr')

        ss_list = []
        total = 0
        for tr in tr_list:
            total += 1
            item = tr.xpath('./td/text()')
            ss = self.set_ss(item[1], item[2], item[3], item[4])
            ss_list.append(ss)
        # 存储代理信息
        self.save_to_redis(ss_list, ptype='ss')
        return ss_list

    async def get_proxy_ssrtool(self, page):
        '''ssrtool免费分享的SSR'''
        main_url = 'https://ssrtool.us/tool/free_ssr'
        api_url = 'https://ssrtool.us/tool/api/free_ssr?page=1&limit=100'
        await page.goto(main_url, timeout=60*1000)
        await page.waitForXPath(r'//table[@class="layui-table"]/tbody/tr', timeout=60*1000)
        await page.goto(api_url)
        page_text = await page.evaluate('''() =>  {return JSON.parse(document.querySelector("body").innerText);}''')
        data_list = page_text['data']
        ssr_list = []
        ssr_keys = ['server', 'server_port', 'method', 'password', 'protocol', 'obfs', 'obfsparam', 'protocolparam', 'remarks', 'group', 'country']
        for data in data_list:
            conf_json = {}
            for key in ssr_keys:
                conf_json[key] = data[key]
            ssr_list.append(conf_json)
        # 存储代理信息
        self.save_to_redis(ssr_list, ptype='ssr')
        return ssr_list

    async def get_proxy_async(self, ptype='all'):
        '''
        爬取代理任务
        参数信息:
            ptype : ss/ssr/v2ray
        '''
        headless = True if ptype != 'test' else False
        page = await self.get_browser(headless=headless)

        if ptype == 'test':
            print('单元测试')
            await self.get_proxy_ssrtool(page)

        elif ptype in ['ssr', 'all']:
            try:
                await self.get_proxy_ssrtool(page)
            except Exception as e:
                self.logger.exception(str(e))

        elif ptype in ['ss', 'all']:
            await self.get_proxy_ss_freess(page)
        return

    def get_proxy_from_rss_uri(self):
        '''
        免费订阅源: ss/ssr/vmess base64 uri
        功能:
            解析base64 加密的 ss/ssr/vmess 链接信息
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        order_ssr_list = [
            'https://qiaomenzhuanfx.netlify.app/',
            'https://muma16fx.netlify.app/',
            'https://youlianboshi.netlify.app/',
            'https://raw.githubusercontent.com/ssrsub/ssr/master/ssrsub',
            'https://raw.githubusercontent.com/voken100g/AutoSSR/master/online',
            'https://raw.githubusercontent.com/voken100g/AutoSSR/master/recent',
            'http://ss.pythonic.life/subscribe',
            'https://prom-php.herokuapp.com/cloudfra_ssr.txt',
        ]
        ssr_list = []
        ss_list = []
        vmess_list = []
        for main_url in order_ssr_list:
            resp = requests.get(main_url, proxies=proxies, headers=self.headers)
            print(resp.status_code, main_url)
            page_text = base64.b64decode(b64pading(resp.text)).decode()
            data_list = re.split(r'[\r]?\n', page_text)
            for data in data_list:
                try:
                    if data == "":
                        continue
                    if data.startswith('vmess://'):
                        item = decode_vmess_uri(data)
                        vmess_list.append(item)
                    elif data.startswith('ss://'):
                        # method:password@server:server_port
                        s = decode_ss_uri(data)
                        item = self.set_ss(server=s[2], server_port=int(s[3]), method=s[0], password=s[1])
                        ss_list.append(item)
                    elif data.startswith('ssr://'):
                        item = decode_ssr_uri(data)
                        ssr_list.append(item)
                except Exception as e:
                    self.logger.exception(str(e))
                    continue
        # 存储代理信息
        self.save_to_redis(ss_list, ptype='ss')
        self.save_to_redis(ssr_list, ptype='ssr')
        self.save_to_redis(vmess_list, ptype='v2ray')

    def get_proxy_youneedwin(self):
        '''
        免费代理提取: https://www.youneed.win/
        提取类型:
            post_id : 33 - ss
            post_id : 34 - ssr
            post_id : 563 - v2ray
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        url = 'https://www.youneed.win/free-ss'
        url_api = 'https://www.youneed.win/wp-admin/admin-ajax.php'
        headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,ja;q=0.6,zh-TW;q=0.5",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "pragma": "no-cache",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "x-requested-with": "XMLHttpRequest",
            'origin': 'https://www.youneed.win',
            'authority': 'www.youneed.win',
            "referrer": "https://www.youneed.win/free-ss",
            "referrerPolicy": "no-referrer-when-downgrade",
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36',
            "cookie": "__cfduid=d24000263af6c02c996f2d808d246dfe11599039383",
        }
        payload = {
            "action": "validate_input",
            "captcha": "success",
            "nonce": "abb5df4f90",
            "post_id": "33",
            "protection": "",
            "type": "captcha"
        }
        try:
            post_id = {
                'ss': '33',
                'ssr': '34',
                'v2ray': '563',
            }
            # 第一次请求提取nonce信息
            resp = requests.get(url, proxies=proxies, headers=self.headers)
            nonce = re.findall(r'"nonce":"(.*?)","post_id', resp.text)
            self.logger.info(f'{resp.status_code}, {resp.url}')
            if len(nonce) == 0:
                return False
            nonce = nonce[0]
            payload['nonce'] = nonce
            for ptype in ['ss', 'ssr', 'v2ray']:
                payload['post_id'] = post_id[ptype]
                resp = requests.post(url_api, proxies=proxies, headers=headers, data=payload)
                self.logger.info(f'{resp.status_code}, {resp.url}')
                if resp.status_code == 200:
                    ss_data = resp.json().get('content')
                    socks_list = []
                    if ptype == 'ss':
                        re_str = r'<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>'
                        ss_info = re.findall(re_str, ss_data)
                        for ss in ss_info:
                            item = self.set_ss(ss[0], ss[1], ss[3], ss[2])
                            socks_list.append(item)
                    elif ptype == 'ssr':
                        re_str = r'data="(ssr://.*)?"\sherf'
                        ssr_info = re.findall(re_str, ss_data)
                        for ssr in ssr_info:
                            try:
                                item = decode_ssr_uri(ssr)
                                socks_list.append(item)
                            except Exception as e:
                                self.logger.exception(str(e))
                    elif ptype == 'v2ray':
                        re_str = r'<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>\n'\
                            '<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>\n<td align="center">(.*)?</td>'
                        v2ray_info = re.findall(re_str, ss_data)
                        for v2ray in v2ray_info:
                            try:
                                # v2ray参数: server, server_port, uid, network, path, tls
                                item = self.set_v2ray(*v2ray)
                                socks_list.append(item)
                            except Exception as e:
                                self.logger.exception(str(e))
                    self.save_to_redis(socks_list, ptype=ptype)
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_ssr_bitefu(self):
        '''
        免费代理提取: http://tool.bitefu.net/ssr.html
        提取类型:
            ssr
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        url = 'http://tool.bitefu.net/ssr.html'
        try:
            resp = requests.get(url, proxies=proxies, headers=self.headers)
            self.logger.info(f'{resp.status_code}, {resp.url}')
            if resp.status_code == 200:
                ss_data = resp.text
                socks_list = []
                re_str = r'href="(ssr://.*)?">'
                ssr_info = re.findall(re_str, ss_data)
                for ssr in ssr_info:
                    try:
                        item = decode_ssr_uri(ssr)
                        socks_list.append(item)
                    except Exception as e:
                        self.logger.exception(str(e))
                self.save_to_redis(socks_list, ptype='ssr')
            return True
        except Exception as e:
            self.logger.error(str(e))
        return False

    def get_proxy_hugetiny(self):
        '''
        免费代理提取: free proxy https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/READMECN.md
        提取类型:
            ss/ssr/v2ray
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            url = 'https://raw.githubusercontent.com/hugetiny/awesome-vpn/master/READMECN.md'
            resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
            self.logger.info(f'{resp.status_code}, {resp.url}')
            if resp.status_code == 200:
                data = resp.text
                ss_list = re.findall('(?<!vme)(ss://.*)\r?\n?', data)
                ssr_list = re.findall('(ssr://.*)\r?\n?', data)
                vmess_list = re.findall('(vmess://.*)\r?\n?', data)
                proxy_list = []
                for ss in ss_list:
                    # method:password@server:server_port
                    s = decode_ss_uri(ss)
                    item = self.set_ss(server=s[2], server_port=int(s[3]), method=s[0], password=s[1])
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='ss')
                proxy_list = []
                for ssr in ssr_list:
                    item = decode_ssr_uri(ssr)
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='ssr')
                proxy_list = []
                for vmess in vmess_list:
                    item = decode_vmess_uri(vmess)
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='v2ray')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_freefq(self):
        '''
        免费代理提取: free proxy https://github.com/freefq/free
        提取类型:
            ss/ssr/v2ray
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            url = 'https://raw.githubusercontent.com/freefq/free/master/README.md'
            resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
            self.logger.info(f'{resp.status_code}, {resp.url}')
            if resp.status_code == 200:
                data = resp.text
                ss_list = re.findall('(?<!vme)(ss://.*)\r?\n', data)
                ssr_list = re.findall('(ssr://.*)\r?\n', data)
                vmess_list = re.findall('(vmess://.*)\r?\n', data)
                proxy_list = []
                for ss in ss_list:
                    # method:password@server:server_port
                    if ss == '':
                        continue
                    s = decode_ss_uri(ss)
                    item = self.set_ss(server=s[2], server_port=int(s[3]), method=s[0], password=s[1])
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='ss')
                proxy_list = []
                for ssr in ssr_list:
                    if ssr == '':
                        continue
                    item = decode_ssr_uri(ssr)
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='ssr')
                proxy_list = []
                for vmess in vmess_list:
                    if vmess == '':
                        continue
                    item = decode_vmess_uri(vmess)
                    proxy_list.append(item)
                self.save_to_redis(proxy_list, ptype='v2ray')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_from_url(self):
        '''
        Web页面爬取 ss/ssr/v2ray base64 url
        提取类型:
            ss/ssr/v2ray
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            start_urls = [
                'https://view.freev2ray.org',
                'http://tool.bitefu.net/ssr.html',
            ]
            ss_list = []
            ssr_list = []
            v2ray_list = []
            for url in start_urls:
                resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
                self.logger.info(f'{resp.status_code}, {resp.url}')
                if resp.status_code == 200:
                    data = resp.text
                    ss_urls = re.findall('(?<!vme)(ss://.*)\"', data)
                    ssr_urls = re.findall('(ssr://.*)\"', data)
                    vmess_urls = re.findall('(vmess://.*)\"', data)
                    for ss in ss_urls:
                        if ss == '':
                            continue
                        # method:password@server:server_port
                        s = decode_ss_uri(ss)
                        item = self.set_ss(server=s[2], server_port=int(s[3]), method=s[0], password=s[1])
                        ss_list.append(item)
                    for ssr in ssr_urls:
                        if ssr == '':
                            continue
                        item = decode_ssr_uri(ssr)
                        ssr_list.append(item)
                    for vmess in vmess_urls:
                        if vmess == '':
                            continue
                        item = decode_vmess_uri(vmess)
                        v2ray_list.append(item)
                    self.logger.info(f'{resp.url}: ss:{len(ss_list)}, ssr:{len(ssr_list)}, v2ray:{len(v2ray_list)}')
            self.save_to_redis(ss_list, ptype='ss')
            self.save_to_redis(ssr_list, ptype='ssr')
            self.save_to_redis(v2ray_list, ptype='v2ray')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_ss_ssbit(self):
        '''
        SS proxy spider SS_JSON: main_url = "https://trial.ssbit.win/"
        '''
        socks_server = self.socks_server
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        re_host = r'<span id="host.">(.*)?</span>'
        re_port = r'<span id="port.">(.*)?</span>'
        re_pass = r'id="pass.">(.*)?</span>'
        re_method = r'<span id="encrypt.">(.*)?</span>'
        try:
            start_urls = [
                "https://trial.ssbit.win/",
            ]
            for url in start_urls:
                resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=30, verify=False)
                self.logger.info(f'{resp.status_code}, {resp.url}')
                if resp.status_code == 200:
                    page_text = resp.text
                    host_list = re.findall(re_host, page_text)
                    port_list = re.findall(re_port, page_text)
                    pass_list = re.findall(re_pass, page_text)
                    method_list = re.findall(re_method, page_text)
                    ss_list = []
                    for i in range(0, len(host_list)):
                        # server, server_port, method, password
                        ss = self.set_ss(host_list[i], port_list[i], method_list[i], pass_list[i])
                        ss_list.append(ss)
                    # 存储代理信息
                    self.save_to_redis(ss_list, ptype='ss')
        except Exception as e:
            self.logger.exception(str(e))
        return True

    def get_proxy_socks_proxyscrape(self):
        '''
        免费代理提取: free proxy proxyscrape
        提取类型:
            http(s)/socks(4/5)
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            for ptype in ['http', 'socks4', 'socks5']:
                url = f'https://api.proxyscrape.com/?request=getproxies&proxytype={ptype}&timeout=10000&country=all'
                resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
                self.logger.info(f'{resp.status_code}, {resp.url}')
                if resp.status_code == 200:
                    ss_data = resp.text
                    socks_list = []
                    socks_list = ss_data.split('\r\n')
                    proxy_list = []
                    for socks in socks_list:
                        if socks == "":
                            continue
                        item = {}
                        item['ptype'] = ptype
                        item['server'], item['server_port'] = socks.split(':')
                        proxy_list.append(item)
                    self.save_to_redis(proxy_list, ptype='proxy')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_socks_freeproxyworld(self):
        '''
        免费代理提取: free proxy freeproxy.world
        提取类型:
            http(s)/socks(4/5)
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            for ptype in ['http', 'socks4', 'socks5']:
                for page in range(1, 3):
                    url = f'https://www.freeproxy.world/?type={ptype}&anonymity=&country=&speed=&port=&page={page}'
                    resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
                    self.logger.info(f'{resp.status_code}, {resp.url}')
                    if resp.status_code == 200:
                        doc = etree.HTML(resp.text)
                        tr_list = doc.xpath(r'//div[@class="proxy-table"]/table/tbody/tr')
                        socks_list = []
                        for tr in tr_list:
                            ip = tr.xpath('string(./td[1])').strip()
                            port = tr.xpath('string(./td[2])').strip()
                            if port is None or port == "":
                                continue
                            host = re.sub(r'\s+', '', ip+':'+port)
                            socks_list.append(host)
                        proxy_list = []
                        for socks in socks_list:
                            if socks == "":
                                continue
                            item = {}
                            item['ptype'] = ptype
                            item['server'], item['server_port'] = socks.split(':')
                            proxy_list.append(item)
                        self.save_to_redis(proxy_list, ptype='proxy')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy_socks_proxynova(self):
        '''
        免费代理提取: free proxy freeproxy.world
        提取类型:
            http(s)/socks(4/5)
        '''
        socks_server = self.socks_server.replace('socks5:', 'socks5h:')
        proxies = {
            'http': f'{socks_server}',
            'https': f'{socks_server}'
        }
        try:
            for ptype in ['http']:
                url = f'https://www.proxynova.com/proxy-server-list/elite-proxies/'
                resp = requests.get(url, proxies=proxies, headers=self.headers, timeout=self.timeout)
                self.logger.info(f'{resp.status_code}, {resp.url}')
                if resp.status_code == 200:
                    doc = etree.HTML(resp.text)
                    tr_list = doc.xpath(r'//table[@id="tbl_proxy_list"]/tbody/tr')
                    socks_list = []
                    for tr in tr_list:
                        ip = tr.xpath('string(./td[1]/abbr)').strip().replace(r"document.write('", "").replace("');", "")
                        port = tr.xpath('string(./td[2])').strip()
                        if port is None or port == "":
                            continue
                        host = re.sub(r'\s+', '', ip+':'+port)
                        socks_list.append(host)
                    proxy_list = []
                    for socks in socks_list:
                        if socks == "":
                            continue
                        item = {}
                        item['ptype'] = ptype
                        item['server'], item['server_port'] = socks.split(':')
                        proxy_list.append(item)
                    self.save_to_redis(proxy_list, ptype='proxy')
            return True
        except Exception as e:
            self.logger.exception(str(e))
        return False

    def get_proxy(self, ptype='all'):
        '''
        爬取所有代理信息: 包括ss/ssr/v2ray
        '''
        if ptype in ['test']:
            self.get_proxy_from_url()

        if ptype in ['ss', 'all']:
            self.get_proxy_ss_ssbit()

        if ptype in ['ssr', 'all']:
            self.get_proxy_ssr_bitefu()

        if ptype in ['ss', 'ssr', 'v2ray', 'all']:
            self.get_proxy_freefq()
            self.get_proxy_youneedwin()
            self.get_proxy_from_rss_uri()
            self.get_proxy_from_url()

        if ptype in ['proxy', ]:
            self.get_proxy_socks_proxyscrape()
            self.get_proxy_socks_freeproxyworld()
            self.get_proxy_socks_proxynova()
        return

    async def start(self, ptype='all'):
        '''
        执行所有的爬取代理任务
        参数信息:
            ptype : ss/ssr/v2ray/all
        '''
        await self.get_proxy_async(ptype)
        self.get_proxy(ptype)
        return


if __name__ == '__main__':

    parser = argparse.ArgumentParser('代理爬取工具')
    proxy_types = ['all', 'ss', 'ssr', 'v2ray', 'proxy', 'test']

    parser.add_argument('-i', '--init', default='config.ini', help='运行初始化配置文件')
    parser.add_argument('-c', '--check', default=None, choices=proxy_types, help='运行代理可用性检测器')
    parser.add_argument('-r', '--run', default=None, choices=proxy_types, help='运行代理提取器-普通版')
    parser.add_argument('-p', '--proxy', default="all", choices=proxy_types, help='运行代理提取器-异步版')

    parse_result = parser.parse_args()
    init = parse_result.init
    check = parse_result.check
    run = parse_result.run
    proxy = parse_result.proxy

    config = load_config(init)
    if config is None:
        exit(1)
    spider = spider_proxy(config=config)

    if check:
        print("start to check proxy:")
        spider.start_check(ptype=check)

    elif run:
        print("start to get_proxy:")
        spider.get_proxy(run)

    elif proxy:
        print("start to get_proxy_async:", proxy)
        asyncio.get_event_loop().run_until_complete(spider.start(proxy))

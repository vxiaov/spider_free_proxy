#!/usr/bin/env python3
# -*- coding: utf-8 -*-
###############################################################################
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2020年12月21日 星期一 15时10分58秒
# Brief: ss/ssr/v2ray代理URI地址编码解码工具
###############################################################################
import json
import base64
from urllib.parse import urlparse, parse_qs, unquote
import requests

default_port = 1080  # 默认的本地端口
default_url = 'https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/ssr/proxy.txt'


def b64pading(enc):
    '''base64补充等号填充方法'''
    if (len(enc) % 4) != 0:
        enc += '=' * (4 - (len(enc) % 4))
    return enc


def b64encode(data):
    return base64.b64encode(data.encode()).decode()


def get_socks(url=default_url):
    '''提取URL中的代理并解析输出JSON格式'''
    resp = requests.get(url)
    socks_uri = base64.b64decode(resp.text)
    return decode_uri(socks_uri.decode())


def decode_ss_uri(ss_uri):
    '''
    解析ss_uri , 只返回元组信息,字段位置可能不固定
    params:
        ss_uri : 以 ss://开头的字符串
        method:password@server:server_port
    '''
    if ss_uri.startswith('ss://'):
        res = urlparse(unquote(ss_uri))
        netloc = res.netloc.split('@')  # ss://base64string@host:port/?plugin=xxx&obfs=xxx&obfs-host=xxx#备注信息
        plugin = parse_qs(res.query)
        if len(netloc) > 1:
            method, password = base64.b64decode(b64pading(netloc[0])).decode().split(':', maxsplit=1)
            ip, port = netloc[1].split(':')
            port = int(port)
        else:
            ss_uri = base64.b64decode(b64pading(netloc[0])).decode()
            s1 = ss_uri.split(':', maxsplit=1)
            s2 = s1[1].rsplit(':', maxsplit=1)
            s3 = s2[0].rsplit('@', maxsplit=1)  # 避免密码中含有特殊的@或:符号
            method = s1[0]
            password = s3[0]
            ip = s3[1]
            port = int(s2[1])

        conf = {}
        conf['local_port'] = default_port
        conf['server'] = ip
        conf['server_port'] = port
        conf['method'] = method
        conf['password'] = password
        if len(plugin) > 0:
            conf['plugin'] = plugin['plugin'][0]
            conf['obfs'] = plugin['obfs'][0]
            conf['obfs-host'] = plugin['obfs-host'][0]

        return conf


def decode_ssr_uri(ssr_uri_string):
    '''
    decode shadowsocksR uri string , format like ssr://ald...dfa=
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
    # SSR格式：ssr://server:server_port:protocol:method:obfs:base64-encode-password/?obfsparam=base64-encode-string&protoparam=base64-encode-string&remarks=base64-encode-string&group=base64-encode-string
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
    conf_json['local_port'] = default_port
    return conf_json


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


def decode_uri(uri):
    '''解析所有类型URI'''
    # ptype = ""
    conf = {}
    if uri.startswith('ss://'):
        # ptype = 'ss'
        conf = decode_ss_uri(uri)
    elif uri.startswith('ssr://'):
        # ptype = 'ssr'
        conf = decode_ssr_uri(uri)
    elif uri.startswith('vmess://'):
        # ptype = 'v2ray'
        conf = decode_vmess_uri(uri)
    # print(ptype, conf)
    return conf


def encode_ss_uri(data):
    if isinstance(data, str):
        data = json.loads(data)
    if not isinstance(data, dict):
        raise "data type is not a dict"

    # 统一使用 SIP002 URI Scheme格式
    user_info = data['method'] + ':' + data['password']
    ss_uri = 'ss://' + b64encode(user_info) + '@'
    ss_uri += data['server'] + ':' + str(data['server_port'])
    if data.get('plugin'):
        ss_uri += '/?pllugin=' + data['plugin']
        if data.get('obfs'):
            ss_uri += '&obfs=' + data['obfs']
            if data.get('obfs-host'):
                ss_uri += '&obfs-host=' + data['obfs-host']
    else:
        proxy_info = user_info + '@' + data['server'] + ':'
        proxy_info += str(data['server_port'])
        ss_uri = 'ss://' + b64encode(proxy_info)
    return ss_uri


def encode_ssr_uri(data):
    if isinstance(data, str):
        data = json.loads(data)

    # 统一使用 SIP002 URI Scheme格式
    ssr_uri = data['server'] + ':' + str(data['server_port']) + ':'
    ssr_uri += data['protocol'] + ':' + data['method'] + ':' + data['obfs']
    ssr_uri += ':' + b64encode(data['password'])
    if data.get('obfs_param'):
        ssr_uri += '/?obfs_param=' + b64encode(data['obfs_param'])
        if data.get('protocol_param'):
            ssr_uri += '&protocol_param=' + b64encode(data['obfs_param'])
        if data.get('remarks'):
            ssr_uri += '&remarks=' + b64encode(data['remarks'])
        if data.get('group'):
            ssr_uri += '&group=' + b64encode(data['group'])

    ssr_uri = 'ssr://' + b64encode(ssr_uri)
    return ssr_uri


def encode_vmess_uri(data):
    if isinstance(data, str):
        data = json.loads(data)

    vmess_uri = {}
    vmess_uri['add'] = data['server']
    vmess_uri['port'] = data['server_port']
    vmess_uri['aid'] = data.get('aid', 64)
    vmess_uri['id'] = data['uid']
    vmess_uri['net'] = data['network']
    vmess_uri['host'] = data.get('host', "")
    vmess_uri['path'] = data['path']
    vmess_uri['tls'] = data['tls']
    vmess_uri['type'] = data.get('type', 'none')
    vmess_uri['v'] = data.get('v', 2)
    vmess_uri = json.dumps(vmess_uri)
    vmess_uri = 'vmess://' + b64encode(vmess_uri)
    return vmess_uri


def encode_uri(ptype, data):
    if ptype == 'ss':
        uri_str = encode_ss_uri(data)
    elif ptype == 'ssr':
        uri_str = encode_ssr_uri(data)
    elif ptype == 'v2ray':
        uri_str = encode_vmess_uri(data)
    else:
        raise 'invalid proxy type(not ss,ssr,v2ray)'
    return uri_str


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser('ss/ssr/v2ray代理URI编码、解码工具')

    hints = '编码URI信息, 两个参数：代理URI类型 代理字符串, 代理URI类型:ss/ssr/vmess'
    parser.add_argument('-e', '--encode', nargs=2, help=hints)
    parser.add_argument('-d', '--decode', default=None, help='解码URI信息')
    parser.add_argument('-g', '--get', default=default_url, help='获取免费订阅SS代理信息')

    parse_result = parser.parse_args()
    info_enc = parse_result.encode
    info_dec = parse_result.decode
    info_get = parse_result.get

    if info_enc:
        res = encode_uri(*info_enc)
        print(res)
    elif info_dec:
        res = decode_uri(info_dec)
        print(json.dumps(res, indent=4))
    elif info_get:
        res = get_socks(info_get)
        print(json.dumps(res, indent=4))
    else:
        print("无效输入")
        exit(0)

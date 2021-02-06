# SOCKS代理负载均衡

1. SOCKS协议代理客户端: ss/ssr/v2ray
2. 负载均衡实现: haproxy
3. SOCKS协议代理服务端信息爬虫: Python实现

支持平台：
- Linux： Ubuntu/Debian/Raspbian


## 安装
> 自动安装Python3环境、shadowsocks-libev、ssr-native和v2ray客户端工具还会自动安装haproxy实现负载均衡功能。


```sh
git clone https://github.com/learnhard-cn/spider_free_proxy.git
cd spider_free_proxy
sh ./install.sh
```


## 手动启动爬虫服务

```sh
./start.sh -p all		# 使用pyppetter方式使用无头浏览器爬虫
./start.sh -c all		# ss/ssr/v2ray爬虫可用性服务检测与启动管理
```

## ss/ssr/v2ray URI 编码/解码工具
> 个人封装的 代理URI编码/解码方法

```sh
$ ./bin/proxy_uri_util.py -h

usage: ss/ssr/v2ray代理URI编码、解码工具 [-h] [-e ENCODE ENCODE] [-d DECODE]

optional arguments:
  -h, --help            show this help message and exit
  -e ENCODE ENCODE, --encode ENCODE ENCODE
                        编码URI信息, 两个参数：代理URI类型 代理字符串, 代理URI类型:ss/ssr/vmess
  -d DECODE, --decode DECODE
                        解码URI信息

```

## Redis代理数据导入导出工具

```sh
$ ./bin/exp.py -f all.txt ss
$ ./bin/load.py -i all.txt -t table   # 将all.txt中代理信息导入到 xxx_table中,all.txt格式为[type host_info  jsonline_detail_data]
$ ./bin/exp_log.sh ./log/proxy_check.log > all.txt    # 用于解析处理日志中已经删除的历史代理信息，可以作为回收工具。
```


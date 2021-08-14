# SOCKS代理负载均衡

1. SOCKS协议代理客户端: ss/ssr/v2ray
2. 负载均衡实现: haproxy
3. SOCKS协议代理服务端信息爬虫: Python实现


## 安装
> 自动安装Anaconda3环境、shadowsocks-libev、ssr-native和v2ray客户端工具还会自动安装haproxy实现负载均衡功能。


```sh
git clone https://github.com/learnhard-cn/spider_free_proxy.git
cd spider_free_proxy
sh ./install.sh
```

## 配置
> 配置过程主要是创建Python虚拟环境、安装依赖包等工作，另外第一次启动需要使用已有的`socks5`作为基础爬取一些被屏蔽的网站

```sh
sh ./config.sh
```


## 手动启动爬虫服务

```sh
./bin/spider_free_proxy.py -p all  # 使用pyppetter方式使用无头浏览器爬虫
./bin/spider_free_proxy.py -c all  # ss/ssr/v2ray爬虫可用性服务检测与启动管理

# 或者使用start.sh脚本启动

./start.sh -p all   # 启动爬虫任务

./start.sh -c all   # 启动代理服务维护任务
```

## `cron`调度配置
> 使用`crontab`命令配置调度任务的目的可以保证服务一直可用, 但是不是必须做的, 因为我们的`scheduler.py`模块实现了调度管理了. 但是还是做一下配置比较好的.

`crontab -e` 命令打开调度配置, 将下面的内容添加进去, 其中`/path/to/start.sh`是你保存`start.sh`的位置, 需要修改成自己的真是路径:
```
* * * * * sh /path/to/start.sh 'cron' >/dev/null 2>&1
```
之后保存退出即可.

**需要说明的是** , `cron`调度执行的脚本`start.sh`一定要将环境变量文件加载进去(例如`source ~/.bashrc`),否则会因为环境问题而无法调度成功.

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
> 有些代理信息是可以被回收利用的，因此历史代理数据可以通过以下方法进行导入和导出操作。

```sh
$ ./bin/exp.py -f all.txt -t ss       # 将代理信息从Redis数据库中导出

$ ./bin/load.py -i all.txt -t table   # 将all.txt中代理信息导入到Redis数据库中名字为xxx_table的Hash表中,all.txt格式为[type host_info  jsonline_detail_data]

$ ./bin/exp_log.sh ./log/proxy_spider.log > all.txt    # 用于解析处理日志中已经删除的历史代理信息，可以作为回收工具。

$ ./load.sh     # 自动回收日志历史的代理并导入到Redis数据库中

```

---



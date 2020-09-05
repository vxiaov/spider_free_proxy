# SOCKS代理负载均衡

1. SOCKS协议代理客户端: ss/ssr/v2ray
2. 负载均衡实现: haproxy
3. SOCKS协议代理服务端信息爬虫: Python实现


## SOCKS代理客户端安装

### 1.`ss-local`命令安装


`Linux`系统命令安装:
- `Ubuntu`系统： `apt install shadowsocks-libev`
- `CentOS`系统: `yum install shadowsocks-libev`
- `openSUSE`系统: `zypper install shadowsocks-libev`

安装后系统中会增加`ss-local`命令.


验证需要的`ss-local`是否可用

```sh
ss-local --help
```

### 2.`ssr-client`命令安装

因为`ssr`增加了一些加密算法和混淆算法需要使用`libsodium`库,因此需要提前安装一下,以`Ubuntu`安装命令为`apt install libsodium`

命令下载地址 [shadowsocksr-native](https://github.com/ShadowsocksR-Live/shadowsocksr-native)

下载压缩包后,解压会得到`ssr-client`和`ssr-server`两个程序,顾名思义啦, `ssr-client`是我们要使用的客户端命令,而 `ssr-server`是服务端使用的命令(自己搭建服务时就会用到).



#### `ssr-client`能替换`ss-local`么?
`ssr-client`可以兼容`ss-local`,也就是说可以`ssr-client`可以使用`ss-local`的客户端配置文件启动.

**但不是完全兼容**, 由于两款软件开发者众多,开发者精力有限等等原因, 很难完全兼容,所以如果遇到不兼容算法问题还是使用`ss-local`吧,当然如果你想要自己动手那就更好了(前提时你要会编写C程序).

例如 当使用`ssr-client`启动`ss`客户端时遇到`Unknown SSR cipher method "aes-256-gcm"`错误信息时,就只能使用`ss-local`了,因为`ssr-client`不支持此加密算法.


#### `ss-local`与`ssr-client`内存资源比较
我们再来对比一下内存资源占用情况

**第一次启动时内存资源占用情况:**
```
╰─ ps aux|head -1; ps aux|egrep -e 'test_ss[r]?.conf'|grep -v grep
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
tester    14131  0.0  0.0 110340  1220 pts/1    Sl   11:31   0:00 bin/ssr-client -c test_ssr.conf
tester    14205  0.0  0.0  19480  1572 pts/1    S    11:31   0:00 ss-local -c test_ss.conf

```

**当使用SOCKS服务访问一次Web页面后内存资源占用情况:**
```
╰─ ps aux|head -1; ps aux|egrep -e 'test_ss[r]?.conf'|grep -v grep
USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
tester    14131  0.0  0.0 110340  2824 pts/1    Sl   11:31   0:00 bin/ssr-client -c test_ssr.conf
tester    14205  0.0  0.0  19480  3284 pts/1    S    11:31   0:00 ss-local -c test_ss.conf
```

可以看到, `ssr-client`的内存占用比`ss-local`更少一些, 这比`python`版本的`ssr`客户端要更加节省资源.

### 3.`v2ray`命令安装

命令下载地址 [Github分流下载地址](https://github.com/v2ray/dist/) , 也可以阅读官方安装教程 [v2ray命令安装方法](https://www.v2ray.com/chapter_00/install.html)
例如我们使用`Linux`的`64位`系统就下载这个压缩包[v2ray-linux-64.zip](https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip)就可以.

解压后就会得到`v2ray`命令. 测试命令是否可用`./v2ray -h` :

```sh
╰─ ./v2ray -h
Usage of ./v2ray:
  -c value
        Short alias of -config
  -confdir string
        A dir with multiple json config
  -config value
        Config file for V2Ray. Multiple assign is accepted (only json). Latter ones overrides the former ones.
  -format string
        Format of input file. (default "json")
  -test
        Test config file only, without launching V2Ray server.
  -version
        Show current version of V2Ray.
```

## 2.负载均衡实现-haproxy
SOCKS协议代理的负载均衡需要的时传输层的`TCP`协议负载均衡, 而`haproxy`恰好就非常擅长做这件事.

### 安装`haproxy`


`Linux`系统命令安装:
- `Ubuntu`系统： `apt install haproxy`
- `CentOS`系统: `yum install haproxy`
- `openSUSE`系统: `zypper install haproxy`

获取[安装源码文件-Latest LTS version (2.2.2)](https://www.haproxy.org/download/2.2/src/haproxy-2.2.2.tar.gz) , 也可以在`Github`获得最新源码[Github-haproxy源码地址](https://github.com/haproxy/haproxy)

```sh
wget -c https://www.haproxy.org/download/2.2/src/haproxy-2.2.2.tar.gz
tar zxvf haproxy-2.2.2.tar.gz
cd haproxy-2.2.2
make clean
make -j $(nproc) TARGET=linux-glibc USE_OPENSSL=1 USE_ZLIB=1 USE_LUA=1 USE_PCRE=1 USE_SYSTEMD=1 PREFIX=/usr
sudo make install
```

安装好后,检测是否可用`haproxy -v`

```sh
╰─ haproxy -v
HA-Proxy version 2.2.2 2020/07/31 - https://haproxy.org/
Status: long-term supported branch - will stop receiving fixes around Q2 2025.
Known bugs: http://www.haproxy.org/bugs/bugs-2.2.2.html
Running on: Linux 4.12.14-lp151.28.59-default #1 SMP Wed Aug 5 10:58:34 UTC 2020 (337e42e) x86_64
```

### 配置负载均衡策略
> 负载均衡的策略很多,这里使用了`最少连接数`均衡策略, 保证每个服务都分发大致等量的请求连接,随意性较强,不需要同个服务地址分发到同个服务下.

`balance`负载均衡算法如下:
- `roundrobin` : 轮训, 支持动态的`weight`权重设置,每个`backend`最多支持`4095`个服务.
- `static-rr`  : 静态轮训, 根据静态的`weight`权重轮训,每个`backend`无上限服务限制.
- `leastconn`  : 最少连接数, 将连接请求分发到连接数最少的服务上, 推荐适合长连接请求策略,不适合短连接请求策略.
- `first`      : 按第一个可用服务分发请求(按`id`从小到大的顺序), 每个服务达到最大连接数(`maxconn`)后分发给下一个可用服务. 例如 `server server1 127.0.0.1:20000 id=1 maxconn=10`
- `source`     : 按源IP地址hash值分发, 可以保证同一个客户端请求可以分发给同一个server服务(适合具有session会话类服务), 当服务节点变化时,请求分发会重新计算.
- `random`/`random(<draws>)` : 随机分发策略, 使用随机数作为权重值(立即生效), 适合服务节点会动态增加或者缩减情景.当指定`<draws>`参数为大于等于1的数值时,表示在选择这些服务器中负载最少的服务器之前的抽签次数(增加选择公平性),默认为2。
- `hdr(<name>)` : 根据`HTTP协议`Requests请求`headers`中`name`字段分发.
- `rdp-cookie`/`rdp-cookie(<name>)` : 根据`cookie`的`name`字段分发, 同一用户分发到同一个服务.
- `uri` : 根据`uri`实现分发策略
- `url_param` : 根据`HTTP`的`GET`请求参数分发策略.

不多说,直接上配置实例:
```
global
    log /dev/log daemon
    maxconn 32768
    chroot /var/lib/haproxy
    user haproxy
    group haproxy
    daemon
    stats socket /var/lib/haproxy/stats user haproxy group haproxy mode 0640 level operator
    tune.bufsize 32768
    tune.ssl.default-dh-param 2048
    ssl-default-bind-ciphers ALL:!aNULL:!eNULL:!EXPORT:!DES:!3DES:!MD5:!PSK:!RC4:!ADH:!LOW@STRENGTH

defaults
    mode                    tcp
    log                     global
    option                  httplog
    option                  dontlognull
    option                  http-server-close
    option                  redispatch
    retries                 3
    timeout http-request    10s
    timeout queue           1m
    timeout connect         10s
    timeout client          1m
    timeout server          1m
    timeout http-keep-alive 10s
    timeout check           10s
    maxconn                 3000

# HAProxy 前端服务
frontend socks5_frontend
    bind    0.0.0.0:1080
    mode    tcp
    option tcplog
    timeout client  30s
    default_backend socks5_backend

# HAProxy 后端服务节点的负载均衡配置
backend socks5_backend
    mode    tcp
    option log-health-checks
    balance leastconn
    timeout server  30s
    timeout connect 10s
    server  socks5_000 127.0.0.1:20000 check
    server  socks5_001 127.0.0.1:20001 check
    server  socks5_002 127.0.0.1:20002 check
    server  socks5_003 127.0.0.1:20003 check
    server  socks5_004 127.0.0.1:20004 check
    server  socks5_005 127.0.0.1:20005 check
    server  socks5_006 127.0.0.1:20006 check
    server  socks5_007 127.0.0.1:20007 check
    server  socks5_008 127.0.0.1:20008 check
    server  socks5_009 127.0.0.1:20009 check

# HAProxy web ui, 访问地址 : http://localhost:19999/haproxy?stats
listen stats
    bind 0.0.0.0:19999
    mode http
    log global

    maxconn 10
    timeout client 100s
    timeout server 100s
    timeout connect 100s
    timeout queue 100s

    stats enable
    stats uri /haproxy?stats
    stats hide-version
    stats realm HAProxy\ Statistics
    stats admin if TRUE
    stats show-node
END
```

将上面配置内容修改成需要的结果, 然后保存到配置文件存放路径(需要root权限的): `/etc/haproxy/haproxy.cfg`

这样就完成了配置工作.

### 启动`haproxy`服务
> 现在大多数Linux都使用了`systemclt`来管理服务,所以我们也是用它来管理`haproxy`

- 启动进程: `systemclt start haproxy`
- 设置为开机自动启动服务: `systemctl enable haproxy`

### webUI页面查看

我们配置中设置了`19999`端口为管理界面,那么我们直接在浏览器访问 `http://localhost:19999/haproxy?stats` 地址就可以看到服务启动状态了.



## 核心部分-SOCKS代理爬虫服务
> 目前我们啥也没启动呢,只是把流程部署完成, 接下来就要部署代理爬虫服务来自动爬取代理和管理可用的代理服务.

接下来分为如下环节:
1. `Redis`服务安装
2. `Python3`环境依赖安装
3. `cron`调度配置

### 1.`Redis`服务安装

`Linux`系统命令安装:
- `Ubuntu`系统： `apt install redis`
- `CentOS`系统: `yum install redis`
- `openSUSE`系统: `zypper install redis`


当然,这样安装方法最简单, 不需要任何配置即可启动服务了,但是数据默认存放在系统磁盘上是不建议的(自己可设置`data`目录), 因为我们没有大数据量存储到`redis`,所以不调整了.

- 启动`redis`服务: `systemctl start redis`
- 设置开机自启动服务: `systemctl enable redis`

这样`redis`的服务就设置好了, 客户端可以使用命令行`redis-cli`, 或者网上搜索`Another-Redis-Desktop-Manager`UI界面工具.

可用性验证:
```sh
╰─ redis-cli
127.0.0.1:6379> set 'a' 1
OK
127.0.0.1:6379> get 'a'
"1"
```

接下来开始部署`python`服务了.

### 2.`Python3`环境依赖安装
建议使用虚拟环境来安装依赖, 比如使用`Anaconda3`安装`Python`环境,可以使用`conda`管理虚拟环境
我们以创建虚拟环境名为`proxy`为例

1. 创建虚拟环境: `conda create -n proxy python=3.8`
2. 切换进入虚拟环境: `conda activate proxy`
3. 安装依赖包: `pip install -r requirements.txt`
4. 修改配置文件`config.ini` , 这里包含可以修改的配置信息, 例如爬虫是否使用代理(防止网址被屏蔽问题,如果有最好配置上),如果没有可以设置`use_proxy = False`

当我们配置的`haproxy`可用时,我们最好把`use_proxy`配置上,这样可以访问更多地址.

#### 手动启动爬虫服务

```sh
./spider_free_proxy.py -p 'all'  # 使用pyppetter方式使用无头浏览器爬虫
./spider_free_proxy.py -r 'all'  # 使用`requests`方式爬虫
./spider_free_proxy.py -c 'all'  # ss/ssr/v2ray爬虫可用性服务检测与启动管理
./spider_free_proxy.py -c 'proxy' # http/socks4/socks5 代理可用性检测(远程直接提供代理服务功能)

```

### 3.`cron`调度配置
> 使用`crontab`命令配置调度任务的目的可以保证服务一直可用, 但是不是必须做的, 因为我们的`scheduler.py`模块实现了调度管理了. 但是还是做一下配置比较好的.

`crontab -e` 命令打开调度配置, 将下面的内容添加进去, 其中`/path/to/start.sh`是你保存`start.sh`的位置, 需要修改成自己的真是路径:
```
* * * * * sh /path/to/start.sh 'cron' >/dev/null 2>&1
```
之后保存退出即可.

**需要说明的是** , `cron`调度执行的脚本`start.sh`一定要将环境变量文件加载进去(例如`source ~/.bashrc`),否则会因为环境问题而无法调度成功.


#!/bin/bash
########################################################################
# File Name: install.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年01月15日 星期五 13时53分49秒
# 安装依赖软件：shadowsocks-libev/ssr-native/v2ray  + haproxy + redis-server
########################################################################

. ~/.bashrc

os_type=""  # Linux操作系统分支类型
pac_cmd=""  # 包管理命令
pac_cmd_install=""  # 包管理命令
pac_cmd_update=""   # 软件源缓存更新
cpu_arc=""  # CPU架构类型，仅支持x86_64
tmpdir="/tmp/proxy"
ssr_ver="0.9.0"     # ssr-native 版本号
basic_package="unzip wget "

check_sys() {
    if [ -f /etc/os-release ] ; then
        . /etc/os-release
        case "$ID" in
            centos)
                os_type="$ID"
                pac_cmd="yum"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                basic_package="$basic_package libxml2-devel libxslt-devel"
                ;;
            opensuse*)
                os_type="$ID"
                pac_cmd="zypper"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                basic_package="$basic_package libxml2-devel libxslt-devel"
                ;;
            ubuntu|debian|raspbian)
                os_type="$ID"
                pac_cmd="apt-get"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                basic_package="$basic_package libxml2-dev libxslt1-dev"
                ;;
            manjaro|arch*)
                os_type="$ID"
                pac_cmd="pacman"
                pac_cmd_update="$pac_cmd -Sy"
                pac_cmd_install="$pac_cmd -S --needed --noconfirm "
                basic_package="$basic_package libxml2-dev libxslt1-dev"
                ;;
            *)
                os_type="unknown"
                pac_cmd=""
                pac_cmd_install=""
                ;;
        esac
    fi
    if [ -z "$pac_cmd" ] ; then
        exit 1
    fi
    cpu_arc="`uname -m`"
    if [ "$cpu_arc" != "x86_64" -a "$cpu_arc" != "armv7l" ] ; then
        echo "仅支持 X86_64及 armv7l 系统架构类型，不支持当前架构类型:[$cpu_arc]"
        exit 2
    fi
    return 0
}

compile_simple_obfs(){
    echo "开始编译 simple-obfs 源码安装!"
    sudo ${pac_cmd_install} --no-install-recommends build-essential autoconf libtool libssl-dev libpcre3-dev libev-dev asciidoc xmlto automake git
    git clone --depth=1 --shallow-submodules https://github.com/shadowsocks/simple-obfs.git
    cd simple-obfs
    git submodule update --init --recursive && ./autogen.sh  && ./configure && make && sudo make install
    echo "编译安装 simple-obfs 完成！"
    cd ../
}


## 1. 安装客户端命令
install_ss(){
    sudo ${pac_cmd_install} shadowsocks-libev
    if which ss-local >/dev/null
    then
        echo "测试结果： ss-local 命令可用，安装 shadowsocks-libev 成功。"
    else
        echo "测试结果：找不到 ss-local 命令， 安装 ss-local 失败！" 
    fi

    if which obfs-local >/dev/null ; then
        echo "obfs-local 命令已经安装成功。"
        return 0
    else
        echo "找不到 obfs-local 命令， 开始安装 obfs-local："
    fi

    sudo ${pac_cmd_install} simple-obfs
    [[ "$?" = "0" ]] || compile_simple_obfs
    if which obfs-local >/dev/null ; then
        echo "测试结果： obfs-local 命令可用，安装 simple-obfs 成功。"
    else
        echo "测试结果：找不到 obfs-local 命令， 安装 obfs-local 失败！"
    fi
}

compile_ssr_native(){
    echo "开始编译 ssr-client 源代码！ 编译过程依据网络差异会需要持续一段时间(5分钟内)，请耐心等待..."
    sudo ${pac_cmd_install} --no-install-recommends build-essential autoconf libtool asciidoc xmlto
    sudo ${pac_cmd_install} git gcc g++ gdb cmake automake
    
    if [ ! -r "$ssr-n" ] ; then
        git clone https://github.com/ShadowsocksR-Live/shadowsocksr-native.git
        mv shadowsocksr-native ssr-n
    fi
    cd ssr-n
    git submodule update --init
    git submodule foreach -q 'git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo master)'

    # build ShadowsocksR-native
    mkdir -p build
    cd build && cmake .. && make && sudo cp -f src/ssr-* /usr/bin && cd ../
    cd ../
    echo "编译安装完成"
}

install_ssr(){
    which ssr-client >/dev/null && echo "ssr-client 已经安装成功了！" && return 0 
    
    if [ "$os_type" = "raspbian" ] ; then
        compile_ssr_native
    elif [ ! -f ssr-native-linux-x64.zip ] ; then
        wget -c https://github.com/ShadowsocksR-Live/shadowsocksr-native/releases/download/${ssr_ver}/ssr-native-linux-x64.zip
        unzip -o -d ${tmpdir} ssr-native-linux-x64.zip
        sudo cp -pf ${tmpdir}/ssr-client /usr/bin/
    fi
    if which ssr-client >/dev/null ; then
        echo "验证结果： 安装成功！ 找到了 `which ssr-client` 命令！"
    else
        echo "验证结果：安装失败！ 找不到 ssr-client 命令!"
    fi
}

install_v2ray(){
    which v2ray >/dev/null && echo "v2ray 已经安装成功了!" && return 0

    if [ "$os_type" = "raspbian" ] ; then
        if [ ! -f v2ray-linux-arm32-v7a.zip ] ; then
            wget -c https://github.com/v2fly/v2ray-core/releases/download/v4.31.0/v2ray-linux-arm32-v7a.zip
        fi
        unzip -o -d ${tmpdir} v2ray-linux-arm32-v7a.zip
    elif [ ! -f v2ray-linux-64.zip ] ; then
        wget -c https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip
        unzip -o -d ${tmpdir} v2ray-linux-64.zip
    fi
    sudo cp -p ${tmpdir}/v2ray /usr/bin
    sudo cp -p ${tmpdir}/v2ctl /usr/bin
    sudo cp -p ${tmpdir}/geo*.dat /usr/bin
}

install_haproxy(){
    sudo ${pac_cmd_install} haproxy
}

config_haproxy(){

    dest_file="/etc/haproxy/haproxy.cfg"
    if [ -f $dest_file ]; then
        sudo cp -p $dest_file $dest_file.`date +%Y%m%d%H%M%S`
    fi

    # generate socks5 server list info
    server_list_info=`awk 'BEGIN{for(i=0;i<=200;i++)printf("\tserver  socks5_%03d 127.0.0.1:%d check\n", i, 20000+i); }'`

    cat <<END | sudo tee $dest_file
global
    log /dev/log daemon
    maxconn 32768
    chroot /var/lib/haproxy
    user haproxy
    group haproxy
    daemon
    tune.bufsize 32768
    tune.ssl.default-dh-param 2048
    ssl-default-bind-ciphers ALL:!aNULL:!eNULL:!EXPORT:!DES:!3DES:!MD5:!PSK:!RC4:!ADH:!LOW@STRENGTH

    stats socket /var/lib/haproxy/stats user haproxy group haproxy mode 0640 level operator
    stats socket ipv4@127.0.0.1:9999 level admin
    stats socket /var/lib/haproxy/stats mode 0640 level admin
    stats timeout 2m

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
    bind    0.0.0.0:1084
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
${server_list_info}

# HAProxy web ui: http://localhost:19999/haproxy?stats
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

}

# start haproxy
start_haproxy(){
    echo "start haproxy..."
    sudo systemctl enable haproxy
    sudo systemctl start haproxy
    echo "---------------------------------------------------------"
    echo "    default webUI url: http://localhost:19999/haproxy?stats"
    echo "---------------------------------------------------------"
}

install_redis(){
    which redis-server >/dev/null && ( echo "redis 已经安装成功！不需要再安装了！" ; return 0; )
    sudo ${pac_cmd_install} redis-server
    which redis-server >/dev/null || ( echo "redis 安装失败！" ; return 1; )
    echo "redis-server 安装成功！"
}

start_redis(){
    echo "start redis..."
    sudo systemctl enable redis
    sudo systemctl start redis
    echo "---------------------------------------------------------"
    echo "  Redis 服务已启动！ 可以使用 redis-cli 命令连接测试 "
    echo "---------------------------------------------------------"
}

# 配置代理爬虫环境，初始化运行
config_spider(){
    py_ver=`python3 -V | awk '{ print $2 }' | sed 's/\.//g'`
    if [ "$py_ver" -lt "360" ] ; then
        echo "Python 版本低于3.6.0，请升级！"
        p_ver='3.9.1'
        wget -c https://www.python.org/ftp/python/${p_ver}/Python-${p_ver}.tgz
        tar zxvf Python-${p_ver}.tgz
        cd Python-${p_ver}/ && ./configure --enable-optimizations --with-lto && make -j$(nproc) && sudo make install && cd ../
        export PATH=/usr/local/bin:$PATH
    fi
    
    sudo pip3 install -r requirements.txt
    # 设置工作目录
    wkdir=`pwd`
    cp start.template.sh start.sh
    sed -i "s#^workdir=.*#workdir=${wkdir}#g" start.sh
    for tmpdir in "running" "log"
    do
        if [ ! -r $tmpdir ] ; then
            mkdir $tmpdir
        fi
    done
    
    # 第一次启动一个默认代理
    order_url="https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/data.exp.list"
    conf_file="./conf/default_ssr.conf"
    exp_file="exp.list"
    wget -O $exp_file ${order_url}
    python3 ./bin/load.py -i $exp_file -t table     # 导入有效代理列表

    echo "开始启动代理检测服务"
    ./start.sh -c all   # 第一次验证有效并启动有效代理
    echo "等待服务启动"
    sleep 5

    echo "开始启动代理爬虫服务"
    ./start.sh -p all   # 第一次爬取代理
}

# 主要安装步骤
main(){

    sudo $pac_cmd_update
    sudo ${pac_cmd_install} ${basic_package}
    install_ss
    install_ssr
    install_v2ray

    install_haproxy
    config_haproxy
    start_haproxy

    install_redis
    start_redis

    config_spider
}


# 检测系统类型
check_sys
main
# ~END~
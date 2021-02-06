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


check_sys() {
    if [ -f /etc/os-release ] ; then
        . /etc/os-release
        case "$ID" in
            centos)
                os_type="$ID"
                pac_cmd="yum"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                ;;
            opensuse*)
                os_type="$ID"
                pac_cmd="zypper"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                ;;
            ubuntu|debian|raspbian)
                os_type="$ID"
                pac_cmd="apt-get"
                pac_cmd_update="$pac_cmd update -y"
                pac_cmd_install="$pac_cmd install -y"
                ;;
            manjaro|arch*)
                os_type="$ID"
                pac_cmd="pacman"
                pac_cmd_update="$pac_cmd -Sy"
                pac_cmd_install="$pac_cmd -S --needed --noconfirm "
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
    git clone -–depth=1 --shallow-submodules https://github.com/shadowsocks/simple-obfs.git
    cd simple-obfs
    git submodule update --init --recursive
    ./autogen.sh
    ./configure && make
    sudo make install
    echo "编译安装 simple-obfs 完成！"

}


## 1. 安装客户端命令
install_ss(){
    sudo ${pac_cmd_install} shadowsocks-libev
    [[ "$?" = "0" ]] || echo "安装 shadowsocks-libev 失败！请手动安装。"
    which ss-local >/dev/null  && { echo "测试结果：找不到 ss-local 命令， 安装 ss-local 失败！" ; return 1 }
    echo "测试结果： ss-local 命令可用，安装 shadowsocks-libev 成功。"

    sudo ${pac_cmd_install} simple-obfs
    [[ "$?" = "0" ]] || { echo "安装 simple-obfs 失败！" &&  compile_simple_obfs }
    which obfs-local >/dev/null  && { echo "测试结果：找不到 obfs-local 命令， 安装 obfs-local 失败！" ; return 1 }
    echo "测试结果： obfs-local 命令可用，安装 simple-obfs 成功。"
}

compile_ssr_native(){
    echo "开始编译 ssr-client 源代码！ 编译过程依据网络差异会需要持续一段时间(5分钟内)，请耐心等待..."
    sudo ${pac_cmd_install} --no-install-recommends build-essential autoconf libtool asciidoc xmlto
    sudo ${pac_cmd_install} git gcc g++ gdb cmake automake
    git clone https://github.com/ShadowsocksR-Live/shadowsocksr-native.git
    mv shadowsocksr-native ssr-n  # rename shadowsocksr-native to ssr-n
    cd ssr-n                      # enter ssr-n directory. 
    git submodule update --init
    git submodule foreach -q 'git checkout $(git config -f $toplevel/.gitmodules submodule.$name.branch || echo master)'

    # build ShadowsocksR-native
    mkdir build && cd build
    cmake .. && make
    sudo cp -f src/ssr-* /usr/bin
    echo "编译安装完成"
}

install_ssr(){
    which ssr-client >/dev/null && { echo "ssr-client 已经安装成功了！"; return 0; }
    
    if [ "$os_type" = "raspbian" ] ; then
        compile_ssr_native
    elif [ ! -f ssr-native-linux-x64.zip ] ; then
        wget -c https://github.com/ShadowsocksR-Live/shadowsocksr-native/releases/download/${ssr_ver}/ssr-native-linux-x64.zip
        unzip -o -d ${tmpdir} ssr-native-linux-x64.zip
        sudo cp -pf ${tmpdir}/ssr-client /usr/bin/
    fi
    which ssr-client >/dev/null || { echo "验证结果：安装失败！ 找不到 ssr-client 命令!" ;  return 1 ; }
    echo "验证结果： 安装成功！ 找到了 `which ssr-client` 命令！"
}

install_v2ray(){
    which v2ray >/dev/null && { echo "v2ray 已经安装成功了!" ; return 0; }

    if [ ! -f v2ray-linux-64.zip ] ; then
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
    # Config DNS nameserver
    if ! grep -q "8.8.8.8" /etc/resolv.conf; then
        sudo cp -p /etc/resolv.conf /etc/resolv.conf.bak
        sudo echo "nameserver 8.8.8.8" > /etc/resolv.conf
        sudo echo "nameserver 8.8.4.4" >> /etc/resolv.conf
    fi

    dest_file="/etc/haproxy/haproxy.cfg"
    if [ -f $dest_file ]; then
        sudo cp -p $dest_file $dest_file.`date +%Y%m%d%H%M%S`
    fi

    # generate socks5 server list info
    server_list_info=`awk 'BEGIN{for(i=0;i<=150;i++)printf("\tserver  socks5_%03d 127.0.0.1:%d check\n", i, 20000+i); }'`

    haproxy_cfg="conf/haproxy.cfg.template"
    if [ ! -f "$haproxy_cfg" ] ; then
        echo "配置文件模板 [$haproxy_cfg] 找不到！"
        return 1
    fi
    sudo sed -np "s#$server_list_info#{server_list_info}#g" ${haproxy_cfg} > /etc/haproxy/haproxy.cfg
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
    which redis-server >/dev/null && { echo "redis 已经安装成功！不需要再安装了！" ; return 0; }
    sudo ${pac_cmd_install} redis-server
    which redis-server >/dev/null || { echo "redis 安装失败！" ; return 1; }
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
    sudo pip3 install -r requirements.txt
    # 设置工作目录
    wkdir=`pwd`
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
    sudo ${pac_cmd_install} unzip wget
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
#!/bin/bash
########################################################################
# File Name: install.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年01月15日 星期五 13时53分49秒
########################################################################

. ~/.bashrc

os_type=""  # Linux操作系统分支类型
pac_cmd=""  # 包管理命令
pac_cmd_ins=""  # 包管理命令
cpu_arc=""  # CPU架构类型，仅支持x86_64

check_sys() {
	if [ -f /etc/os-release ] ; then
		. /etc/os-release
		case "$ID" in
			centos)
				os_type="$ID"
				pac_cmd="yum"
				pac_cmd_ins="$pac_cmd install -y"
				;;
			opensuse*)
				os_type="$ID"
				pac_cmd="zypper"
				pac_cmd_ins="$pac_cmd install -y"
				;;
			ubuntu|debian)
				os_type="$ID"
				pac_cmd="apt-get"
				pac_cmd_ins="$pac_cmd install -y"
				;;
			manjaro|arch*)
				os_type="$ID"
				pac_cmd="pacman"
				pac_cmd_ins="$pac_cmd -S "
				;;
			*)
				os_type="unknown"
				pac_cmd=""
				pac_cmd_ins=""
				;;
		esac
	fi
	if [ -z "$pac_cmd" ] ; then
		return 1
	fi
	cpu_arc="`uname -m`"
	if [ "$cpu_arc" != "x86_64" ] ; then
		echo "invalid cpu arch:[$cpu_arc]"
		return 2
	fi
	return 0
}


tmpdir="/tmp/proxy"

## 1. 安装客户端命令
install_ss(){
	${pac_cmd_ins} shadowsocks-libev  simple-obfs
}


install_ssr()
{
	if [ ! -f ssr-native-linux-x64.zip ] ; then
		ver="0.9.0"
		wget -c https://github.com/ShadowsocksR-Live/shadowsocksr-native/releases/download/${ver}/ssr-native-linux-x64.zip
	fi
	unzip -o -d ${tmpdir} ssr-native-linux-x64.zip
	cp -p ./bin/ssr-client /usr/bin/
}

install_v2ray()
{
	if [ ! -f v2ray-linux-64.zip ] ; then
		wget -c https://github.com/v2ray/dist/raw/master/v2ray-linux-64.zip
	fi
	unzip -o -d ${tmpdir} v2ray-linux-64.zip
	cp -p ${tmpdir}/v2* /usr/bin
	cp -p ${tmpdir}/geo*.dat /usr/bin
}

install_haproxy(){
	${pac_cmd_ins} haproxy
}

compile_haproxy(){
	wget -c https://www.haproxy.org/download/2.2/src/haproxy-2.2.2.tar.gz
	tar zxvf haproxy-2.2.2.tar.gz
	cd haproxy-2.2.2
	make clean
	make -j $(nproc) TARGET=linux-glibc USE_OPENSSL=1 USE_ZLIB=1 USE_LUA=1 USE_PCRE=1 USE_SYSTEMD=1 PREFIX=/usr
	sudo make install
}


config_haproxy()
{
	# Config DNS nameserver
	if ! grep -q "8.8.8.8" /etc/resolv.conf; then
		cp -p /etc/resolv.conf /etc/resolv.conf.bak
		echo "nameserver 8.8.8.8" > /etc/resolv.conf
		echo "nameserver 8.8.4.4" >> /etc/resolv.conf
	fi

	if [ -f /etc/haproxy/haproxy.cfg ]; then
		cp -p /etc/haproxy/haproxy.cfg /etc/haproxy/haproxy.cfg.bak
	fi

	# generate socks5 server list info
	server_list_info=`awk 'BEGIN{for(i=0;i<=200;i++)printf("\tserver  socks5_%03d 127.0.0.1:%d check\n", i, 20000+i); }'`

	cat > /etc/haproxy/haproxy.cfg <<EOF
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
	# server  socks5_000 127.0.0.1:20000 check
	# server  socks5_001 127.0.0.1:20001 check
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

EOF
}


# start haproxy
start_haproxy()
{
	echo "start haproxy..."
	systemctl enable haproxy
	systemctl start haproxy
	echo "---------------------------------------------------------"
	echo "	default webUI url: http://localhost:19999/haproxy?stats"
	echo "---------------------------------------------------------"
}

install_redis(){
	${pac_cmd_ins} redis
}

start_redis()
{
	echo "start redis..."
	systemctl enable redis
	systemctl start redis
}

install_anaconda()
{
	# install anaconda python environment
	echo "downloading Anaconda3... file size : 500MB+"
	wget -c https://repo.anaconda.com/archive/Anaconda3-2020.11-Linux-x86_64.sh
	echo "installing Anaconda3...(default to /opt/anaconda3)"
	sh Anaconda3-2020.11-Linux-x86_64.sh -p /opt/anaconda3 -b
}

config_python_venv(){
	venv_name="spider"
	export PATH=/opt/anaconda3/bin:/opt/anaconda3/condabin:$PATH
	# conda create -yn $venv_name python=3.8
	conda init bash
	conda activate $venv_name
	# git clone https://github.com/learnhard-cn/spider_free_proxy.git
	# cd spider_free_proxy
	pip install -r requirements.txt
	echo "start to fetch socks5 proxy ... cmd :[python3 ./spider_free_proxy.py -p 'all']"
	python3 ./bin/spider_free_proxy.py --init ./conf/config.ini -p 'all'   # 使用pyppetter方式使用无头浏览器爬虫,对于无桌面环境用户，第一次运行可能会出现浏览器无法启动情况，这是由于系统缺少浏览器运行的依赖库，可以手动执行浏览器命令看报错缺少的库信息，然后逐个安装上就可以解决。
	echo "start to check valid socks5 proxy ... cmd :[python3 ./spider_free_proxy.py -c 'all']"
	python3 ./bin/spider_free_proxy.py --init ./conf/config.ini -c 'all'   # checking ss/ssr/v2ray
	
	# 设置工作目录
	sed -i "s/^workdir=.*/workdir=`pwd`/" start.sh
	sed -i "s/^venv_name=.*/venv_name=${venv_name}/" start.sh
	# 添加调度任务
	echo "----------------------------------------------------------"
	echo "You may need to add this job to crontab:"
	echo "*/5 * * * * sh `pwd`/start.sh 'cron' >/dev/null 2>&1"
	echo "----------------------------------------------------------"

}

# main process


if [ "$?" != "0" ] ; then
	echo "Unsupport system type"
	exit 0
fi

if [ "`id -u`" != "0" ] ; then
	echo "root user needed!"
	echo "you can add 'sudo ' command to the begining of the running command."
	echo "or use root use to run it"
	exit 0
fi

if [ `which unzip` != "0" ] ; then
	${pac_cmd_ins} unzip
fi

if [ `which wget` != "0" ] ; then
	${pac_cmd_ins} wget
fi

check_sys

main(){
	install_ss
	install_ssr
	install_v2ray

	install_haproxy
	config_haproxy
	start_haproxy

	install_redis
	start_redis
	install_anaconda
	config_python_venv
}


# main
#

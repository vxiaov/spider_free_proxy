#!/usr/bin/env bash
########################################################################
# File Name: config.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年01月15日 星期五 21时53分18秒
########################################################################


get_first_socks5()
{
	curl https://raw.githubusercontent.com/learnhard-cn/free_proxy_ss/main/ss/proxy.txt | base64 -d 
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


# 初始化创建目录#
for tmpdir in "running" "chrome_profile" "log"
do
	if [ ! -r $tmpdir ] ; then
		mkdir $tmpdir
	fi
done

config_python_venv


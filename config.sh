#!/usr/bin/env bash
########################################################################
# File Name: config.sh
# Author: zioer
# mail: next4nextjob@gmail.com
# Created Time: 2021年01月15日 星期五 21时53分18秒
########################################################################


init_socks5()
{
    conf_file="./conf/default_ssr.conf"
    python3 ./bin/proxy_uri_util.py  > ${conf_file}
    ssr-client -d -c ${conf_file}
}



config_python_venv(){
    venv_name="spider"
    install_path="/opt/anaconda3"

    . ${install_path}/etc/profile.d/conda.sh

    conda env list| grep ${venv_name} >/dev/null
    if [ "$?" = "0" ] ; then
        echo "env [$venv_name] is already created!"
    else
        conda create -yn $venv_name python=3.8
        conda init bash
    fi

    conda activate $venv_name
    pip install -r requirements.txt

    # 设置工作目录
    wkdir=`pwd`
    sed -i "s/^workdir=.*/workdir=${wkdir}/g" start.sh
    sed -i "s/^venv_name=.*/venv_name=${venv_name}/g" start.sh
    sed -i "s/1084/1080/g" ./conf/config.ini   # 修改默认代理为临时的1080端口代理

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

init_socks5

echo "1080端口代理可用性检测(可用时才可以正常运行爬虫爬取免费代理):"
curl -x socks5://127.0.0.1:1080 https://httpbin.org/ip
if [ "$?" = "0" ] ; then
    ./start.sh -p all   # 第一次爬取代理
    ./start.sh -c all   # 第一次验证有效并启动有效代理(有效代理启动后，就可以替换回1084端口了)
    sed -i "s/1080/1084/" ./conf/config.ini   # 修改代理端口为haproxy代理端口
else
    echo "临时代理1080端口不可用，请更换一个可用代理再进行手工启动"
fi



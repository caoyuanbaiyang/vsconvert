#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/1/10 16:08
# @Author  : TYQ
# @File    : vsconvert.py
# @Software: win10 python3
import logging
import shutil

from lib.readcfg import ReadCfg
from lib.Logger import logger
import os
import importlib

log_file = "syslog.log"
groups_file = "config/groups.yaml"
action_file = "config/action.yaml"


class VsConvert(object):
    def __init__(self, filepath=None):
        self.mylog = logger(log_file, logging.INFO, logging.INFO)
        if os.path.exists(groups_file):
            self.groups = ReadCfg().readcfg(groups_file)
        else:
            self.groups = {}
        if filepath is None:
            self.action_cfg = ReadCfg().readcfg(action_file)
        else:
            self.action_cfg = ReadCfg().readcfg(filepath)

    def __get_host_name(self, hostsnames):
        # hostsnames 可以是列表，可以是ALL，可以是具体主机名
        # 还可以是组名
        rt_hostnames = []
        if isinstance(hostsnames, list):
            # hosts.yaml 中部分主机 或 groups.yaml中指定的组
            for host in hostsnames:
                if host in self.groups:
                    # host 是组，需要获取组员
                    if isinstance(self.groups[host], dict):
                        # 嵌套组
                        if "children" not in self.groups[host]:
                            self.mylog.cri("嵌套组配置错误，必须有children关键字")
                            raise Exception("嵌套组配置错误，必须有children关键字")
                        for children_group in self.groups[host]["children"]:
                            rt_hostnames = rt_hostnames + self.groups[children_group]
                    else:
                        # 非嵌套组
                        rt_hostnames = rt_hostnames + self.groups[host]
                else:
                    # host 是具体的主机
                    rt_hostnames.append(host)

        elif isinstance(hostsnames, str):
            if hostsnames == "ALL":
                # hosts.yaml 中全部的主机
                for hostdir in os.listdir(self.action_cfg["PUBLIC"]["source"]):
                    if os.path.isdir(os.path.join(self.action_cfg["PUBLIC"]["source"], hostdir)):
                        rt_hostnames.append(hostdir)
            else:
                # hosts.yaml 中某一台主机，后续弃用，先保持兼容
                rt_hostnames.append(hostsnames)
        else:
            raise Exception("action文件hosts配置有误")
        return rt_hostnames

    def __check_hostname(self, hostsnames):
        # hostnames 为主机名列表，该函数检查主机名是否在hosts.yaml中
        rt_hostnames = []
        source_dir = self.action_cfg["PUBLIC"]["source"]

        for hostname in hostsnames:
            hostname_dir = os.path.join(source_dir, hostname)
            if not os.path.isdir(hostname_dir):
                # 检查失败
                rt_hostnames.append(hostname)
        return rt_hostnames

    def __check_acton_hostcfg(self):
        hostnames = []
        err_hostnames = []
        for action in self.action_cfg["ACTION"]:
            hostnames = hostnames + self.__get_host_name(action["hosts"])
            err_hostnames = err_hostnames + self.__check_hostname(hostnames)

        if len(err_hostnames) != 0:
            return False, err_hostnames
        else:
            return True, []

    def __action_func_inner(self, hostname, modelname, pub_param, param):
        self.mylog.info("------模块:{mod},主机:{host}" .format(host=hostname, mod=modelname))
        if not os.path.isdir(pub_param["source"]):
            self.mylog.cri("public source目录不存在")
            raise Exception("public source目录不存在")

        m = importlib.import_module("model." + modelname + "." + modelname)
        m.ModelClass(self.mylog).action(hostname, pub_param, param)

    def action_func(self):
        # 检查hosts 配置是否有错误的，如果有错误，则不运行
        checkrz, rzlist = self.__check_acton_hostcfg()
        if not checkrz:
            self.mylog.cri(f"action 配置文件中hosts错误：{rzlist}")
            raise Exception("action 配置文件hosts配置错误")

        # 开始-测试用，正式发布时去掉
        pub_param = self.action_cfg["PUBLIC"]
        if os.path.isdir(pub_param["dest"]):
            t = pub_param["dest"]
            if input(f"目录 {t} 已存在，是否删除(y/n) ") == 'y':
                shutil.rmtree(pub_param["dest"])
        os.makedirs(pub_param["dest"])
        # 结束-测试用，正式发布时去掉

        for action in self.action_cfg["ACTION"]:
            # 遍历hosts列表
            hostname_list = self.__get_host_name(action["hosts"])
            for task in action["tasks"]:
                # 遍历task列表
                self.mylog.info('#########执行任务：{task}#########'.format(task=task["name"]))
                # 模块信息
                for modelname, param in task.items():
                    if modelname == "name":
                        continue
                    for hostname in hostname_list:
                        self.__action_func_inner(hostname, modelname, self.action_cfg["PUBLIC"], param)
        self.mylog.info('#########所有任务完成#########')
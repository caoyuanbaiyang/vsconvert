#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/1/10 16:08
# @Author  : TYQ
# @File    : vsconvert.py
# @Software: win10 python3
import logging
import shutil
from lib.hosts import hosts
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

    def __check_acton_hostcfg(self, hostobj):
        hostnames = []
        err_rt_hostnames = []
        for action in self.action_cfg["ACTION"]:
            ok_hostnames, err_hostnames = hostobj.get_host_name(action["hosts"])
            hostnames = hostnames + ok_hostnames
            err_rt_hostnames = err_rt_hostnames + err_hostnames
        if len(err_rt_hostnames) != 0:
            return False, err_rt_hostnames
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
        hostobj = hosts(self.mylog, self.groups, self.action_cfg["PUBLIC"]["source"])
        checkrz, rzlist = self.__check_acton_hostcfg(hostobj)
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
            hostname_list, err_host_list = hostobj.get_host_name(action["hosts"])
            for task in action["tasks"]:
                # 遍历task列表
                self.mylog.info('#########执行任务：{task}#########'.format(task=task["name"]))
                # 模块信息
                for modelname, param in task.items():
                    if modelname == "name":
                        continue
                    if modelname == "GetHostList":
                        self.mylog.info(f"主机列表：{hostname_list}")
                        continue
                    for hostname in hostname_list:
                        self.__action_func_inner(hostname, modelname, self.action_cfg["PUBLIC"], param)
        self.mylog.info('#########所有任务完成#########')
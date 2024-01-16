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
        self.mylog = logger(log_file, logging.INFO, logging.DEBUG)
        if os.path.exists(groups_file):
            self.groups = ReadCfg().readcfg(groups_file)
        else:
            self.groups = {}
        if filepath is None:
            self.action_cfg = ReadCfg().readcfg(action_file)
            self.cfgfilepath = action_file
        else:
            self.action_cfg = ReadCfg().readcfg(filepath)
            self.cfgfilepath = filepath

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
        self.mylog.info("------模块:{mod},主机:{host}".format(host=hostname, mod=modelname))

        m = importlib.import_module("model." + modelname + "." + modelname)
        m.ModelClass(self.mylog).action(hostname, pub_param, param)

    def __prerun_check(self):
        # action文件，public中的source配置的目录不存在则退出
        pub_param = self.action_cfg["PUBLIC"]
        if not os.path.isdir(pub_param["source"]):
            self.mylog.cri("public source目录不存在")
            raise Exception("public source目录不存在")

        # action文件，public中的dest配置的目录已存在且选择删除则删除
        if os.path.isdir(pub_param["dest"]) and input(f"目录 {pub_param['dest']} 已存在，是否删除(y/n) ") == "y":
            shutil.rmtree(pub_param["dest"])
        os.makedirs(pub_param["dest"])

        # 检查hosts 配置是否有错误，如果有错误，则不运行
        hostobj = hosts(self.mylog, self.groups, self.action_cfg["PUBLIC"]["source"])
        checkrz, rzlist = self.__check_acton_hostcfg(hostobj)
        if not checkrz:
            self.mylog.cri(f"action 配置文件中hosts错误：{rzlist}")
            raise Exception("action 配置文件hosts配置错误")

        return hostobj

    def action_func(self):
        hostobj = self.__prerun_check()

        self.mylog.green(f'############开始任务{self.cfgfilepath}############')
        for action in self.action_cfg["ACTION"]:
            # 遍历hosts列表
            hostname_list, err_host_list = hostobj.get_host_name(action["hosts"])
            for task in action["tasks"]:
                # 遍历task列表
                self.mylog.info('*********执行任务：{task}*********'.format(task=task["name"]))
                # 模块信息
                for modelname, param in task.items():
                    if modelname == "name":
                        continue
                    if modelname == "GetHostList":
                        self.mylog.info(f"主机列表：{hostname_list}")
                        continue
                    for hostname in hostname_list:
                        self.__action_func_inner(hostname, modelname, self.action_cfg["PUBLIC"], param)
        self.mylog.green('#########所有任务完成#########')

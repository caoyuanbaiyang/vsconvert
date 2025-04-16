# -*- coding: utf-8 -*-
# !/usr/bin/env python
# @Time    : 2024/1/11 10:50
# @Author  : TYQ
# @File    : tplrender.py
# @Software: win10 python3
import os
import shutil
import glob
import commentjson
import re

import chardet
from jinja2 import Environment

import lib.paramiko_ssh as paramiko_ssh

C_PATTERN = r'{{db_info\..*\.pwd'


def get_encoding(filename):
    # 以二进制模式打开文件以检测编码
    with open(filename, 'rb') as file:
        raw_data = file.read(1000)
        # 检测文件编码
        result = chardet.detect(raw_data)
        encoding = result['encoding']
        confidence = result['confidence']
        if confidence < 0.9:
            # 如果检测置信度低于0.9，默认使用utf-8
            encoding = 'utf-8'
        return encoding


def open_file(filename):
    # 以二进制模式打开文件以检测编码
    encoding = get_encoding(filename)

    # 以检测到的编码打开文件并加载JSON数据
    with open(filename, 'r', encoding=encoding) as f:
        return encoding, f.read()


def load_json(filename):
    try:
        # 以二进制模式打开文件以检测编码
        encoding = get_encoding(filename)

        # 以检测到的编码打开文件并加载JSON数据
        with open(filename, 'r', encoding=encoding, errors='ignore') as file:
            data = commentjson.load(file)
        return data
    except Exception as e:
        print(f"Error loading JSON file {filename}: {e}")
        return ''


def check_file_for_pattern(file_path, pattern):
    with open(file_path, 'r') as file:
        for line in file:
            if re.search(pattern, line):
                return True
    return False


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog
        self.source_dir = ""
        self.dest_dir = ""
        self.env_cfg = {}
        self.template_suffix = []
        self.template_filters = None

    def action(self, hostname, pub_param, param):
        self.source_dir = os.path.join(pub_param["source"], hostname)
        self.dest_dir = os.path.join(pub_param["dest"], hostname)

        if "variable_start_string" in param:
            self.env_cfg["variable_start_string"] = param["variable_start_string"]
        if "variable_end_string" in param:
            self.env_cfg["variable_end_string"] = param["variable_end_string"]
        if "filters" in param:
            self.template_filters = param["filters"]
        self.template_suffix = param["templates"]["template_suffix"]
        if os.path.isdir(self.dest_dir):
            if "y" == input(f"主机目录{self.dest_dir}已存在，删除才可继续，\n 请确认是否删除(y/n)？"):
                shutil.rmtree(self.dest_dir)
            else:
                self.mylog.cri(f"主机目录{self.dest_dir}已存在，选择退出")
                exit
        # 文件夹拷贝，主机名级别
        copy_ignore_list = None

        if "copy_ignores" in param:
            copy_ignore_list = shutil.ignore_patterns(*param["copy_ignores"])
        shutil.copytree(self.source_dir, self.dest_dir, ignore=copy_ignore_list)

        self.mylog.info(f" 目录: {self.source_dir} 拷贝结束，拷贝目的: {self.dest_dir}")

        # 获取变量文件列表
        vars_files = self.get_vars_files(param["vars_files"])
        # 加载变量文件
        render_vars = self.load_vars_files(vars_files)
        # 获取模板文件夹列表
        template_dirs = self.get_template_dirs(param["templates"])
        template_files = self.get_template_files(template_dirs)
        #  渲染模板文件
        self.render_template_files(template_files, render_vars)

    def get_vars_files(self, vars_files_cfgs: list) -> list:
        vars_files = []
        for item in vars_files_cfgs:
            vars_files = vars_files + glob.glob(item)
        return vars_files

    def load_vars_files(self, vars_files: list):
        render_vars = {}
        for vars_file in vars_files:
            # 加载变量文件
            self.mylog.debug(f" 加载变量文件: {vars_file}")
            vars_data = load_json(vars_file)
            vars_file_name = os.path.basename(vars_file)
            vars_key = os.path.splitext(vars_file_name)[0]
            render_vars[vars_key] = vars_data
        return render_vars

    def get_template_dirs(self, templates_cfg: list) -> list:
        template_dirs = []
        for directory in templates_cfg["dirs"]:
            if directory == 'NO_DIR':
                template_dirs.append(self.dest_dir)
            else:
                if any(char in directory for char in ['*', '?', '[', ']']):
                    path_name = os.path.join(self.dest_dir, directory)
                    matched_dirs = glob.glob(path_name)
                    for matched_dir in matched_dirs:
                        if os.path.isdir(matched_dir):
                            template_dirs.append(matched_dir)
                else:
                    template_dirs.append(os.path.join(self.dest_dir, directory))
        return template_dirs

    def get_template_files(self, directory_list: list) -> list:
        tpl_files = []
        for directory in directory_list:
            for root, dirs, files in os.walk(directory):
                for file in files:
                    if os.path.splitext(file)[1] not in self.template_suffix:
                        self.mylog.debug(os.path.join(root, file) + " is not a template file")
                        continue
                    tpl_files.append(os.path.join(root, file))
        return tpl_files

    # 渲染模板文件
    def render_template_files(self, template_files: list, vars_data: list):
        # 创建Jinja2环境
        env = Environment(**self.env_cfg)

        # 根据dbpwd.json创建Jinja2的过滤函数
        if self.template_filters:
            # 加载dbpwd.json文件
            cfg_data = load_json(self.template_filters)
            # 遍历dbpwd.json中的每个过滤函数
            for filter_name in cfg_data:
                # 创建过滤函数
                def create_filter(filter_name):
                    def filter_function(input_str):
                        # 创建SSH连接
                        runner = paramiko_ssh.Runner('config/id_rsa')
                        conn = paramiko_ssh.Connection(runner, cfg_data[filter_name]['ip'], '22',
                                                       cfg_data[filter_name]['username'], '1')
                        conn.connect()
                        # 执行加密命令
                        cmd = cfg_data[filter_name]['encrypt'].replace("$1", input_str)
                        exit_status, n, stdout, stderr = conn.exec_command(cmd)
                        # 如果有错误，记录错误日志
                        if stderr:
                            self.mylog.error(f"Encryption error for {filter_name}: {stderr}")
                        # 返回加密后的字符串
                        return stdout.rstrip("\n")

                    return filter_function

                # 将过滤函数添加到Jinja2环境中
                env.filters[filter_name] = create_filter(filter_name)

        # 遍历模板文件列表
        for template_file in template_files:
            try:
                # # 打开模板文件
                encoding, original_template_string = open_file(template_file)

                # 记录日志
                self.mylog.info(f'  rendering file: {template_file}')

                # 渲染模板
                template_all = env.from_string(original_template_string)
                rendered_data = template_all.render(**vars_data)

                # 生成渲染后的文件名
                rendered_file = os.path.splitext(template_file)[0]
                # 写入渲染后的文件
                with open(rendered_file, 'w', encoding=encoding, errors='ignore') as f:
                    f.write(rendered_data)

            except UnicodeDecodeError as e:
                # 记录不可打开文件的日志
                self.mylog.info(f'  不可打开文件 {template_file} 不转换: {e}')
            except Exception as e:
                # 记录渲染失败的日志
                self.mylog.error(f'  rendering file {template_file} failed: {e}')


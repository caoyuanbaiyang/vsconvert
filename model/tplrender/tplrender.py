# -*- coding: utf-8 -*-
# !/usr/bin/env python
# @Time    : 2024/1/11 10:50
# @Author  : TYQ
# @File    : tplrender.py
# @Software: win10 python3
import os
import shutil
import glob
import json
import re

from jinja2 import Environment

import lib.paramiko_ssh as paramiko_ssh

C_PATTERN = r'{{db_info\..*\.pwd'


def load_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


def check_file_for_pattern(file_path, pattern):
    with open(file_path, 'r') as file:
        for line in file:
            if re.search(pattern, line):
                return True
    return False


def filter_function(input_str: str) -> str:
    # do nothing just return the input string
    return input_str


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
        env = Environment(**self.env_cfg)
        if self.template_filters:
            env.filters['filter_function'] = filter_function

        for template_file in template_files:
            try:
                with open(template_file, 'r', encoding='utf-8') as f:
                    original_template_string = f.read()

                self.mylog.info(f'  rendering file: {template_file}')
                # 如何包含数据库的字定义过滤器，则由异常处理调整
                try:
                    template_all = env.from_string(original_template_string)
                    rendered_data = template_all.render(**vars_data)
                except Exception as e:
                    if not self.template_filters:
                        self.mylog.error(f'  rendering file {template_file} failed: {e}')
                    else:
                        if "No filter named" in str(e) and self.template_filters:
                            filter_str = str(e).split()[3].split("'")[1]
                            db_pwd_path = re.search(r'db_info\..*?\.pwd', original_template_string).group()
                            db_pwd = env.from_string('$${{' + db_pwd_path + '}}').render(**vars_data)
                            template_string = original_template_string.replace(filter_str, 'filter_function')
                            t1, db_pwd1, t2 = self.get_encrypt_pwd(filter_str, db_pwd)
                            db_pwd1 = db_pwd1.rstrip("\n")
                            template_string = re.sub(r'(\$\$\{\{)(db_info\..*?\.pwd)', rf'\1 db_pwd ', template_string)
                            template_all = env.from_string(template_string)
                            rendered_data = template_all.render(**vars_data, db_pwd=db_pwd1)
                        else:
                            self.mylog.error(f'  rendering file {template_file} failed: {e}')

                rendered_file = os.path.splitext(template_file)[0]
                with open(rendered_file, 'w', encoding='utf-8') as f:
                    f.write(rendered_data)

                if check_file_for_pattern(template_file, C_PATTERN):
                    self.mylog.debug(f'                DB template file, need to create a .tmpl file')
                    template_raw_string = re.sub(r'\$\$\{\{db_info\..*?\.pwd.*?\}\}', r'{% raw %}\g<0>{% endraw %}',
                                                 original_template_string)
                    template_raw = env.from_string(template_raw_string)
                    rendered_raw_data = template_raw.render(**vars_data)
                    rendered_raw_file = os.path.splitext(rendered_file)[0] + '.tmpl'
                    with open(rendered_raw_file, 'w', encoding='utf-8') as f:
                        f.write(rendered_raw_data)
                    self.mylog.debug(f'                DB template file, create a .tmpl file: {rendered_raw_file}')

            except UnicodeDecodeError as e:
                self.mylog.info(f'  不可打开文件 {template_file} 不转换: {e}')
            except Exception as e:
                self.mylog.error(f'  rendering file {template_file} failed: {e}')

    def get_encrypt_pwd(self, encrypt_type: str, intput_str: str) -> str:
        cfg_data = load_json(self.template_filters)
        runner = paramiko_ssh.Runner('config/id_rsa')
        if encrypt_type in cfg_data:
            conn = paramiko_ssh.Connection(runner, cfg_data[encrypt_type]['ip'], '22', cfg_data[encrypt_type]['username'], '1')
            conn.connect()
            print(paramiko_ssh.SSH_CONNECTION_CACHE.keys())
            cmd = cfg_data[encrypt_type]['encrypt'].replace("$1", intput_str)
            exit_status, n, stdout, stderr = conn.exec_command(cmd)
            print(f"exit_status: {exit_status}")
            print(f"stdout: {stdout}")
            if stderr:
                print(f"stderr: {stderr}")
            return exit_status, stdout, stderr

# -*- coding: utf-8 -*-
# !/usr/bin/env python
# @Time    : 2024/1/11 10:50
# @Author  : TYQ
# @File    : tplrender.py
# @Software: win10 python3
import os
import shutil
import fnmatch
import glob
import json

from jinja2 import Environment, TemplateNotFound, BaseLoader, FileSystemLoader


def load_json(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
    return data


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog
        self.source_dir = ""
        self.dest_dir = ""
        self.env_cfg = {}
        self.template_suffix = []

    def action(self, hostname, pub_param, param):
        self.source_dir = os.path.join(pub_param["source"], hostname)
        self.dest_dir = os.path.join(pub_param["dest"], hostname)

        if "variable_start_string" in param:
            self.env_cfg["variable_start_string"] = param["variable_start_string"]
        if "variable_end_string" in param:
            self.env_cfg["variable_end_string"] = param["variable_end_string"]
        self.template_suffix = param["templates"]["template_suffix"]
        if os.path.isdir(self.dest_dir):
            if "y" == input(f"目录{self.dest_dir}已存在，删除才可继续，\n 请确认是否删除(y/n)？"):
                shutil.rmtree(self.dest_dir)
            else:
                self.mylog.cri(f"目录{self.dest_dir}以存在，选择退出")
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
        #  渲染模板文件
        self.render_template(template_dirs, render_vars)

    def get_vars_files(self, vars_files_cfgs: list) -> list:
        vars_files = []
        for item in vars_files_cfgs:
            vars_files = vars_files + glob.glob(item)
        return vars_files

    def load_vars_files(self, vars_files: list):
        render_vars = {}
        for vars_file in vars_files:
            # 加载变量文件
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

    # 渲染模板文件
    def render_template(self, template_dirs: list, vars_data: list):
        loader = FileSystemLoader(template_dirs)
        env = Environment(loader=loader, **self.env_cfg)
        template_list = loader.list_templates()
        for template_file in template_list:
            template_path = env.loader.get_source(env, template_file)[1]
            if os.path.splitext(template_file)[1] not in self.template_suffix:
                self.mylog.info(f'  {template_path} is not a template file')
                continue
            template = env.get_template(template_file)
            self.mylog.info(f'  render file: {template_path}')
            rendered_data = template.render(**vars_data)
            rendered_file = os.path.splitext(template_path)[0]
            with open(rendered_file, 'w', encoding='utf-8') as f:
                f.write(rendered_data)





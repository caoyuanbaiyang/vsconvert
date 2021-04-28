# -*- coding: utf-8 -*-
# !/usr/bin/env python

# @Time    : 2020/1/14 14:46
# @Author  : TYQ
# @File    : vsconvert.py
# @Software: win10 python3
import codecs
import os
import shutil
import re
from fnmatch import fnmatchcase as match
import copy

import chardet

REPLACE_PATTERN = r'(.*)\{lib:(.*):(.*)\}(.*)'


def isContrainSpecialCharacter(string):
    # fnmatch 支持的模糊匹配通配符
    special_character = r"*?[]!"
    for i in special_character:
        if i in string:
            return True
    return False


def exclude_files(filename, dir_filename, excludes=[]):  # 是否属于不下载的文件判断
    # exclude 为具体配置，支持文件名配置及带目录的配置   # exclude 的不下载，跳过本次循环，进入下一循环
    if filename in excludes or dir_filename in excludes:
        return True

    # exclude 为模糊配置，配置的话就不下载，跳过本次循环，进入下一循环
    for exclude in excludes:
        if match(filename, exclude) or match(dir_filename, exclude):
            return True

    # 以上情况都不是这返回False
    return False


def is_need_alter(mylog, file, excludes, limit_size=1024000):
    (dirname, filename) = os.path.split(file)
    if os.path.getsize(file) < limit_size and not exclude_files(filename=filename, dir_filename=file, excludes=excludes):
        rz = True
    else:
        mylog.info(f"忽略文件:文件大小-{os.path.getsize(file)},文件名称-{filename} ,路径-{file},limit_size-{limit_size}")
        rz = False
    return rz


#: BOMs to indicate that a file is a text file even if it contains zero bytes.
_TEXT_BOMS = (
    codecs.BOM_UTF16_BE,
    codecs.BOM_UTF16_LE,
    codecs.BOM_UTF32_BE,
    codecs.BOM_UTF32_LE,
    codecs.BOM_UTF8,
)


def is_binary_file(file_path):
    with open(file_path, 'rb') as file:
        initial_bytes = file.read(8192)
        file.close()
    return not any(initial_bytes.startswith(bom) for bom in _TEXT_BOMS) and b'\0' in initial_bytes


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def action(self, hostname, pub_param, param):
        source_dir = os.path.join(pub_param["source"], hostname)
        dest_dir = os.path.join(pub_param["dest"], hostname)

        if os.path.isdir(dest_dir):
            if "y" == input(f"目录{dest_dir}已存在，删除才可继续，\n 请确认是否删除(y/n)？"):
                shutil.rmtree(dest_dir)
            else:
                self.mylog.cri(f"目录{dest_dir}以存在，选择退出")
                exit
        # 文件夹拷贝，主机名级别
        copy_ignore_list = None
        for i, param_item in enumerate(param, start=1):
            if "copy_ignores" in param_item and "ignores" in param_item["copy_ignores"]:
                copy_ignore_list = shutil.ignore_patterns(*param_item["copy_ignores"]["ignores"])
        shutil.copytree(source_dir, dest_dir, ignore=copy_ignore_list)

        self.mylog.info(f"目录: {source_dir} 拷贝结束，拷贝目的: {dest_dir}")

        # 读取配置信息
        for i, param_item in enumerate(param, start=1):
            # dirs 目录配置
            if "dirs" in param_item:
                dirs = param_item["dirs"]
            # rpls 替换语法配置
            if "rpls" in param_item:
                # 循环目录进行处理
                for dir_item in dirs:
                    rpl_dir = list(dir_item.keys())[0]
                    rec_identify = list(dir_item.values())[0]

                    # dirs 配置项为文件夹
                    if rpl_dir.endswith("\\") or rpl_dir == "$HOME":
                        if rpl_dir == "$HOME":
                            rpl_dir = ""
                        self.alter_dir(os.path.join(dest_dir, rpl_dir), rec_identify, param_item["rpls"])

                    # dirs 配置项为带*号的,带*号只能对文件进行配置，因此目录循环模式为关闭状态
                    elif isContrainSpecialCharacter(rpl_dir):
                        (dirname, filename) = os.path.split(rpl_dir)
                        self.alter_dir(os.path.join(dest_dir, dirname), "-r", param_item["rpls"], filename)

                    # dirs 配置项为纯文件
                    else:
                        self.alter_file(os.path.join(dest_dir, rpl_dir), param_item["rpls"])

    # filename_patten 只是给具体文件配置或带*号配置时使用
    def alter_dir(self, v_dir, rec_identify, switchparam, filename_patten="*"):
        for file in os.listdir(v_dir):
            path_file = os.path.join(v_dir, file)
            # 如果是文件
            if not os.path.isdir(path_file) and match(file, filename_patten):
                self.alter_file(path_file, switchparam)
            # 如果是目录且循环
            if os.path.isdir(path_file):
                for switch_item in switchparam:
                    switch_item_list = []
                    if not ("alter_exclude" in switch_item):
                        alter_excludes = []
                    else:
                        alter_excludes = switch_item["alter_exclude"]
                    if file in alter_excludes:
                        self.mylog.info(f"忽略目录:{path_file}")
                        continue
                    if rec_identify == "+r":
                        switch_item_list.append(switch_item)
                        self.alter_dir(path_file, rec_identify, switch_item_list)

    def alter_file(self, file, switchparam):
        # 如果file 是二进制文件则跳过
        if is_binary_file(file):
            return
        for switch_item in switchparam:
            if not ('alter_exclude' in switch_item):
                alter_excludes = []
            else:
                alter_excludes = switch_item["alter_exclude"]
            if is_need_alter(self.mylog, file, alter_excludes):
                # replace 可支持lib,如随机密码函数randpwd
                self.__alter_file_inner(file, switch_item["regexp"], switch_item["replace"])

    def __alter_file_inner(self, file, pattern, replace):
        self.mylog.info(f"文件：{file} 查找:{pattern} ")
        repl_new = replace
        rem = re.match(REPLACE_PATTERN, replace)

        fbytes = min(20480, os.path.getsize(file))
        result = chardet.detect(open(file, 'rb').read(fbytes))
        encoding = result['encoding']
        with open(file, "r", newline="", encoding=encoding, errors='replace') as f1, open("%s.bak.tyq" % file, "w",
                                                                                          newline="",
                                                                                          encoding=encoding,
                                                                                          errors='replace') as f2:
            for (rownum, line) in enumerate(f1, 1):
                if rem:
                    # replace 可支持lib,如随机密码函数randpwd
                    func = rem.group(2)
                    para = rem.group(3)
                    import lib.replace_lib as replace_lib
                    m = eval(f"replace_lib.{func}")(para)
                    repl = r'\1' + m + r'\4'
                    repl_new = re.sub(REPLACE_PATTERN, repl, replace)
                line_new = re.sub(pattern, repl_new, line)
                if line != line_new:
                    ln = line.replace("\n", "").replace("\r", "")
                    self.mylog.info(f"  匹配行{rownum}, 内容:{ln}")
                    self.mylog.info(f"  替换行{rownum}, 内容:{line_new}")
                f2.write(line_new)
        os.remove(file)
        os.rename("%s.bak.tyq" % file, file)

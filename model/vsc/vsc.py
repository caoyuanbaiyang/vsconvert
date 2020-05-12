#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/1/14 14:46
# @Author  : TYQ
# @File    : vsconvert.py
# @Software: win10 python3
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


def is_need_alert(file, cfg_dir, cfg_file, excludes):
    (dirname, filename) = os.path.split(file)
    if not isContrainSpecialCharacter(cfg_file):
        if os.path.getsize(file) < 1024000 and (cfg_file == file or cfg_dir == dirname) and \
                not exclude_files(filename, file, excludes):
            rz = True
        else:
            rz = False
    else:
        # cfg_file中有模糊匹配，需先对cfg_file 做操作
        (cfg_dirname, cfg_filename) = os.path.split(cfg_file)
        if os.path.getsize(file) < 1024000 and cfg_dirname == dirname and match(filename, cfg_filename):
            rz = True
        else:
            rz = False
    return rz


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def action(self, hostname, pub_param, param):
        source_dir = os.path.join(pub_param["source"], hostname)
        dest_dir = os.path.join(pub_param["dest"], hostname)

        if not os.path.isdir(dest_dir):
            os.makedirs(dest_dir)

        if not ('copy_exclude' in param):
            copy_excludes = []
        else:
            copy_excludes = param["copy_exclude"]

        swithparam = copy.deepcopy(param)
        swithparam.pop('copy_exclude')

        self.dir_copy(source_dir, dest_dir, swithparam, copy_excludes, pub_param, hostname)

    def dir_copy(self, source_dir, dest_dir, switchparam, copy_excludes, pub_param, hostname):
        for file in os.listdir(source_dir):
            src_name = os.path.join(source_dir, file)
            dest_name = os.path.join(dest_dir, file)

            if exclude_files(file, src_name, copy_excludes):
                self.mylog.info("忽略拷贝:{}".format(src_name))
                continue

            if os.path.isfile(src_name):
                self.mylog.info("文件拷贝:{}".format(src_name))
                shutil.copy(src_name, dest_name)
                self.alert_file(dest_name, switchparam, pub_param, hostname)
            else:
                if not os.path.isdir(dest_name):
                    self.mylog.info("目录拷贝:{}".format(src_name))
                    os.makedirs(dest_name)
                self.dir_copy(src_name, dest_name, switchparam, copy_excludes, pub_param, hostname)

    def alert_file(self, file, switchparam, pub_param, hostname):
        (dirname, filename) = os.path.split(file)
        for switchitem in list(switchparam.items()):
            file_param = switchitem[0]
            if file_param.endswith("\\"):
                # file 为目录
                cfg_dir = os.path.join(pub_param["dest"], hostname, file_param.rstrip("\\"))
                cfg_file = ''
            else:
                # file 为文件
                cfg_dir = ''
                cfg_file = os.path.join(pub_param["dest"], hostname, file_param)

            for replace_item in switchitem[1]:
                if not ('alert_exclude' in replace_item):
                    alert_excludes = []
                else:
                    alert_excludes = replace_item["alert_exclude"]
                if is_need_alert(file, cfg_dir, cfg_file, alert_excludes):
                    # replace 可支持lib,如随机密码函数randpwd
                    self.__alter_file_inner(file, replace_item["regexp"], replace_item["replace"])

    def __alter_file_inner(self, file, pattern, replace):
        replace_str = replace
        rem = re.match(REPLACE_PATTERN, replace)

        fbytes = min(32, os.path.getsize(file))
        result = chardet.detect(open(file, 'rb').read(fbytes))
        encoding = result['encoding']
        with open(file, "r", encoding=encoding, newline="") as f1, open("%s.bak" % file, "w", encoding=encoding,
                                                                        newline="") as f2:
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
                    self.mylog.info("  匹配行{}, 内容:{}".format(rownum, line.replace("\n", "")))
                    self.mylog.info("  替换行{}, 内容:{}".format(rownum, line_new.replace("\n", "")))
                f2.write(line_new)
        os.remove(file)
        os.rename("%s.bak" % file, file)

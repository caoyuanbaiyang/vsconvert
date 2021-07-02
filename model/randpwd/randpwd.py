# -*- coding: utf-8 -*-
# !/usr/bin/env python

# @Time    : 2020/1/14 14:46
# @Author  : TYQ
# @File    : vsconvert.py
# @Software: win10 python3


import os
import stat
import shutil
import re
import chardet

REPLACE_PATTERN = r'(.*)\{lib:(.*):(.*)\}(.*)'


class ModelClass(object):
    def __init__(self, mylog):
        self.mylog = mylog

    def action(self, hostname, pub_param, param):
        for switchitem in list(param.items()):
            file_param = switchitem[0]
            # file 为文件
            cfg_dir = ''
            cfg_file = os.path.join(pub_param["source"], hostname, file_param)
            cfg_file_new = cfg_file + "_new"
            shutil.copy(cfg_file, cfg_file_new)
            os.chmod(cfg_file_new, stat.S_IRWXU)

            for replace_item in switchitem[1]:
                self.__alter_file_inner(cfg_file_new, replace_item["regexp"], replace_item["replace"])

    def __alter_file_inner(self, file, pattern, replace):
        repl_new = replace
        rem = re.match(REPLACE_PATTERN, replace)

        fbytes = min(2048, os.path.getsize(file))
        result = chardet.detect(open(file, 'rb').read(fbytes))
        encoding = result['encoding']
        with open(file, "r", newline="", encoding=encoding) as f1, open("%s.bak" % file, "w", newline="",
                                                                        encoding=encoding) as f2:
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

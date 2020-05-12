#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/5/11 16:08
# @Author  : TYQ
# @File    : replace_lib.py
# @Software: win10 python3
import random

s1 = "abcdefghijklmnopqrstuvwxyz"
s4 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
s2 = "1234567890"
s3 = "!@#$%^&*"


def randompwd(param):
    pwd = ""
    for i in range(2):
        pwd += s1[random.randint(0, len(s1)-1)]
    for i in range(2):
        pwd += s4[random.randint(0, len(s4)-1)]
    pwd += s3[random.randint(0, len(s3)-1)]
    for i in range(4):
        pwd += s2[random.randint(0, len(s2)-1)]
    return pwd


if __name__ == '__main__':
    print(randompwd())

#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2020/5/11 16:08
# @Author  : TYQ
# @File    : replace_lib.py
# @Software: win10 python3
import random
import string


s1 = "abcdefghijklmnopqrstuvwxyz"
s4 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
s2 = "1234567890"
s3 = "!@#$%^&*"


def randompwd1(param):
    pwd = ""
    for i in range(2):
        pwd += s1[random.randint(0, len(s1)-1)]
    for i in range(2):
        pwd += s4[random.randint(0, len(s4)-1)]
    pwd += s3[random.randint(0, len(s3)-1)]
    for i in range(4):
        pwd += s2[random.randint(0, len(s2)-1)]
    return pwd


def randompwd(param):
    str_long = int(param)

    lowercase_num = random.randint(2, 4)
    uppercase_num = random.randint(2, str_long - lowercase_num - 3)
    digits_num = str_long - 2 - uppercase_num - lowercase_num

    password = random.sample(string.ascii_uppercase, uppercase_num) + random.sample(string.digits, digits_num) + random.sample(
        string.ascii_lowercase, lowercase_num) + list(random.choice(s3))

    random.shuffle(password)
    pwd = random.choice(string.ascii_lowercase) + ''.join(password)
    return pwd


if __name__ == '__main__':
    for i in range(100):
        print(randompwd(9))

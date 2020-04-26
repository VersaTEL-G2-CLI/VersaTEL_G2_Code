#conding:utf-8
import re

#for diskgroup
def judge_cmd_result_suc(cmd):
    re_suc = re.compile('SUCCESS')
    if re_suc.search(cmd):
        return True


def judge_cmd_result_err(cmd):
    re_err = re.compile('ERROR')
    if re_err.search(cmd):
        return True


def judge_cmd_result_war(cmd):
    re_err = re.compile('WARNING')
    if re_err.search(cmd):
        return True


def get_err_mes(cmd):
    re_mes_des = re.compile(r'(?<=Description:\\n)[\S\s]*(?=\\nCause:)')
    if re_mes_des.search(cmd):
        return (re_mes_des.search(cmd).group())


def get_cau_mes(cmd):
    re_mes_cau = re.compile(r'(?<=Cause:\\n)[\S\s]*(?=\\nDetails:)')
    if re_mes_cau.search(cmd):
        return re_mes_cau.search(cmd).group()

def get_err_mes_vd(cmd):
    re_mes_des = re.compile(r'(?<=Description:\\n)[\S\s]*(?=\\nDetails:)')
    if re_mes_des.search(cmd):
        return (re_mes_des.search(cmd).group())


def get_err_not_vg(result,node,vg):
    re_ = re.compile(r'\(Node: \''+node+'\'\) Volume group \''+vg+'\' not found')
    if re_.search(result):
        return (re_.search(result).group())


def get_err_detailes(result):
    re_ = re.compile(r'Description:\n[\t\s]*(.*)\n')
    if re_.search(result):
        return (re_.search(result).group(1))

def get_war_mes(result):
    re_ = re.compile(r'\x1b\[1;33mWARNING:\n\x1b(?:.*\s*)+\n$')
    if re_.search(result):
        return (re_.search(result).group())


def refining_thinlv(str):
    list = str.splitlines()
    list_thinlv = []
    re_ = re.compile(r'\s*(\S*)\s*(\S*)\s*\S*\s*(\S*)\s*\S*\s*\S*\s*\S*\s*?')
    for list_one in list:
        if 'twi' in list_one:
            thinlv_one = re_.findall(list_one)
            list_thinlv.append(thinlv_one[0])
    return list_thinlv

def refining_vg(str):
    list = str.splitlines()
    list_vg = []
    re_ = re.compile(r'\s*(\S*)\s*\S*\s*\S*\s*\S*\s*\S*\s*(\S*)\s*(\S*)\s*?')
    for list_one in list[1:]:
        vg_one = re_.findall(list_one)
        list_vg.append(vg_one[0])
    return list_vg



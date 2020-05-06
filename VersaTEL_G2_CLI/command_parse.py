# coding:utf-8

import argparse
import sys
# import view
from stor_cmds import Action as stor_action
import usage
import linstordb

import os
from crm_resouce import crm
from getlinstor import GetLinstor
from iscsi_json import JSON_OPERATION
from cli_socketclient import SocketSend
import regex
from command import CLI


# 多节点创建resource时，storapoo多于node的异常类
class NodeLessThanSPError(Exception):
    pass


class InvalidSize(Exception):
    pass


class CLIParse():
    def __init__(self):
        self.cmd = CLI()
        # if sys.argv[1] == 'stor':
        #     self.cmd.parser_stor()
        # elif sys.argv[1] == 'iscsi':
        #     self.cmd.parser_iscsi()
        # else:
        #     print('111')

        self.vtel = self.cmd.vtel
        self.args = self.vtel.parse_args()
        if self.args.vtel_sub == 'stor':
            self.stor_judge()
        elif self.args.vtel_sub == 'iscsi':
            self.iscsi_judge()
        else:
            self.vtel.print_help()


    def case_node(self):
        args = self.args
        parser_create = self.cmd.node_create
        parser_delete = self.cmd.node_delete

        def node_create():
            if args.gui:
                handle = SocketSend()
                handle.send_result(stor_action.create_node, args.node, args.ip, args.nodetype)
            elif args.node and args.nodetype and args.ip:
                stor_action.create_node(args.node, args.ip, args.nodetype)
            else:
                parser_create.print_help()

        def node_modify():
            pass

        def node_delete():
            def excute():
                if args.gui:
                    print('for gui delete node')
                else:
                    stor_action.delete_node(args.node)

            def _delete_comfirm():  # 命名，是否删除
                if stor_action.confirm_del():
                    excute()
                else:
                    print('Delete canceled')

            def _skip_confirm():  # 是否跳过确认
                if args.yes:
                    excute()
                else:
                    _delete_comfirm()

            _skip_confirm() if args.node else parser_delete.print_help()

        def node_show():
            tb = linstordb.OutputData()
            if args.nocolor:
                tb.show_node_one(args.node) if args.node else tb.node_all()
            else:
                tb.show_node_one_color(args.node) if args.node else tb.node_all_color()

        # 对输入参数的判断（node的下一个参数）
        if self.args.node_sub in ['create', 'c']:
            node_create()
        elif self.args.node_sub in ['modify', 'm']:
            node_modify()
        elif self.args.node_sub in ['delete', 'd']:
            node_delete()
        elif self.args.node_sub in ['show', 's']:
            node_show()
        else:
            self.cmd.stor_node.print_help()

    def case_resource(self):
        args = self.args
        parser_create = self.cmd.resource_create
        parser_modify = self.cmd.resource_modify
        parser_delete = self.cmd.resource_delete
        """
        resource create 使用帮助
        自动创建：vtel stor create RESOURCE -s SIZE -a -num NUM
        手动创建：vtel stor create RESOURCE -s SIZE -n NODE -sp STORAGEPOOL
        创建diskless：vtel stor create RESOURCE -diskless NODE
        添加mirror到其他节点(手动):vtel stor create RESOURCE -am -n NODE -sp STORAGEPOOL
        添加mirror到其他节点(自动):vtel stor create RESOURCE -am -a -num NUM
        """

        def resource_create():
            # def is_args_correct():
            #     if len(args.node) >= len(args.storagepool):
            #         return True

            """
            以下注释代码为创建resource判断分支的另一种写法
            把创建resource的三种模式：正常创建（包括自动和手动），创建diskless，添加mirror分别封装
            最后再执行
            """

            # 指定node和storagepool数量的规范判断，符合则继续执行
            def is_args_correct():
                if len(args.node) < len(args.storagepool):
                    raise NodeLessThanSPError('指定的storagepool数量应少于node数量')

            def is_vail_size(size):
                if not regex.judge_size(size):
                    raise InvalidSize('Invalid Size')

            # 特定模式必需的参数
            list_auto_required = [args.auto, args.num]
            list_manual_required = [args.node, args.storagepool]

            # 正常创建resource
            def create_normal_resource():
                # 正常创建resource禁止输入的参数
                list_normal_forbid = [args.diskless, args.add_mirror]
                if not args.size:
                    return
                if any(list_normal_forbid):
                    return
                try:
                    is_vail_size(args.size)
                except InvalidSize:
                    print('%s is not a valid size!' % args.size)
                    sys.exit(0)
                else:
                    pass

                if all(list_auto_required) and not any(list_manual_required):
                    # For GUI
                    if args.gui:
                        handle = SocketSend()
                        handle.send_result(stor_action.create_res_auto, args.resource, args.size, args.num)
                        return True
                    # CLI
                    else:
                        stor_action.create_res_auto(args.resource, args.size, args.num)
                        return True
                elif all(list_manual_required) and not any(list_auto_required):
                    try:
                        is_args_correct()
                    except NodeLessThanSPError:
                        print('The number of nodes and storage pools do not meet the requirements')
                        return True
                    else:
                        # For GUI
                        if args.gui:
                            handle = SocketSend()
                            handle.send_result(stor_action.create_res_manual, args.resource, args.size, args.node,
                                               args.storagepool)
                            return True
                        # CLI
                        else:
                            stor_action.create_res_manual(args.resource, args.size, args.node, args.storagepool)
                            return True

            # 创建resource的diskless资源条件判断，符合则执行
            def create_diskless_resource():
                list_diskless_forbid = [args.auto, args.num, args.storagepool, args.add_mirror, args.size]
                if not args.node:
                    return
                if not any(list_diskless_forbid):
                    if args.gui:
                        handle = SocketSend()
                        handle.send_result(stor_action.create_res_diskless, args.node, args.resource)
                        return True
                    else:
                        stor_action.create_res_diskless(args.node, args.resource)
                        return True

            # 添加mirror
            def add_resource_mirror():
                # 添加mirror禁止输入的参数
                list_add_mirror_forbid = [args.diskless, args.size]
                if not args.add_mirror:
                    return
                if any(list_add_mirror_forbid):
                    return
                if all(list_auto_required) and not any(list_manual_required):
                    # For GUI
                    if args.gui:
                        handle = SocketSend()
                        handle.send_result(stor_action.add_mirror_auto, args.resource, args.num)
                        return True
                    else:
                        stor_action.add_mirror_auto(args.resource, args.num)
                        return True
                elif all(list_manual_required) and not any(list_auto_required):
                    try:
                        is_args_correct()
                    except NodeLessThanSPError:
                        print('The number of nodes does not meet the requirements')
                        return True
                    else:
                        # For GUI
                        if args.gui:
                            handle = SocketSend()
                            handle.send_result(stor_action.add_mirror_manual, args.resource, args.node,
                                               args.storagepool)
                            return True
                        else:
                            stor_action.add_mirror_manual(args.resource, args.node, args.storagepool)
                            return True

            # 总执行
            if create_normal_resource():
                pass
            elif create_diskless_resource():
                pass
            elif add_resource_mirror():
                pass
            else:
                parser_create.print_help()

            # # 对应创建模式必需输入的参数和禁止输入的参数
            # list_auto_required = [args.auto, args.num]
            # list_auto_forbid = [args.node, args.storagepool, args.diskless,args.add_mirror]
            # list_manual_required = [args.node, args.storagepool]
            # list_manual_forbid = [args.auto, args.num, args.diskless,args.add_mirror]
            # list_diskless_forbid = [args.auto, args.num, args.storagepool,args.add_mirror]
            #
            #
            # if args.size:
            #     #自动创建条件判断，符合则执行
            #     if all(list_auto_required) and not any(list_auto_forbid):
            #         stor_action.create_res_auto(args.resource, args.size, args.num)
            #     #手动创建条件判断，符合则执行
            #     elif all(list_manual_required) and not any(list_manual_forbid):
            #         if is_args_correct():
            #             stor_action.create_res_manual(args.resource,args.size,args.node,args.storagepool)
            #         else:
            #             parser_create.print_help()
            #     else:
            #         parser_create.print_help()
            #
            #
            # elif args.diskless:
            #     # 创建resource的diskless资源条件判断，符合则执行
            #     if args.node and not any(list_diskless_forbid):
            #         stor_action.create_res_diskless(args.node, args.resource)
            #     else:
            #         parser_create.print_help()
            #
            # elif args.add_mirror:
            #     #手动添加mirror条件判断，符合则执行
            #     if all([args.node,args.storagepool]) and not any([args.auto, args.num]):
            #         if is_args_correct():
            #             stor_action.add_mirror_manual(args.resource,args.node,args.storagepool)
            #         else:
            #             parser_create.print_help()
            #     #自动添加mirror条件判断，符合则执行
            #     elif all([args.auto,args.num]) and not any([args.node,args.storagepool]):
            #         stor_action.add_mirror_auto(args.resource,args.num)
            #     else:
            #         parser_create.print_help()
            #
            # else:
            #     parser_create.print_help()

        # resource修改功能，未开发
        def resource_modify():
            if args.resource:
                if args.size:
                    print('调整resource的size')
                elif args.node and args.diskless:
                    print('将某节点上某个diskful的资源调整为diskless')

                elif args.node and args.storagepool:
                    print('将某节点上某个diskless的资源调整为diskful')
            else:
                parser_modify.print_help()

        # resource删除判断
        def resource_delete():
            def excute():  # 判断是否指定节点
                if args.node:
                    if args.gui:
                        print('for gui')
                    else:
                        stor_action.delete_resource_des(args.node, args.resource)
                elif not args.node:
                    if args.gui:
                        print('for gui')
                    else:
                        stor_action.delete_resource_all(args.resource)

            def _delete_comfirm():  # 命名，是否删除
                if stor_action.confirm_del():
                    excute()
                else:
                    print('Delete canceled')

            def _skip_confirm():  # 是否跳过确认
                if args.yes:
                    excute()
                else:
                    _delete_comfirm()

            _skip_confirm() if args.resource else parser_delete.print_help()

            # if args.resource:
            #     if args.node:
            #         if args.yes:
            #             stor_action.delete_resource_des(args.node, args.resource)
            #         else:
            #             if stor_action.confirm_del():
            #                 stor_action.delete_resource_des(args.node, args.resource)
            #     elif not args.node:
            #         if args.yes:
            #             stor_action.delete_resource_all(args.resource)
            #         else:
            #             if stor_action.confirm_del():
            #                 stor_action.delete_resource_all(args.resource)
            # else:
            #     parser_delete.print_help()

        def resource_show():
            tb = linstordb.OutputData()
            if args.nocolor:
                tb.show_res_one(args.resource) if args.resource else tb.res_all()
            else:
                tb.show_res_one_color(args.resource) if args.resource else tb.res_all_color()

        # 对输入参数的判断（resource的下一个参数）
        if args.resource_sub in ['create', 'c']:
            resource_create()
        elif args.resource_sub in ['modify', 'm']:
            resource_modify()
        elif args.resource_sub in ['delete', 'd']:
            resource_delete()
        elif args.resource_sub in ['show', 's']:
            resource_show()
        else:
            self.cmd.stor_resource.print_help()

    def case_storagepool(self):
        args = self.args
        parser_create = self.cmd.storagepool_create
        parser_modify = self.cmd.storagepool_modify
        parser_delete = self.cmd.storagepool_delete

        def storagepool_create():
            if args.storagepool and args.node:
                if args.lvm:
                    if args.gui:
                        handle = SocketSend()
                        handle.send_result(stor_action.create_storagepool_lvm, args.node, args.storagepool, args.lvm)
                    else:
                        stor_action.create_storagepool_lvm(args.node, args.storagepool, args.lvm)
                elif args.tlv:
                    if args.gui:
                        handle = SocketSend()
                        handle.send_result(stor_action.create_storagepool_thinlv, args.node, args.storagepool, args.tlv)
                    else:
                        stor_action.create_storagepool_thinlv(args.node, args.storagepool, args.tlv)
                else:
                    parser_create.print_help()
            else:
                parser_create.print_help()

        def storagepool_modify():
            pass

        def storagepool_delete():
            def excute():
                if args.gui:
                    print('for gui')
                else:
                    stor_action.delete_storagepool(args.node, args.storagepool)

            def _delete_comfirm():  # 命名，是否删除
                if stor_action.confirm_del():
                    excute()
                else:
                    print('Delete canceled')

            def _skip_confirm():  # 是否跳过确认
                if args.yes:
                    excute()
                else:
                    _delete_comfirm()

            _skip_confirm() if args.storagepool else parser_delete.print_help()

        def storagepool_show():
            tb = linstordb.OutputData()
            if args.nocolor:
                tb.show_sp_one(args.storagepool) if args.storagepool else tb.sp_all()
            else:
                tb.show_sp_one_color(args.storagepool) if args.storagepool else tb.sp_all_color()

        if args.storagepool_sub in ['create', 'c']:
            storagepool_create()
        elif args.storagepool_sub in ['modify', 'm']:
            storagepool_modify()
        elif args.storagepool_sub in ['delete', 'd']:
            storagepool_delete()
        elif args.storagepool_sub in ['show', 's']:
            storagepool_show()
        else:
            self.cmd.stor_storagepool.print_help()

    # pass
    def case_snap(self):
        args = self.args
        parser = self.cmd.storagepool_create

        def snap_create():
            args = self.args
            parser = self.cmd.storagepool_create

            if args.storagepool and args.node:
                if args.lvm:
                    stor_action.create_storagepool_lvm(args.node, args.storagepool, args.lvm)
                elif args.tlv:
                    stor_action.create_storagepool_thinlv(args.node, args.storagepool, args.tlv)
            else:
                parser.print_help()

        def snap_modify():
            pass

        def snap_delete():
            pass

        def snap_show():
            pass

        if args.snap_sub == 'create':
            snap_create()
        elif args.snap_sub == 'modify':
            snap_modify()
        elif args.snap_sub == 'delete':
            snap_delete()
        elif args.snap_sub == 'show':
            snap_show()
        else:
            self.cmd.stor_snap.print_help()

    # gui端 get DB
    def getdb(self):
        db = linstordb.LINSTORDB()
        handle = SocketSend()
        handle.send_result(db.data_base_dump)  # get sql_scipt

    def stor_judge(self):
        args = self.args
        if args.vtel_sub == 'stor':
            if self.args.stor_sub in ['node', 'n']:
                self.case_node()
            elif self.args.stor_sub in ['resource', 'r']:
                self.case_resource()
            elif self.args.stor_sub in ['storagepool', 'sp']:
                self.case_storagepool()
            elif self.args.stor_sub in ['snap', 'sn']:
                self.case_snap()

            elif self.args.db:
                self.getdb()
            else:
                self.cmd.vtel_stor.print_help()

    """
    ------iscsi-------
    """

    # 命令判断
    def iscsi_judge(self):
        js = JSON_OPERATION()
        args = self.args
        if args.iscsi in ['host', 'h']:
            if args.host in ['create', 'c']:
                if args.gui == 'gui':
                    handle = SocketSend()
                    handle.send_result(self.judge_hc, args, js)
                else:
                    self.judge_hc(args, js)
            elif args.host in ['show', 's']:
                self.judge_hs(args, js)
            elif args.host in ['delete', 'd']:
                self.judge_hd(args, js)
            else:
                print("iscsi host (choose from 'create', 'show', 'delete')")
                self.cmd.iscsi_host.print_help()
        elif args.iscsi in ['disk', 'd']:
            if args.disk in ['show', 's']:
                self.judge_ds(args, js)
            else:
                print("iscsi disk (choose from 'show')")
                self.cmd.iscsi_disk.print_help()
        elif args.iscsi in ['hostgroup', 'hg']:
            if args.hostgroup in ['create', 'c']:
                if args.gui == 'gui':
                    handle = SocketSend()
                    handle.send_result(self.judge_hgc, args, js)
                else:
                    self.judge_hgc(args, js)
            elif args.hostgroup in ['show', 's']:
                self.judge_hgs(args, js)
            elif args.hostgroup in ['delete', 'd']:
                self.judge_hgd(args, js)
            else:
                print("iscsi hostgroup (choose from 'create', 'show', 'delete')")
                self.cmd.iscsi_hostgroup.print_help()
        elif args.iscsi in ['diskgroup', 'dg']:
            if args.diskgroup in ['create', 'c']:
                if args.gui == 'gui':
                    handle = SocketSend()
                    handle.send_result(self.judge_dgc, args, js)
                else:
                    self.judge_dgc(args, js)
            elif args.diskgroup in ['show', 's']:
                self.judge_dgs(args, js)
            elif args.diskgroup in ['delete', 'd']:
                self.judge_dgd(args, js)
            else:
                print("iscsi diskgroup (choose from 'create', 'show', 'delete')")
                self.cmd.iscsi_diskgroup.print_help()
        elif args.iscsi in ['map', 'm']:
            if args.map in ['create', 'c']:
                if args.gui == 'gui':
                    handle = SocketSend()
                    handle.send_result(self.judge_mc, args, js)
                else:
                    self.judge_mc(args, js)
            elif args.map in ['show', 's']:
                self.judge_ms(args, js)
            elif args.map in ['delete', 'd']:
                self.judge_md(args, js)
            else:
                print("iscsi map (choose from 'create', 'show', 'delete')")
                self.cmd.iscsi_map.print_help()
        elif args.iscsi == 'show':
            print(js.read_data_json())
            handle = SocketSend()
            handle.send_result(self.judge_s, js)
        else:
            print("iscsi (choose from 'host', 'disk', 'hg', 'dg', 'map')")
            self.cmd.vtel_iscsi.print_help()

    # host创建
    def judge_hc(self, args, js):
        print("hostname:", args.iqnname)
        print("host:", args.iqn)
        if js.check_key('Host', args.iqnname):
            print("Fail! The Host " + args.iqnname + " already existed.")
            return False
        else:
            js.creat_data("Host", args.iqnname, args.iqn)
            print("Create success!")
            return True

    # host查询
    def judge_hs(self, args, js):
        if args.show == 'all' or args.show == None:
            hosts = js.get_data("Host")
            print("	" + "{:<15}".format("Hostname") + "Iqn")
            print("	" + "{:<15}".format("---------------") + "---------------")
            for k in hosts:
                print("	" + "{:<15}".format(k) + hosts[k])
        else:
            if js.check_key('Host', args.show):
                print(args.show, ":", js.get_data('Host').get(args.show))
            else:
                print("Fail! Can't find " + args.show)
        return True

    # host删除
    def judge_hd(self, args, js):
        print("Delete the host <", args.iqnname, "> ...")
        if js.check_key('Host', args.iqnname):
            if js.check_value('HostGroup', args.iqnname):
                print("Fail! The host in ... hostgroup, Please delete the hostgroup first.")
            else:
                js.delete_data('Host', args.iqnname)
                print("Delete success!")
        else:
            print("Fail! Can't find " + args.iqnname)

    # disk查询
    def judge_ds(self, args, js):
        cd = crm()
        # data = cd.lsdata()
        data = cd.get_data_linstor()
        linstorlv = GetLinstor(data)
        disks = {}
        for d in linstorlv.get_data():
            disks.update({d[1]: d[5]})
        js.up_data('Disk', disks)
        if args.show == 'all' or args.show == None:
            print("	" + "{:<15}".format("Diskname") + "Path")
            print("	" + "{:<15}".format("---------------") + "---------------")
            for k in disks:
                print("	" + "{:<15}".format(k) + disks[k])
        else:
            if js.check_key('Disk', args.show):
                print(args.show, ":", js.get_data('Disk').get(args.show))
            else:
                print("Fail! Can't find " + args.show)

    # hostgroup创建
    def judge_hgc(self, args, js):
        print("hostgroupname:", args.hostgroupname)
        print("iqn name:", args.iqnname)
        if js.check_key('HostGroup', args.hostgroupname):
            print("Fail! The HostGroup " + args.hostgroupname + " already existed.")
            return False
        else:
            t = True
            for i in args.iqnname:
                if js.check_key('Host', i) == False:
                    t = False
                    print("Fail! Can't find " + i)
            if t:
                js.creat_data('HostGroup', args.hostgroupname, args.iqnname)
                print("Create success!")
                return True
            else:
                print("Fail! Please give the true name.")
                return False

    # hostgroup查询
    def judge_hgs(self, args, js):
        if args.show == 'all' or args.show == None:
            print("Hostgroup:")
            hostgroups = js.get_data("HostGroup")
            for k in hostgroups:
                print("	" + "---------------")
                print("	" + k + ":")
                for v in hostgroups[k]:
                    print("		" + v)
        else:
            if js.check_key('HostGroup', args.show):
                print(args.show + ":")
                for k in js.get_data('HostGroup').get(args.show):
                    print("	" + k)
            else:
                print("Fail! Can't find " + args.show)

    # hostgroup删除
    def judge_hgd(self, args, js):
        print("Delete the hostgroup <", args.hostgroupname, "> ...")
        if js.check_key('HostGroup', args.hostgroupname):
            if js.check_value('Map', args.hostgroupname):
                print("Fail! The hostgroup already map,Please delete the map")
            else:
                js.delete_data('HostGroup', args.hostgroupname)
                print("Delete success!")
        else:
            print("Fail! Can't find " + args.hostgroupname)

    # diskgroup创建
    def judge_dgc(self, args, js):
        print("diskgroupname:", args.diskgroupname)
        print("disk name:", args.diskname)
        if js.check_key('DiskGroup', args.diskgroupname):
            print("Fail! The DiskGroup " + args.diskgroupname + " already existed.")
            return False
        else:
            t = True
            for i in args.diskname:
                if js.check_key('Disk', i) == False:
                    t = False
                    print("Fail! Can't find " + i)
            if t:
                js.creat_data('DiskGroup', args.diskgroupname, args.diskname)
                print("Create success!")
                return True
            else:
                print("Fail! Please give the true name.")
                return False

    # diskgroup查询
    def judge_dgs(self, args, js):
        if args.show == 'all' or args.show == None:
            print("Diskgroup:")
            diskgroups = js.get_data("DiskGroup")
            for k in diskgroups:
                print("	" + "---------------")
                print("	" + k + ":")
                for v in diskgroups[k]:
                    print("		" + v)
        else:
            if js.check_key('DiskGroup', args.show):
                print(args.show + ":")
                for k in js.get_data('DiskGroup').get(args.show):
                    print("	" + k)
            else:
                print("Fail! Can't find " + args.show)

    # diskgroup删除
    def judge_dgd(self, args, js):
        print("Delete the diskgroup <", args.diskgroupname, "> ...")
        if js.check_key('DiskGroup', args.diskgroupname):
            if js.check_value('Map', args.diskgroupname):
                print("Fail! The diskgroup already map,Please delete the map")
            else:
                js.delete_data('DiskGroup', args.diskgroupname)
                print("Delete success!")
        else:
            print("Fail! Can't find " + args.diskgroupname)

    # map创建
    def judge_mc(self, args, js):
        print("map name:", args.mapname)
        print("hostgroup name:", args.hg)
        print("diskgroup name:", args.dg)
        if js.check_key('Map', args.mapname):
            print("The Map \"" + args.mapname + "\" already existed.")
            return False
        elif js.check_key('HostGroup', args.hg) == False:
            print("Can't find " + args.hg)
            return False
        elif js.check_key('DiskGroup', args.dg) == False:
            print("Can't find " + args.dg)
            return False
        else:
            if js.check_value('Map', args.dg) == True:
                print("The diskgroup already map")
                return False
            else:
                crmdata = self.crm_up(js)
                if crmdata:
                    mapdata = self.map_data(js, crmdata, args.hg, args.dg)
                    if self.map_crm_c(mapdata):
                        js.creat_data('Map', args.mapname, [args.hg, args.dg])
                        print("Create success!")
                        return True
                    else:
                        return False
                else:
                    return False

    # map查询
    def judge_ms(self, args, js):
        crmdata = self.crm_up(js)
        if args.show == 'all' or args.show == None:
            print("Map:")
            maps = js.get_data("Map")
            for k in maps:
                print("	" + "---------------")
                print("	" + k + ":")
                for v in maps[k]:
                    print("		" + v)
        else:
            if js.check_key('Map', args.show):
                print(args.show + ":")
                maplist = js.get_data('Map').get(args.show)
                print('	' + maplist[0] + ':')
                for i in js.get_data('HostGroup').get(maplist[0]):
                    print('		' + i + ': ' + js.get_data('Host').get(i))
                print('	' + maplist[1] + ':')
                for i in js.get_data('DiskGroup').get(maplist[1]):
                    print('		' + i + ': ' + js.get_data('Disk').get(i))
            else:
                print("Fail! Can't find " + args.show)

    # map删除
    def judge_md(self, args, js):
        print("Delete the map <", args.mapname, ">...")
        if js.check_key('Map', args.mapname):
            print(js.get_data('Map').get(args.mapname), "will probably be affected ")
            resname = self.map_data_d(js, args.mapname)
            if self.map_crm_d(resname):
                js.delete_data('Map', args.mapname)
                print("Delete success!")
        else:
            print("Fail! Can't find " + args.mapname)

    # 读取所有json文档的数据
    def judge_s(self, js):
        data = js.read_data_json()
        return data

    # 获取并更新crm信息
    def crm_up(self, js):
        cd = crm()
        crm_config_statu = cd.get_data_crm()
        if 'ERROR' in crm_config_statu:
            print("Could not perform requested operations, are you root?")
            return False
        else:
            redata = cd.re_data(crm_config_statu)
            js.up_crmconfig(redata)
            return redata

    # 获取创建map所需的数据
    def map_data(self, js, crmdata, hg, dg):
        mapdata = {}
        hostiqn = []
        for h in js.get_data('HostGroup').get(hg):
            iqn = js.get_data('Host').get(h)
            hostiqn.append(iqn)
        mapdata.update({'host_iqn': hostiqn})
        disk = js.get_data('DiskGroup').get(dg)
        cd = crm()
        data = cd.get_data_linstor()
        linstorlv = GetLinstor(data)
        print("get linstor r lv data")
        # print(linstorlv.get_data())
        diskd = {}
        for d in linstorlv.get_data():
            for i in disk:
                if i in d:
                    diskd.update({d[1]: [d[4], d[5]]})
        mapdata.update({'disk': diskd})
        mapdata.update({'target': crmdata[2]})
        # print(mapdata)
        return mapdata

    # 获取删除map所需的数据
    def map_data_d(self, js, mapname):
        dg = js.get_data('Map').get(mapname)[1]
        disk = js.get_data('DiskGroup').get(dg)
        return disk

    # 调用crm创建map
    def map_crm_c(self, mapdata):
        cd = crm()
        for i in mapdata['target']:
            target = i[0]
            targetiqn = i[1]
        # print(mapdata['disk'])
        for disk in mapdata['disk']:
            res = [disk, mapdata['disk'].get(disk)[0], mapdata['disk'].get(disk)[1]]
            if cd.createres(res, mapdata['host_iqn'], targetiqn):
                c = cd.createco(res[0], target)
                o = cd.createor(res[0], target)
                s = cd.resstart(res[0])
                if c and o and s:
                    print('create colocation and order success:', disk)
                else:
                    print("create colocation and order fail")
                    return False
            else:
                print('create resource Fail!')
                return False
        return True

    # 调用crm删除map
    def map_crm_d(self, resname):
        cd = crm()
        crm_config_statu = cd.get_data_crm()
        if 'ERROR' in crm_config_statu:
            print("Could not perform requested operations, are you root?")
            return False
        else:
            for disk in resname:
                if cd.delres(disk):
                    print("delete ", disk)
                else:
                    return False
            return True


if __name__ == '__main__':
    CLIParse()
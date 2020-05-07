#coding:utf-8
import colorama as ca
import prettytable as pt
import sqlite3,socket,subprocess,datetime,threading
import multiprocessing as mp
import regex



class LINSTORDB():
    #LINSTOR表
    crt_sptb_sql = '''
    create table if not exists storagepooltb(
        id integer primary key, 
        StoragePool varchar(20),
        Node varchar(20),
        Driver varchar(20),
        PoolName varchar(20),
        FreeCapacity varchar(20),
        TotalCapacity varchar(20),
        SupportsSnapshots varchar(20),
        State varchar(20)
        );'''

    crt_rtb_sql = '''
    create table if not exists resourcetb(
        id integer primary key,
        Node varchar(20),
        Resource varchar(20),
        Storagepool varchar(20),
        VolumeNr varchar(20),
        MinorNr varchar(20),
        DeviceName varchar(20),
        Allocated varchar(20),
        InUse varchar(20),
        State varchar(20)
        );'''

    crt_ntb_sql = '''
    create table if not exists nodetb(
        id integer primary key,
        Node varchar(20),
        NodeType varchar(20),
        Addresses varchar(20),
        State varchar(20)
        );'''

    crt_vgtb_sql = '''
        create table if not exists vgtb(
        id integer primary key,
        VG varchar(20),
        VSize varchar(20),
        VFree varchar(20)
        );'''

    crt_thinlvtb_sql = '''
        create table if not exists thinlvtb(
        id integer primary key,
        LV varchar(20),
        VG varchar(20),
        LSize varchar(20)
        );'''

    replace_stb_sql = '''
    replace into storagepooltb
    (
        id,
        StoragePool,
        Node,
        Driver,
        PoolName,
        FreeCapacity,
        TotalCapacity,
        SupportsSnapshots,
        State
        )
    values(?,?,?,?,?,?,?,?,?)
    '''

    replace_rtb_sql = '''
        replace into resourcetb
        (   
            id,
            Node,
            Resource,
            StoragePool,
            VolumeNr,
            MinorNr,
            DeviceName,
            Allocated,
            InUse,
            State
            )
        values(?,?,?,?,?,?,?,?,?,?)
    '''

    replace_ntb_sql = '''
        replace into nodetb
        (
            id,
            Node,
            NodeType,
            Addresses,
            State
            )
        values(?,?,?,?,?)
    '''

    replace_vgtb_sql = '''
        replace into vgtb
        (
            id,
            VG,
            VSize,
            VFree
            )
        values(?,?,?,?)
    '''

    replace_thinlvtb_sql = '''
        replace into thinlvtb
        (
            id,
            LV,
            VG,
            LSize
            )
        values(?,?,?,?)
    '''
    #连接数据库,创建光标对象
    def __init__(self):
        #linstor.db
        self.con = sqlite3.connect(":memory:", check_same_thread=False)
        self.cur = self.con.cursor()

    #执行获取数据，删除表，创建表，插入数据
    def rebuild_tb(self):
        self.drop_tb()
        self.create_tb()
        self.get_vg()
        self.get_thinlv()
        self.get_output()
        # self.create_tb()
        # self.run_insert()
        self.con.commit()

    def get_output(self):
        #threading
        threads = []

        thread_ins_node = threading.Thread(target=self.get_node())
        threads.append(thread_ins_node)
        thread_ins_res = threading.Thread(target=self.get_res())
        threads.append(thread_ins_res)
        thread_ins_sp = threading.Thread(target=self.get_sp())
        threads.append(thread_ins_sp)

        for i in range(len(threads)):
            threads[i].start()
        for i in range(len(threads)):
            threads[i].join()


    def get_vg(self):
        result_vg = subprocess.Popen('vgs',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output_vg = result_vg.stdout.read().decode()
        vg = regex.refine_vg(output_vg)
        self.insert_data(self.replace_vgtb_sql,vg)

    def get_thinlv(self):
        result_thinlv = subprocess.Popen('lvs',shell=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        output_thinlv = result_thinlv.stdout.read().decode()
        thinlv = regex.refine_thinlv(output_thinlv)
        self.insert_data(self.replace_thinlvtb_sql, thinlv)

    def get_node(self):
        result_node = subprocess.Popen('linstor --no-color --no-utf8 n l', shell=True, stdout=subprocess.PIPE,
                                       stderr=subprocess.STDOUT)
        output_node = result_node.stdout.read().decode('utf-8')
        node = regex.refine_linstor(output_node)
        self.insert_data(self.replace_ntb_sql,node)

    def get_res(self):
        result_res = subprocess.Popen('linstor --no-color --no-utf8 r lv', shell=True, stdout=subprocess.PIPE,
                                      stderr=subprocess.STDOUT)
        output_res = result_res.stdout.read().decode('utf-8')
        res = regex.refine_linstor(output_res)
        self.insert_data(self.replace_rtb_sql,res)

    def get_sp(self):
        result_sp = subprocess.Popen('linstor --no-color --no-utf8 sp l', shell=True, stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
        output_sp = result_sp.stdout.read().decode('utf-8')
        sp = regex.refine_linstor(output_sp)
        self.insert_data(self.replace_stb_sql,sp)


    #创建表
    def create_tb(self):
        self.cur.execute(self.crt_vgtb_sql)
        self.cur.execute(self.crt_thinlvtb_sql)
        self.cur.execute(self.crt_sptb_sql)#检查是否存在表，如不存在，则新创建表
        self.cur.execute(self.crt_rtb_sql)
        self.cur.execute(self.crt_ntb_sql)
        self.con.commit()

    #删除表，现不使用
    def drop_tb(self):
        tables_sql = "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        self.cur.execute(tables_sql)
        tables = self.cur.fetchall()
        for table in tables:
            drp_sql = "drop table if exists %s"%table
            self.cur.execute(drp_sql)
        self.con.commit()


    def insert_data(self,sql,list_data):
        for i in range(len(list_data)):
            list_data[i].insert(0,i+1)
            self.cur.execute(sql,list_data[i])



    def data_base_dump(self):
        cur = self.cur
        con = self.con
        self.rebuild_tb()
        SQL_script = con.iterdump()
        cur.close()
        return "\n".join(SQL_script)



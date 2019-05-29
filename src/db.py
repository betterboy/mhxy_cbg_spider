#!/usr/bin/python3
# -*- coding: utf-8 -*-

#封装相关数据库操作
import redis
import pymysql
import sys
import time
import os
import queue
from src.util import MyLogger
from src.util import ConfigParse


config = ConfigParse()
config.read()

def get_config_field(section, key):
    return config.get_config_field(section, key)


class Redis(object):
    def __init__(self):
        self._port = get_config_field('redis', 'PORT')
        self._ip = get_config_field('redis', 'IP')
        self._db = get_config_field('redis', 'DB')

    def get_connection(self):
        pool = redis.ConnectionPool(
            host=self._ip, port=self._port, db=self._db)
        return redis.Redis(connection_pool=pool)


class MysqlPool(object):
    def __init__(self, maxconn=8, db=None):
        self._port = int(get_config_field('mysql', 'PORT'))
        self._ip = get_config_field('mysql', 'IP')
        self._user = get_config_field('mysql', 'USER')
        self._passwd = get_config_field('mysql', 'PASSWD')
        self._pool_size = maxconn
        if db == None:
            db = get_config_field('mysql', 'DB')
        self._db = db

    def create_conn(self):
        try:
            conn = pymysql.connect(host=self._ip,
                                   port=self._port,
                                   user=self._user,
                                   passwd=self._passwd,
                                   db=self._db,
                                   cursorclass=pymysql.cursors.DictCursor
                                   )
            return conn
        except Exception as e:
            print("create connection failed. error:", e)
            return None

    def init(self):
        self.pool = queue.Queue()
        for i in range(self._pool_size):
            conn = self.create_conn()
            if conn:
                self.pool.put(conn)

    def get_connection(self):
        if self.pool.empty():
            conn = self.create_conn()
            return conn
        else:
            return self.pool.get()

    def release(self, conn):
        #conn.ping(reconnect=True)
        self.pool.put(conn)

    def close(self):
        while not self.pool.empty():
            conn = self.pool.get()
            conn.close()
    

def equip_upsert(conn, upsert_list):
    sql = ('insert into equip (game_ordersn, producer, brief_desc, price_int, equip_name, server_name,'
        'equip_level, info_dumps, date) values(%(game_ordersn)s, %(producer)s, %(brief_desc)s, %(price_int)s,'
            '%(equip_name)s, %(server_name)s, %(equip_level)s, %(info_dumps)s, current_timestamp) on duplicate key update '
                'price_int=%(price_int)s, server_name=%(server_name)s, brief_desc=%(brief_desc)s;')
    cursor = conn.cursor()
    for data in upsert_list:
        print(data['equip_name'])
        cursor.execute(sql, data)
        conn.commit()
    cursor.close()


def create_equip_table(conn):
    sql = ('create table if not exists equip (game_ordersn varchar(30) not null,'
                                                'producer varchar(20) not null,'
                                                'brief_desc varchar(512) not null,'
                                                'price_int int not null,'
                                                'equip_name varchar(20) not null,'
                                                'server_name varchar(20) not null,'
                                                'equip_level int not null,'
                                                'info_dumps text not null,'
                                                'date datetime not null default CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,'
                                                'primary key(game_ordersn)) engine=Innodb default charset=utf8;')

    cursor = conn.cursor()
    cursor.execute(sql)
    conn.commit()
    cursor.close()


def lingshi_upsert(conn, upsert_list):
    pass

def get_test_data():
    data  = {
        'game_ordersn': '222222',
        'producer': 'xyq2',
        'brief_desc': u'测试信h',
        'price_int': 120,
        'equip_name': 'equip',
        'server_name': 'server_name',
        'equip_level': 150,
        'info_dumps':'dumps_info'
    }
    return [data]
    

if __name__ == "__main__":
    pool = MysqlPool(maxconn=8, db='xyq2')
    pool.init()
    conn = pool.get_connection()
    cursor = conn.cursor()
    cursor.execute('select version()')
    create_equip_table(conn)

    pool.close()

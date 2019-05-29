import sys
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.equip_spider import EquipSpider
from src.db import create_equip_table
from src.db import MysqlPool
import etc.settings


def equip_spider_task(conn, kindid, name):
    equip_spider = EquipSpider(kindid, conn)
    equip_spider.run()
    return name


def start_equip_spider():
    conn_pool = MysqlPool(maxconn=16, db='xyq2')
    conn_pool.init()
    equip_kinds = etc.settings.EquipKinds
    executer = ThreadPoolExecutor(max_workers=4)
    all_tasks = []
    conn = conn_pool.get_connection()
    create_equip_table(conn)
    conn_pool.release(conn)
    for id, name in equip_kinds.items():
        print(id, name)
        conn = conn_pool.get_connection()
        all_tasks.append(executer.submit(equip_spider_task, conn, id, name))
    for future in as_completed(all_tasks):
        data = future.result()
        print("Task %d completed!" % data)
    conn_pool.close()


if __name__ == "__main__":
    start_equip_spider()
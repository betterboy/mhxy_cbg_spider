#! -*- coding: utf-8 -*-
#装备查询

import sys
import sys
import time
import json
import re
import requests
import threading

from src.base_spider import BaseSpider
from src.util import MyLogger
import src.request_util
from src.db import MysqlPool
from src.db import equip_upsert

PAGE_MAX = 100
PRICE_MAX = 1000000

equip_log = MyLogger().new('equip.log')

class EquipSpider(BaseSpider):
    def __init__(self, kind_id, sql_conn, query_url=r'https://recommd.xyq.cbg.163.com/cgi-bin/recommend.py'):
        super(EquipSpider, self).__init__()
        self.kind_id = kind_id
        self.callback_index = 1
        self.proxy_fetcher = src.request_util.get_proxy_fetcher()
        self.query_url = query_url
        self.query_succ = 0
        self.query_fail = 0
        self.conn = sql_conn
    
    def get_query_params(self, price_min, price_max, page):
        return {
            'callback': 'Request.JSONP.request_map.request_%d' % self.callback_index,
            'act': 'recommd_by_role',
            'page':page, 
            'level_min': 90,
            'level_max': 160,
            'price_min': price_min * 100,
            'price_max': price_max * 100,
            'kindid': self.kind_id,
            'sum_attr_without_melt': 1,
            'count': 15,
            'search_type': 'overall_search_equip',
            'view_loc': 'overall_search'
        }
    
    @staticmethod
    def get_producer(desc):
        desc = re.sub(r"#Y", "|", desc)
        desc = re.sub(r"#[a-zA-Z]|[A-Z0-9]", "", desc)
        desc = re.sub(r" ", "", desc)
        desc = re.sub(r"强化打造", "", desc)
        lists = desc.split("|")
        for _k in lists:
            if "制造者" in _k:
                name = _k.split("：")[-1]
                return name
    
    def get_session(self):
        sess = requests.Session()
        header = src.request_util.get_header()
        header['Referer'] = 'https://xyq.cbg.163.com/cgi-bin/equipquery.py?act=show_overall_search_equip'
        sess.headers.update(header)
        return sess
    
    def get_proxies(self):
        proxies = {}
        proxy_list = self.proxy_fetcher.get_proxies()
        if len(proxies) < 2: return proxies
        proxies['http'] = proxy_list[0]
        proxies['https'] = proxies[1]
        return proxies
    
    @staticmethod
    def check_status_code(status_code):
        """
        藏宝阁自己的状态码，如果被屏蔽回返回不同的状态码,暂时不处理
        TODO: 处理验证码情况
        """
        equip_log.debug("Status code return. code=%d", status_code)
        if status_code != 1:
            return False
        return True
    
    def parse_and_save(self, data):
        """
        @param
        data: json格式的原始数据
        return: 返回[{}], 包含了装备数据
        """
        #当查询范围过小时，equips可能为空，这是正常情况
        equips_list = data['equips']
        if not equips_list: return
        #解析出制造者，然后打包插入数据库
        upsert_list = []
        for equip in equips_list:
            fixed_data = {}
            other_info = equip['other_info']
            desc = json.loads(other_info)['desc']
            producer = self.get_producer(desc)
            fixed_data['producer'] = producer
            fixed_data['brief_desc'] = desc
            fixed_data['price_int'] = equip['price_int']
            fixed_data['equip_name'] = equip['equip_name']
            fixed_data['server_name'] = equip['server_name']
            fixed_data['equip_level'] = equip['equip_level']
            fixed_data['info_dumps'] = json.dumps(equip)
            fixed_data['game_ordersn'] = equip['game_ordersn']
            upsert_list.append(fixed_data)
        
        equip_upsert(self.conn, upsert_list)

    def query_single_page(self, sess, page, price_min, price_max):
        equip_log.info("Request page: price_min=%d,price_max=%d,page=%d", price_min, price_max, page)
        params = self.get_query_params(price_min, price_max, page)
        try:
            proxies = self.get_proxies()
            response = sess.get(self.query_url, params=params, proxies=proxies)
        except Exception as e:
            print("Request error:", e)
            time.sleep(5)
            return None, ""
        if response.status_code != requests.codes.ok:
            equip_log.error("Request status code=%d", response.status_code)
            return None, response.text
        page_data = src.request_util.loads_jsonp(response.text)
        if not page_data:
            equip_log.error("loads jsonp error:%s", response.text)
            return None, response.text
        if not self.check_status_code(page_data['status']): return None, response.text
        self.callback_index = self.callback_index + 1
        return page_data, response.text


    def query_by_range(self, sess, price_min, price_max):
        """
        按价格返回查询装备数据
        @return boolean, price_max -- 第一个值表示是否正常查询，第二个值表示此次查询所用的price_max
        """
        cur_page = 1
        #先取一页确定价格范围
        page1_data, text = self.query_single_page(sess, cur_page, price_min, price_max)
        if not page1_data:
            self.query_fail = self.query_fail + 1
            equip_log.error("Request page data error. text=%s", text)
            return False, price_max
        self.query_succ = self.query_succ + 1
        if not page1_data['equips']: return True, price_max
        total_page = page1_data["pager"]["total_pages"]
        if total_page >= PAGE_MAX:
            price_max = price_min + (price_max - price_min) / 2
            return True, price_max

        for i in range(cur_page, total_page+1):
            page_data, text = self.query_single_page(sess, i, price_min, price_max)
            if not page_data:
                equip_log.error('Request single page failed. index=%d,price_min=%d,price_max=%d',
                                    i, price_min, price_max)
                continue
            self.parse_and_save(page_data)
        return True, price_max

    def run(self):
        price_min = 300
        price_max = 301
        range = 10
        sess = self.get_session()
        while True:
            ret, cur_price_max = self.query_by_range(sess, price_min, price_max)
            equip_log.info('Request stat. succ=%d,fail=%d', self.query_succ, self.query_fail)
            if not ret:
                time.sleep(1)
                equip_log.debug('Request range failed.')
                continue
            if cur_price_max >= PRICE_MAX: return

            #价格范围太大，缩小返回重新查询
            if cur_price_max < price_max:
                range = range / 2
            else:
                range = range * 2
            price_min = cur_price_max + 1
            price_max = min(price_min + range, PRICE_MAX)
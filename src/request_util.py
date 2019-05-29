# -*- coding: utf-8 -*-
#这里主要负责自定义request，包括代理，header等
import random
import os
import json
import re
from src.db import get_config_field
from haipproxy.client.py_cli import ProxyFetcher


HEADER_LIST = []

def get_proxy_fetcher():
    """
    需要维护自己的代理，你可以在这里封装自己的代理。
    """
    host = get_config_field('redis', 'IP')
    port = get_config_field('redis', 'PORT')
    db = get_config_field('redis', 'DB')
    args = dict(host=host, port=port, password='', db=db)
    return ProxyFetcher('zhihu', strategy='greedy', redis_args=args)


def get_user_agent():
    global HEADER_LIST
    if not HEADER_LIST:
        file_name = os.path.join(os.path.abspath('.'), 'etc/user_agents.txt')
        with open(file_name, 'r') as fr:
            for line in fr.readlines():
                HEADER_LIST.append(line)

    return random.choice(HEADER_LIST).strip()


def get_header():
    header = {}
    header["Accept"] = 'application/json; text/javascript; charset=UTF-8'
    header["User-Agent"] = get_user_agent()
    return header

def loads_jsonp(jsonp):
    try:
        return json.loads(re.match(r'.*?({.*}).*', jsonp, re.S).group(1))
    except Exception:
        return {}


if __name__ == "__main__":
    print(get_header())
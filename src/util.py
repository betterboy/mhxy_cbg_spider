#!/usr/bin/python3
#-*- coding:utf-8 -*-

import logging
import logging.handlers
import sys
import os
from configparser import ConfigParser

class ConfigParse(object):
    """封装一个配置文件解析类"""
    def __init__(self, file_name='config.ini'):
        file_name = os.path.join(os.path.abspath('.'), 'etc/' + file_name)
        self._config_file_name = file_name

    def read(self):
        try:
            self.parse = ConfigParser()
            self.parse.read(self._config_file_name)
        except Exception as e:
            print("ConfigParse read file failed. err= ", e)
            exit()

    def get_config_field(self, section, key):
        value = ''
        try:
            value = self.parse.get(section, key)
        except Exception:
            pass
        return value


class MyLogger(object):
    def __init__(self):
        pass

    def new(self, filename, logger=None):
        self.logger = logging.getLogger(logger)
        self.logger.setLevel(logging.DEBUG)
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(filename)s %(funcName)s %(message)s')

        log_dir = os.path.join(os.path.abspath('.'), 'log/')
        if not os.path.exists(log_dir): os.mkdir(log_dir)

        filename = os.path.join(log_dir + filename)
        time_file_handler = logging.handlers.TimedRotatingFileHandler(filename=filename, when='H')
        time_file_handler.setFormatter(fmt)

        stream_file_handler = logging.StreamHandler()
        stream_file_handler.setFormatter(fmt)

        self.logger.addHandler(time_file_handler)
        self.logger.addHandler(stream_file_handler)
        return self.logger

        
if __name__ == "__main__":
    config = ConfigParse()
    config.read()
    print(config.get_config_field('redis', 'PORT'))
    

        


        

#!/usr/bin/python
#-*- coding: utf-8 -*-
"""통계 수집 프로세스인 statistics.py 모듈을 테스트
@since 2016-09-19
"""

import yaml
from util import statistics

import util.statistics_model as model

from util import gsf 
from handler import rrl_handler as rrl

TITLE = 'generator'
TITLE_FAULT = 'faultmsg'
TITLE_API = 'generator'
from util.ko_logger import ko_logger
logger = ko_logger(tag=TITLE, logdir="./log/", loglevel="debug", logConsole=False).get_instance()

import time
import datetime

# AES
from util.aes_cipher import AESCipher

# configuration
def loadConfig(cfgName):
    """
    - FUNC: Orch-M의 설정 파일 로딩
    - INPUT
        cfgName(M): 설정 파일이름
    - OUTPUT : 설정 파일 Dict
    """
    logger.info( rrl.lI2('load Config : fName=%s'%cfgName) )

    with open(cfgName, "r") as f:
        cfgf = yaml.load(f)

    gVar = gsf.VarShared( cfgf['gVar'] )
    cfgf['gVar'] = gVar

    # 2017. 11. 14 - lsh
    # AES Decrypt
    cipher=AESCipher(cfgf['orchm_salt'] , cfgf['orchm_code'] )
    cfgf['mysql_passwd'] = cipher.decrypt(cfgf['mysql_passwd'] )
    cfgf['db_passwd'] = cipher.decrypt(cfgf['db_passwd'] )
    cfgf['zb_passwd'] = cipher.decrypt(cfgf['zb_passwd'] )
    cfgf['zb_db_passwd'] = cipher.decrypt(cfgf['zb_db_passwd'] )

    return cfgf

if __name__ == '__main__':
    cfgName = './cfg/orchm.cfg'
    cfg = loadConfig(cfgName)

    # 통계 데이터 생성
    g = statistics.generateData(cfg, logger)
    g.run()

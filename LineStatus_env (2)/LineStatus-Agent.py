# -*- coding: utf-8 -*-
# KT 회선 상태 체크, 2020. 6.23, LSH
# OLT 에 연결된 포트 상태를 SNMP 를 이용하여 체크한다.

import logging
import logging.handlers
import urllib2, ssl

import base64
import hashlib
from Crypto import Random
from Crypto.Cipher import AES

from util.aes_cipher import AESCipher
from util import db_sql
from util import snmp_info
from util import allinhome_api
from pysnmp import hlapi

from multiprocessing import Lock
from threading import Timer,Thread

import multiprocessing as mp
import os, time, json
import datetime

import psycopg2
import psycopg2.extras

import pymysql
import yaml

# 멀티프로세서 사용시 변수 동시 접근 금지.
lock = Lock()

# POOL 개수
MAX_POOL = 10
# 반복주기
REPEAT_CYCLE = 180
# DB 회선상태 결과값 저장 주기
LOOP_TIME = 10

# AES Key
AES_KEY = '79715953B9D5CED9'
BS=16
PAD = lambda s: s + (BS - len(s) % BS) * chr(BS - len(s) % BS) 
UNPAD = (lambda s: s[:-ord(s[len(s)-1:])])

# 환경파일
CFG_INFO = {}

OLD_DATE = ''

# 라인 정보.
LST_LINE_INFO = []

# SNMP 사용불가 장비, API 로 상태 조회가 필요한 장비명
LST_USE_API = ('MVD5048', 'MVD5024', 'HAMX-6000E')

# noti request
HEADER = { "content-Type": "application/json;charset=UTF-8", "accept":"application/json" }
SNMPGET = "snmpget -%s -c %s %s %s"



# item-value 값이 있어야함.
# status_code = 0 은 해제, 1 은 발생 
NOTI_JSON =  {
    'body': {
        'item': [
        {
            'key': 'icmpping[]',
            'value': '0'
        }
        ],
        'host': {
            'ip': '%s',
            'name': '%s'
        },
        'trigger': {
            'status_code': '0',
            'name': '[critical] 회선 연결 상태 Fault',
            'grade_code': '5'
        },
        'event': {
            'date': '%s',
            'time': '%s'
        },
    'isLineStatus' : 'True'
  }
}

# 로거 인스턴스 생성
logger = logging.getLogger("mylogger")


# 회선 정보
class LineInfo ():
    def __init__(self, info):
        # self.line_seq= ''
        self.snmp_read = info['snmp_read']
        # self.product_nm = ''
        self.port_oid = info['port_oid']
        self.line_num = info['line_num']
        # self.svcmain_type = svcmain_type
        # self.said = ''
        # self.modem_reset_yn = ''
        # self.ont_mac = ''
        self.snmp_ver = info['snmp_ver']
        self.equip_ip = info['equip_ip']
        self.status = info['status']
        self.model_name = info['model_name']
        self.dttm = ''
        self.value = '0'
        self.ErrMessage = ''

        # API 호출용 라인번호 암호화
        self.encrypt_line_num = self.fn_enc_line_num()
    
    def fn_enc_line_num(self) :
        # MVD5048 모델은 SNMP 가 아니라 API 호출방식으로 상태 조회
        # API 호출시 AES 암호화 필요. KEY = 79715953B9D5CED9
        if self.model_name in LST_USE_API :
            raw = PAD(self.line_num)
            cipher = AES.new(AES_KEY, AES.MODE_ECB)
            enc = cipher.encrypt(raw).encode("hex")
            return enc
            # return base64.b64encode(enc).decode('utf-8')            
        else :
            return ""


def init() :
    global CFG_INFO
    global MAX_POOL
    global REPEAT_CYCLE

    CFG_INFO = loadConfig()

    path = os.getcwd()

    # MultiProcess 개수 conf 에 정의 Default 10 개.
    MAX_POOL = CFG_INFO['multiprocess'] if CFG_INFO.has_key('multiprocess') else MAX_POOL
    REPEAT_CYCLE = CFG_INFO['repeat_cycle'] if CFG_INFO.has_key('repeat_cycle') else REPEAT_CYCLE


    if not os.path.isdir(path + '/log') :
        os.mkdir(path + '/log')
        
    # 포매터를 만든다
    formatter = logging.Formatter(' [%(asctime)s][%(levelname)s|%(filename)s:%(lineno)s] %(message)s')

    fileMaxByte = 1024 * 1024 * 10  # 10MB

    # 화면, 파일 각각 핸들러 생성
    filename = path + "/log/lineStatus.log"
    fileHandler = logging.handlers.RotatingFileHandler(filename, maxBytes=fileMaxByte, backupCount=10)

    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)

    # 핸들러를 생성된 logger 에 추가한다.
    logger.addHandler(fileHandler)
    logger.addHandler(streamHandler)
    logger.setLevel(logging.DEBUG)


def setArg( arg, argName, noneType=None ):
    return (lambda x: x[argName] if x.has_key(argName) else noneType)(arg)


def send_req (reqBody) :
    strBody = json.dumps( reqBody )
    req = urllib2.Request(CFG_INFO['orchm_url'], strBody, HEADER)
    for i in range(3) :
        try :
            response = urllib2.urlopen(req, context=ssl._create_unverified_context())    
            break
        except Exception as e :
            logger.error (" count : %s, message : %s " % ( str(i+1), str(e)) )
            time.sleep(3)

    # retBody = response.read()
    # logger.info ("responese : %s " % retBody)


def loadConfig():
    """
    - FUNC:설정 파일 로딩
    - OUTPUT : 설정 파일 Dict
    """

    path = os.getcwd()
    cfgName = path + '/cfg/LineStatus-Agent.conf'
    with open(cfgName, "r") as f:
        cfgf = yaml.load(f)

    # AES Decrypt
    cipher=AESCipher(cfgf['orchm_salt'] , cfgf['orchm_code'] )
    cfgf['db_passwd'] = cipher.decrypt(cfgf['db_passwd'] )

    return cfgf

def Load_LineInfo( ):
    global LST_LINE_INFO
    global OLD_DATE

    #  날짜 바뀌면, DB 값 모두 가져온다.
    bALL = OLD_DATE <> time.strftime('%Y-%m-%d', time.localtime(time.time()))

    # 최근 수정된 Data ( modify_dttm ) 을 기준으로 조회한다.
    # 조건은 conf 의 repeat_cycle (초)  + 2분 (동작시간) 추가 한다.
    BeforeTime = int ( REPEAT_CYCLE / 60 ) + 2

    dbConn = None
    try:
        if CFG_INFO['db_type'] == 'postgresql' :
            dbConn = psycopg2.connect( database=CFG_INFO['db_name'], user=CFG_INFO['db_user'], password=CFG_INFO['db_passwd'], 
                host=CFG_INFO['db_addr'], port=int(CFG_INFO['db_port']), application_name='LineStatus-Agent' )
            dbConn.autocommit = True
            cur = dbConn.cursor(cursor_factory=psycopg2.extras.DictCursor)

        else : 
            dbConn = pymysql.connect(host=CFG_INFO['db_addr'], port=int(CFG_INFO['db_port']), user=CFG_INFO['db_user'], passwd=CFG_INFO['db_passwd'], db=CFG_INFO['db_name'],  autocommit=True, charset='utf8')
            cur = dbConn.cursor(pymysql.cursors.DictCursor)            

        if bALL :
            # 21. 5.25
            # snmp 정보가 없는 장비,  status 값 N 처리.
            cur.execute(db_sql.UPDATE_STATUS_N()) 

            cur.execute(db_sql.GET_LINE_INFO_ALL()) 
        else :
            cur.execute(db_sql.GET_LINE_INFO(CFG_INFO['db_type'], BeforeTime)) 
        rows = cur.fetchall() 
        cur.close() 


        if len(rows) <> 0 :
            logger.info ( " Get Lines Info : %s" % rows )
            logger.info ( " Get Lines Count : %s" % len(rows ))

    except Exception as e: 
        logger.error ( 'Error : %s ' % e )
    finally: 
        if dbConn: 
            dbConn.close()

    lst_lineinfos = []
    lst_lineinfos = [ LineInfo( r ) for r in rows ]

    if len(lst_lineinfos) == 0 :
        return

    # init 시 Status 값을 Value 에 반영
    for r in lst_lineinfos :
        r.value = '1' if r.status == 'Y' else '0'

    # 모두 갱신 ( 날짜가 바뀌었다. )
    if bALL :
        # print ( rows )
        OLD_DATE = time.strftime('%Y-%m-%d', time.localtime(time.time()))
        del LST_LINE_INFO[:]
        LST_LINE_INFO = lst_lineinfos
    else :
        # 갱신.
        if len(lst_lineinfos) > 0 : 
            #  같은 line_num 삭제하고, 마지막 모두 추가. 

            for r in lst_lineinfos :
                for i in reversed(range(len(LST_LINE_INFO))) :
                    if r.line_num == LST_LINE_INFO[i].line_num :
                        del LST_LINE_INFO[i]
            # 추가.
            LST_LINE_INFO.extend(lst_lineinfos)
    return

def noti_data():
    dbConn = psycopg2.connect( database=CFG_INFO['db_name'], user=CFG_INFO['db_user'], password=CFG_INFO['db_passwd'], 
        host=CFG_INFO['db_addr'], port=int(CFG_INFO['db_port']), application_name='LineStatus-Agent' )
    dbConn.autocommit = True
    cur = dbConn.cursor(cursor_factory=psycopg2.extras.DictCursor)

    logger.info ( "Send Noti Start" )

    for r in result_list :
        for line in LST_LINE_INFO :
            if r.line_num == line.line_num : 
                if str(r.value) <> str(line.value) :

                    logger.info ( "%s <> %s" % (r.value, line.value))
                    # 현재 상태값 반영
                    line.value = r.value
                    # Noti 준비.
                    cur.execute(db_sql.GET_LINENUM_TO_SERVERNAME(r.line_num))
                    rows = cur.fetchall() 
                    onebox_id = rows[0]['servername']
                    onebox_ip = rows[0]['mgmtip']

                    NOTI_JSON['body']['host']['ip'] = onebox_ip
                    NOTI_JSON['body']['host']['name'] = onebox_id

                    NOTI_JSON['body']['trigger']['status_code'] = '1' if r.value == '0' else '0'
                    # noti['body']['trigger']['name'] = '[critical] 회선 연결 상태 Fault'

                    NOTI_JSON['body']['event']['date'] = r.dttm.strftime('%Y.%m.%d')
                    NOTI_JSON['body']['event']['time'] = r.dttm.strftime('%H:%M:%S') 

                    logger.info ( " Noti String : %s" % NOTI_JSON )
                    send_req (NOTI_JSON)

    cur.close() 

def save_data():
    dbConn = None
    try:
        CFG_INFO = loadConfig()
        if CFG_INFO['db_type'] == 'postgresql' :
            dbConn = psycopg2.connect( database=CFG_INFO['db_name'], user=CFG_INFO['db_user'], password=CFG_INFO['db_passwd'], 
                host=CFG_INFO['db_addr'], port=int(CFG_INFO['db_port']), application_name='LineStatus-Agent' )
            dbConn.autocommit = True
            cur = dbConn.cursor(cursor_factory=psycopg2.extras.DictCursor)
        else : 
            dbConn = pymysql.connect(host=CFG_INFO['db_addr'], port=int(CFG_INFO['db_port']), user=CFG_INFO['db_user'], passwd=CFG_INFO['db_passwd'], db=CFG_INFO['db_name'], autocommit=True, charset='utf8')
            cur = dbConn.cursor(pymysql.cursors.DictCursor)            


        sql = " INSERT INTO tb_line_status ( mon_dttm, line_num, value ) VALUES " 
        sql_add = ''
        for r in result_list :
            if sql_add <> '' :
                sql_add += ", "

            if CFG_INFO['db_type'] == 'postgresql' :
                sql_add += "( TIMESTAMP '%s', '%s', %s )" % ( r.dttm, r.line_num, r.value) 
            else : # MySql
                sql_add += "( '%s', '%s', %s )" % ( r.dttm.strftime('%Y-%m-%d %H:%M:%S'), r.line_num, r.value) 

        sql += sql_add

        # logger.info (sql)

        cur.execute(sql) 
        rowcount = cur.rowcount

        logger.info ( "Insert count : %s" % rowcount)


        # tb_onebox_line_detail, status 값 UPDATE Y or N
        # 0 ~ 1 루프
        for i in range(2) :
            Y_N = "Y" if i == 1 else "N"
            sql = " UPDATE tb_onebox_line_detail SET status = '%s' WHERE del_yn = 'N' AND line_num in ( " % Y_N

            sql_add = ''
            for r in result_list :
                if r.value == str(i) :
                    if sql_add <> '' :
                        sql_add += ", "

                    sql_add += " '%s' " % ( r.line_num ) 

            sql += sql_add + " ) "

            if sql_add == '' :
                continue

            # logger.info (sql)

            cur.execute(sql) 
            rowcount = cur.rowcount            
            logger.info ( "Update count : %s" % rowcount)

    except Exception as e: 
        print 'Error : ', e 
    finally: 
        if dbConn: 
            dbConn.close()

result_list = []

def callback_result(line_info):

    # SNMP OID 결과값을 Callback 에서 받는다. 
    lock.acquire()
    try:
        result_list.append(line_info)

        # logger.info ( line_info.equip_ip )
        # logger.info ( line_info.value)

        if line_info.value == "0" :
            logger.info ( "Error line number %s,  Message : %s " % ( line_info.line_num, line_info.ErrMessage ) )
            if line_info.model_name in LST_USE_API :
                logger.info ( "Test cmd : curl -k http://10.220.175.123/api/lineInfo/ONEBOX/" + line_info.encrypt_line_num)
            else :
                logger.info ( "Test cmd : " + SNMPGET % ( line_info.snmp_ver, line_info.snmp_read, line_info.equip_ip, line_info.port_oid ))

        # time.sleep(1)
    finally:
        lock.release()    


def Start_Get_Snmp():
 
    # 회선 정보 가져오기
    Load_LineInfo()

    if len(LST_LINE_INFO) == 0 :
        logger.error ( "Fail, Load_LineInfo()" )
        return

    pool = mp.Pool(MAX_POOL)

    for r in LST_LINE_INFO :
        if r.model_name in LST_USE_API :
            pool.apply_async(allinhome_api.callAPI, args=( r, ), callback = callback_result)
        else :
            pool.apply_async(snmp_info.getSnmp, args=( r, ), callback = callback_result)

    pool.close()
    pool.join()

    # logger.info (CFG_INFO['db_type'])
    # 장애 알람.
    if CFG_INFO['db_type'] == 'postgresql' :
        noti_data()


    save_data()


if __name__ == '__main__':
    init()

    test_mode = False
    # test_mode = CFG_INFO['db_addr'] == '211.224.204.203'

    if test_mode : 
        Start_Get_Snmp()        
    else :
        while True :
            del result_list[:]
            try : 
                Start_Get_Snmp()
            except Exception as e: 
                logger.error ( ' Start_Get_Snmp : %s ' % e )

            logger.info ( "== Wait %s seconds for next job == " % REPEAT_CYCLE)
            time.sleep ( REPEAT_CYCLE )

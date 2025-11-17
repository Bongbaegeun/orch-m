#-*- coding: utf-8 -*-
"""통계 데이터 생성을 위한 모듈

@since 2016-09-12
"""

from util import db_mng
import threading
import psycopg2

import time

class copyZbToOrchmModel():
    zb = None
    zbCur = None
    
    orch = None
    orchCur = None
    
    logger = None
    
    def __init__(self, logger, cfg):
        self.logger = logger

        self.zb = db_mng.makeZbDbConn(cfg)  # 자빅스 DB 연결 객체
        self.zbCur = self.zb.cursor()       # 자빅스 DB 커서

        self.orch = db_mng.makeDbConn(cfg)  # Orch-M DB 연결 객체
        self.orchCur = self.orch.cursor()   # Orch-M DB 커서

    def zb_createTable(self):
        """자빅스에 설정 테이블을 생성
        """
        sql = """CREATE TABLE orchm_statics (
            moniteminstanceseq	integer
        ,	serverseq	integer
        ,	servername	varchar(255)
        ,	monitemkey	varchar(255)
        ,	data_type	varchar(5)
        )
        """
        self.zbCur.execute(sql)

    def zb_existsTable(self):
        """자빅스에 통계 테이블이 존재하는지 검사
        """
        sql = """
            SELECT EXISTS (
            SELECT 1
            FROM   information_schema.tables 
            WHERE  table_schema = 'public'
                AND    table_name = 'orchm_statics'
            )"""
        self.zbCur.execute(sql)
        rst = self.zbCur.fetchone()
        return rst[0]

    def zb_deleteConfig(self):
        """기존 설정 데이터 삭제
        """
        # sql = "DELETE FROM orchm_statics"
        sql = "TRUNCATE orchm_statics"
        self.zbCur.execute(sql)

    def copyConfig(self):
        """Orch-M DB 의 설정 정보를 Zabbix DB에 복사
        """
        
        # Orch-M DB에서 설정 정보 불러오기
        sql = """SELECT
            ii.moniteminstanceseq, zbki.serverseq, s.servername, zbki.monitemkey, ii.data_type
            FROM tb_mapzbkeyinstance as zbki
            LEFT OUTER JOIN tb_moniteminstance ii on zbki.moniteminstanceseq=ii.moniteminstanceseq
            LEFT OUTER JOIN tb_server s ON s.serverseq=zbki.serverseq
            INNER JOIN tb_maphostinstance hi ON hi.serverseq = s.serverseq
            WHERE ii.delete_dttm is null
                AND ii.statistics_yn = 'y'"""
        self.orchCur.execute(sql)
        items = self.orchCur.fetchall()

        # Zabbix 에 설정 정보 등록하기
        sql = """INSERT INTO orchm_statics
        (moniteminstanceseq, serverseq, servername, monitemkey, data_type)
        VALUES
        """

        # 18. 8.13 - LSH
        # 각각 insert 하던것을 한번에 Insert 하도록 변경함
        SubSql = ""
        for i, item in enumerate (items) :
            if i > 0 : 
                SubSql += ","
            SubSql += """ (%s, %s, '%s', '%s', '%s') """ % ( item[0], item[1], item[2], item[3], item[4] )
            
        sql += SubSql
        self.zbCur.execute(sql)
    
    def _copyHistory(self, startTime, endTime):
        """float 형식의 데이터를 Orch-M DB에 복사
        """
        # Zabbix 에서 조건에 해당하는 데이터 불러오기
        sql = """select o.moniteminstanceseq, his.clock, his.value from orchm_statics o
            left join hosts h on o.servername = h.name
            left join items i on o.monitemkey=i.key_ AND h.hostid = i.hostid
            left join history_uint his on i.itemid=his.itemid
            where o.data_type = 'int' and his.clock >= %s and his.clock < %s
            order by his.clock"""
        param = [startTime, endTime]
        self.zbCur.execute(sql, param)
        values = self.zbCur.fetchall()

        self.logger.info(sql)
        self.logger.info(param)

        # 18. 8.13 - LSH
        # 각각 insert 하던것을 한번에 Insert 하도록 변경함
        sql = """INSERT INTO tb_monitemhistory_int
            (moniteminstanceseq, clock, value) 
            VALUES 
            """
        SubSql = ""
        for i, value in enumerate(values) :
            if i > 0 : 
                SubSql += ","
            SubSql += """ (%s, %s, %s) """ % ( value[0], value[1], value[2] )
            
        sql += SubSql
        # print sql
        try:
            self.orchCur.execute(sql)
        except psycopg2.Error as e:
            print e
            
    def _copyHistoryFloat(self, startTime, endTime):
        """unsigned int 형식의 데이터를 Orch-M DB에 복사
        """
        # Zabbix 에서 조건에 해당하는 데이터 불러오기
        sql = """SELECT o.moniteminstanceseq, his.clock, his.value FROM orchm_statics o
            left join hosts h on o.servername = h.name
            left join items i on o.monitemkey=i.key_ AND h.hostid = i.hostid
            left join history his on i.itemid=his.itemid
            where o.data_type = 'float' and his.clock >= %s and his.clock < %s
            order by his.clock"""
        param = [startTime, endTime]
        self.zbCur.execute(sql, param)
        values = self.zbCur.fetchall()

        
        # 18. 8.13 - LSH
        # 각각 insert 하던것을 한번에 Insert 하도록 변경함
        sql = """INSERT INTO tb_monitemhistory_float
            (moniteminstanceseq, clock, value) 
            VALUES 
            """
        SubSql = ""
        for i, value in enumerate(values) :
            if i > 0 : 
                SubSql += ","
            SubSql += """ (%s, %s, %s) """ % ( value[0], value[1], value[2] )
            
        sql += SubSql
        #print sql
        try:
            self.orchCur.execute(sql)
        except psycopg2.Error as e:
            print e

    def copyData(self, startTime, endTime):
        """모니터링 이력 정보 복사
        """
        startTime = int(startTime)
        endTime = int(endTime)

        # 자빅스의 데이터를 복사
        self._copyHistory(startTime, endTime)
        self._copyHistoryFloat(startTime, endTime)
        self.logger.info("startTime: " + str(startTime) + ", endTime: " + str(endTime))

    def getMaxTimestamp(self):
        """Orch-M 으로 복사한 데이터 중 가장 최근 데이터의 시각 정보를 반환한다.
        프로그램이 재시작 했을때 어느 시점부터 데이터를 복사해야 하는지 판단하기 위해서
        기존에 복사한 데이터 중 가장 최근 시각 정보를 가져온다.
        """

        sql = "SELECT max(clock) as clock FROM tb_monitemhistory_int"
        self.orchCur.execute(sql)
        rst = self.orchCur.fetchone()
        return rst[0]

class generateModel():
    """통계 데이터 생성을 위한 모델
    """
    logger = None

    def __init__(self, cfg=None, logger=None):
        self.logger = logger

        self.orch = db_mng.makeDbConn(cfg)
        self.orchCur = self.orch.cursor()

    def getMaxTimestamp(self, type="hour"):
        """가장 마지막에 생성된 통계 데이터 시각 정보 불러오기
        다음 통계 데이터를 생성해야 하는 시작 시점으로 사용된다.

        시각 정보를 발췌하는 테이블이 int 인 이유는 프로그램이 구동시 int를 수행한 다음
        float 테이블에 통계 데이터를 생성한다. 프로그램이 재구동될때 마다 통계 데이터를
        재등록하는 과정이 수행하기 때문에 float 데이터가 등록되는 것을 보장한다.

        :argument type: 시/일/주 단위 정보
        """
        sql = ""
        if type == "hour": # 시
            #sql = "SELECT MAX(clock) FROM tb_monitemtrend_hour"
            # 현재시간을 가져와
            sql = "SELECT to_char(now(), 'yyyy-mm-dd HH24')"
        elif type == "day": # 일
            sql = "SELECT MAX(day) FROM tb_monitemtrend_day"
        elif type == "week": # 주
            sql = "SELECT MAX(week) FROM tb_monitemtrend_week"
        elif type == "month": # 월
            sql = "SELECT MAX(month) FROM tb_monitemtrend_month"
        else:
            return None

        self.orchCur.execute(sql)
        rst = self.orchCur.fetchone()

        timestamp = None

        # 수집된 정보를 기준으로 일/주/월의 시작 날짜를 추출
        if rst[0] == None:
            sql = "SELECT MIN(clock) FROM tb_monitemhistory_int"
            self.orchCur.execute(sql)
            rst = self.orchCur.fetchone()

            timestamp = rst[0]

            if timestamp == None:
                if type == "hour":
                    sql = "SELECT to_char(now(), 'yyyy-mm-dd HH24')"
                elif type == "day":
                    sql = "SELECT to_char(now(), 'yyyy-mm-dd')"
                elif type == "week":
                    sql = "SELECT to_char(date_trunc('week', current_timestamp), 'yyyy-mm-dd')"
                elif type == "month":
                    sql = "SELECT to_char(now(), 'yyyy-mm-01')"
            else:
                if type == "hour":
                    # 시간은 언제나 현재시간을 준다.
                    sql = "SELECT to_char(now(), 'yyyy-mm-dd HH24')"
                elif type == "day":
                    sql = "SELECT to_char(to_timestamp(%s), 'yyyy-mm-dd')" % timestamp
                elif type == "week":
                    sql = "SELECT to_char(date_trunc('week', TIMESTAMP WITH TIME ZONE 'epoch' + %s * INTERVAL '1 second'), 'yyyy-mm-dd')" % timestamp
                elif type == "month":
                    sql = "SELECT to_char(to_timestamp(%s), 'yyyy-mm-01')" % timestamp

            self.orchCur.execute(sql)
            rst = self.orchCur.fetchone()
        return rst[0]
    
    def reinsert_hour_int(self, timestamp):
        """시 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_hour_int (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq, (clock / (60 * 60) * (60 * 60)) AS clock, cast(sum(value) / count(*) AS int) AS value
                FROM tb_monitemhistory_int
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, clock / (60 * 60)
                ) AS hist
            LEFT JOIN tb_monitemtrend_hour_int AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""

        param = [timestamp, timestamp + (60 * 60)]
        self.orchCur.execute(sql, param)

    def reinsert_hour_float(self, timestamp):
        """시 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_hour_float (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq, (clock / (60 * 60) * (60 * 60)) AS clock, cast(sum(value) / count(*) AS int) AS value
                FROM tb_monitemhistory_float AS hist
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, clock / (60 * 60)
            ) AS hist
            LEFT JOIN tb_monitemtrend_hour_float AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60)]
        self.orchCur.execute(sql, param)
        
    def reinsert_day_int(self, timestamp):
        """일 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_day_int (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    hist.moniteminstanceseq, hist.clock / (60 * 60 * 24) * (60 * 60 * 24) AS clock, cast(sum(hist.value) / count(*) AS int) AS value
                FROM tb_monitemhistory_int AS hist
                WHERE hist.clock >= %s AND hist.clock < %s AND trend.moniteminstanceseq is null
                GROUP BY hist.moniteminstanceseq, hist.clock / (60 * 60 * 24)
            ) AS hist
            LEFT JOIN tb_monitemtrend_day_int AS trend ON hist.moniteminstanceseq = trend.moniteminstanceseq AND hist.clock = trend.clock 
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24)]
        self.orchCur.execute(sql, param)
        
    def reinsert_day_float(self, timestamp):
        """일 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_day_float (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
			FROM (
				SELECT
                moniteminstanceseq, clock / (60 * 60 * 24) * (60 * 60 * 24) as clock, cast(sum(value) / count(*) as int) as value
                FROM tb_monitemhistory_float
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, clock / (60 * 60 * 24)
            ) AS hist
            LEFT JOIN tb_monitemtrend_day_float AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24)]
        self.orchCur.execute(sql, param)
        
    def reinsert_week_int(self, timestamp):
        """주 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_week_int (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq,
                    EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock))) AS clock,
                    CAST(sum(value) / COUNT(*) AS integer) AS value	
                FROM tb_monitemhistory_int AS hist
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week_int AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24 * 7)]
        self.orchCur.execute(sql, param)
        
    def reinsert_week_float(self, timestamp):
        """주 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_week_float (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq,
                    EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock))) AS clock,
                    CAST(sum(value) / COUNT(*) AS integer) AS value	
                FROM tb_monitemhistory_float AS hist
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week_float AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24 * 7)]
        self.orchCur.execute(sql, param)
        
    def reinsert_month_int(self, timestamp, next_timestamp):
        """월 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_month_int (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq,
                    EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock))) AS clock,
                    CAST(sum(value) / COUNT(*) AS integer) AS value    
                FROM tb_monitemhistory_int AS hist
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week_int AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, next_timestamp]
        self.orchCur.execute(sql, param)
        
    def reinsert_month_float(self, timestamp, next_timestamp):
        """주 통계 데이터 재 등록
        """
        sql = """INSERT INTO tb_monitemtrend_week_float (moniteminstanceseq, clock, value) (
            SELECT hist.moniteminstanceseq, hist.clock, hist.value
            FROM (
                SELECT
                    moniteminstanceseq,
                    EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock))) AS clock,
                    CAST(sum(value) / COUNT(*) AS integer) AS value	
                FROM tb_monitemhistory_float AS hist
                WHERE clock >= %s AND clock < %s
                GROUP BY moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week_float AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, next_timestamp]
        self.orchCur.execute(sql, param)
        
    def generateHour_int(self, timestamp):
        """시 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_hour (moniteminstanceseq, clock, type, min_int, avg_int, max_int, cnt) (
            SELECT
                hist.moniteminstanceseq, hist.clock, hist.type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    his.moniteminstanceseq
                    , clock / (60 * 60) * (60 * 60) as clock
                    , 'int' as type
                    , min(his.value) as min
                    , cast(sum(his.value) / count(*) as int) as avg
                    , max(his.value) as max
                    , count(*) as cnt
                FROM tb_monitemhistory_int AS his
                WHERE his.clock >= %s AND his.clock < %s
                GROUP BY his.moniteminstanceseq, his.clock / (60 * 60)
            ) AS hist
            LEFT JOIN tb_monitemtrend_hour AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60)]
        self.orchCur.execute(sql, param)
        

    def generateHour_float(self, timestamp):
        """시 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_hour (moniteminstanceseq, clock, type, min_float, avg_float, max_float, cnt) (
            SELECT
                hist.moniteminstanceseq, hist.clock, hist.type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    his.moniteminstanceseq
                    , clock / (60 * 60) * (60 * 60) as clock
                    , 'float' as type
                    , min(his.value) as min
                    , cast(sum(his.value) / count(*) as int) as avg
                    , max(his.value) as max
                    , count(*) as cnt
                FROM tb_monitemhistory_float AS his
                WHERE his.clock >= %s AND his.clock < %s
                GROUP BY his.moniteminstanceseq, his.clock / (60 * 60)
            ) AS hist
            LEFT JOIN tb_monitemtrend_hour AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.clock = trend.clock
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60)]
        self.orchCur.execute(sql, param)
        
    def generateDay_int(self, timestamp):
        """일 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_day (moniteminstanceseq, day, type, min_int, avg_int, max_int, cnt) (
            SELECT
                hist.moniteminstanceseq, hist.day, hist.type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    his.moniteminstanceseq
                    , to_char(to_timestamp(his.clock / (60 * 60 * 24) * (60 * 60 * 24)), 'yyyy-mm-dd') as day
                    , 'int' as type
                    , min(his.value) as min
                    , cast(sum(his.value) / count(*) as int) as avg
                    , max(his.value) as max
                    , count(*) as cnt
                FROM tb_monitemhistory_int AS his
                WHERE his.clock >= %s AND his.clock < %s
                GROUP BY his.moniteminstanceseq, his.clock / (60 * 60 * 24)
            ) AS hist
            LEFT JOIN tb_monitemtrend_day AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.day = trend.day
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24)]
        self.orchCur.execute(sql, param)
        
    def generateDay_float(self, timestamp):
        """일 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_day (moniteminstanceseq, day, type, min_float, avg_float, max_float, cnt) (
            SELECT
                hist.moniteminstanceseq, hist.day, hist.type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    his.moniteminstanceseq
                    , to_char(to_timestamp(his.clock / (60 * 60 * 24) * (60 * 60 * 24)), 'yyyy-mm-dd') as day
                    , 'float' as type
                    , min(his.value) as min
                    , cast(sum(his.value) / count(*) as int) as avg
                    , max(his.value) as max
                    , count(*) as cnt
                FROM tb_monitemhistory_float AS his
                WHERE his.clock >= %s AND his.clock < %s
                GROUP BY his.moniteminstanceseq, his.clock / (60 * 60 * 24)
            ) AS hist
            LEFT JOIN tb_monitemtrend_day AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.day = trend.day
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24)]
        self.orchCur.execute(sql, param)

    # 17.12.11 - lsh
    # 상용에서 psycopg2.DataError: integer out of range 오류 발생
    # bigint 로 변경
    def generateWeek_int(self, timestamp):
        """주 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_week (moniteminstanceseq, week, type, min_int, avg_int, max_int, cnt) (
            SELECT hist.moniteminstanceseq, hist.week, 'int' as type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    to_char(to_timestamp(EXTRACT(epoch FROM date_trunc('week', to_timestamp(hist.clock)))), 'yyyy-mm-dd') as week
                    , hist.moniteminstanceseq
                    , min(hist.value)::bigint as min
                    , CAST(sum(hist.value) / COUNT(*) AS bigint) AS avg
                    , max(hist.value)::bigint as max
                    , count(*) as cnt
                FROM tb_monitemhistory_int AS hist
                WHERE hist.clock >= %s AND hist.clock < %s
                GROUP BY hist.moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(hist.clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.week = trend.week
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24 * 7)]
        self.orchCur.execute(sql, param)

    def generateWeek_float(self, timestamp):
        """주 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_week (moniteminstanceseq, week, type, min_float, avg_float, max_float, cnt) (
            SELECT hist.moniteminstanceseq, hist.week, 'float' as type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    to_char(to_timestamp(EXTRACT(epoch FROM date_trunc('week', to_timestamp(hist.clock)))), 'yyyy-mm-dd') as week
                    , hist.moniteminstanceseq
                    , min(hist.value)::int as min
                    , CAST(sum(hist.value) / COUNT(*) AS integer) AS avg
                    , max(hist.value)::int as max
                    , count(*) as cnt
                FROM tb_monitemhistory_float AS hist
                WHERE hist.clock >= %s AND hist.clock < %s
                GROUP BY hist.moniteminstanceseq, EXTRACT(epoch FROM date_trunc('week', to_timestamp(hist.clock)))
            ) AS hist
            LEFT JOIN tb_monitemtrend_week AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.week = trend.week
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp + (60 * 60 * 24 * 7)]
        self.orchCur.execute(sql, param)
        try :
            self.orchCur.execute(sql, param)
        except :
            self.logger.info  ( "SQL : %s, \n Param : %s " % ( sql, str( param) ) )

    def generateMonth_int(self, timestamp, next_timestamp):
        """월 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_month (moniteminstanceseq, month, type, min_int, avg_int, max_int, cnt) (
            SELECT hist.moniteminstanceseq, hist.month, 'int' as type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    to_char(to_timestamp(%s), 'yyyy-mm-dd') as month
                    , hist.moniteminstanceseq
                    , min(hist.value)::int as min
                    , CAST(sum(hist.value) / COUNT(*) AS integer) AS avg
                    , max(hist.value)::int as max
                    , count(*) as cnt
                FROM tb_monitemhistory_int AS hist
                WHERE hist.clock >= %s AND hist.clock < %s
                GROUP BY hist.moniteminstanceseq
            ) AS hist
            LEFT JOIN tb_monitemtrend_month AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.month = trend.month
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp, next_timestamp]

        try :
            self.orchCur.execute(sql, param)
        except :
            self.logger.info  ( "SQL : %s, \n Param : %s " % ( sql, str( param) ) )

    def generateMonth_float(self, timestamp, next_timestamp):
        """월 통계 데이터 생성
        """
        sql = """INSERT INTO tb_monitemtrend_month (moniteminstanceseq, month, type, min_float, avg_float, max_float, cnt) (
            SELECT hist.moniteminstanceseq, hist.month, 'float' as type, hist.min, hist.avg, hist.max, hist.cnt
            FROM (
                SELECT
                    to_char(to_timestamp(%s), 'yyyy-mm-dd') as month
                    , hist.moniteminstanceseq
                    , min(hist.value)::float as min
                    , CAST(sum(hist.value) / COUNT(*) AS float) AS avg
                    , max(hist.value)::float as max
                    , count(*) as cnt
                FROM tb_monitemhistory_float AS hist
                WHERE hist.clock >= %s AND hist.clock < %s
                GROUP BY hist.moniteminstanceseq
            ) AS hist
            LEFT JOIN tb_monitemtrend_month AS trend ON hist.moniteminstanceseq=trend.moniteminstanceseq AND hist.month = trend.month
            WHERE trend.moniteminstanceseq is null
        )"""
        param = [timestamp, timestamp, next_timestamp]
        try :
            self.orchCur.execute(sql, param)
        except :
            self.logger.info  ( "SQL : %s, \n Param : %s " % ( sql, str( param) ) )


class cleanModel():
    """수집한 통계 데이터를 보존 기간이 경과된 데이터는 삭제하기 위한 모델
    """
    def __init__(self, cfg):
        self.orch = db_mng.makeDbConn(cfg)
        self.orchCur = self.orch.cursor()
        
    def removeData(self, logger):
        """Zabbix로부터 복사해 온 감시 항목 데이터 중 185일이 경과된 데이터 삭제.
        """
        days = 185
        limit_days = 60     
        seconds_in_a_day = 60 * 60 * 24 * limit_days

        limit_days2 = int(time.time()) - seconds_in_a_day
        # history 데이터 삭제
        for TableName in ['tb_monitemhistory_int', 'tb_monitemhistory_float'] :
            sql = """DELETE FROM %s
                WHERE clock < %s """ % (TableName, limit_days2)
            ret = db_mng._execute(self.orch, sql, None, isSelect=False)
            if ret > 0 :
                logger.info (' %s .1 : %s' % ( TableName, str(ret)))


        # 시간 통계 데이터 삭제
        sql = """DELETE FROM tb_monitemtrend_hour
            WHERE day <= substring(cast(now() - interval '%s day' as text) from 1 for 10)
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info (' ret. hour : %s' % str(ret))
    

        # 일간 통계 데이터 삭제
        sql = """DELETE FROM tb_monitemtrend_day
            WHERE day <= substring(cast(now() - interval '%s day' as text) from 1 for 10)
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info (' ret.3 : %s' % str(ret))
        
        # 주간 통계 데이터 삭제
        sql = """DELETE FROM tb_monitemtrend_week
            WHERE week <= substring(cast(now() - interval '%s day' as text) from 1 for 10)
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info (' ret.4 : %s' % str(ret))
        
        # 월간 통계 데이터 삭제
        sql = """DELETE FROM tb_monitemtrend_month
            WHERE month <= substring(cast(now() - interval '%s day' as text) from 1 for 10)
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info (' ret.5 : %s' % str(ret) )



        # 2019.11.11 - 추가
        # tb_userstatus  정리 
        sql = """DELETE FROM tb_userstatus
            WHERE start_time < now() - interval '%s day'
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info ('ret. tb_userstatus : %s' % str(ret) )

        # tb_smssendstatus
        sql = """DELETE FROM tb_smssendstatus
            WHERE create_dttm < now() - interval '%s day'
        """
        param = [days]
        ret = self.orchCur.execute(sql, param)
        logger.info ('ret. tb_smssendstatus : %s' % str(ret) )

        # tb_histalarm  정리 (curalarm 에 있는것은 제외)
        try : 
            sql = """DELETE FROM tb_histalarm
                WHERE mon_dttm < now() - interval '%s day'
                AND resolve_dttm IS NOT null
                AND curalarmseq NOT IN ( SELECT curalarmseq FROM tb_smssendstatus )
            """
            param = [days]
            ret = self.orchCur.execute(sql, param)
            logger.info ('ret. tb_histalarm : %s' % str(ret) )

        except Exception as e: 
            print('Error ', e) 

        print (' Delete End ' )

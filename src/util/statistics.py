#-*- coding: utf-8 -*-
"""통계 데이터 생성을 위한 모듈

@since 2016-09-12
"""

from util import db_mng
import util.statistics_model as model
import threading

import time
import datetime
from dateutil import relativedelta

class copyZbToOrchm(threading.Thread):
    """모니터링 데이터 복사를 위한 스레드
    """

    logger = None

    """현재 작업일
    작업일이 변경되면 통계 설정 정보를 다시 복사해야 한다.
    """
    workdate = None

    """DB 를 다루기 위한 객체
    """
    db = None

    # 수집주기
    period = 60 * 2 # 수집 주기는 2분으로 설정
    # 데이터를 복사한 시각 범위
    timestamp = None
    
    def __init__(self, logger=None, cfg=None):
        """모니터링 데이터 복사를 위한 스레드

        :aguments cfg: 프로그램 설정 정보가 담겨 있는 변수
        :aguments logger: 로그를 남기는데 사용하는 로거 객체
        """
        threading.Thread.__init__(self)
        self.logger = logger
        self.cfg = cfg

        self.db = model.copyZbToOrchmModel(self.logger, self.cfg)

        self.workdate = time.strftime("%Y-%m-%d", time.localtime()) # 오늘 날짜로 작업일 설정
        self.getMaxTimestamp()

        self.init_zb() # 자빅스 데이터베이스 초기화

    def copyConfig(self, bDelete=True, curDate=None):
        """통계 설정 정보를 Orch-M 에서 Zabbix 로 복사

        :argument bDelete: 이 값이 True 인 경우 기존 데이터를 삭제한다.
        :argument curDate: 갱신할 현재 작업일
        """
        if bDelete == True:
            self.db.zb_deleteConfig() # 기존 데이터 삭제

        self.db.copyConfig() # 설정 정보 복사

        if curDate != None:
            self.workdate = curDate
    
    def getMaxTimestamp(self):
        """프로그램을 재구동시 Zabbix 에서 가져와야 하는 데이터의 가장 마지막 시각 정보 발췌
        시각 정보는 Orch-M 에서 가져와야 어디까지 복사되었는지 확인할 수 있다.
        """
        max_timestamp = self.db.getMaxTimestamp()
        self.timestamp = time.time() + 1 if max_timestamp == None else max_timestamp + 1

    def init_zb(self):
        """zabbix 의 데이터베이스에 대한 초기화 작업
        Orch-M 과 ZB 에서 사용하는 DB가 같은 서버에 존재하지 않기 때문에 성능을 위해서 설정 정보를
        Orch-M 에서 ZB에 복사한다. 통계 데이터 생성을 위한 설정 정보는 일단위로 적용되기 때문에
        매일 0시에 설정 정보를 Orch-M 에서 ZB 의 DB 서버에 복사하는 작업을 수행한다.
        주요 작업은 다음과 같다.
        
        * 설정 테이블이 존재하는지 검사 후 존재하지 않을 경우 새로 생성한다.
        * 기존 설정 정보를 모두 삭제한다.
        * 신규 설정 정보를 새로 등록한다.
        """

        bDelete = True
        rst = self.db.zb_existsTable() # zb 에 설정 테이블이 존재하는지 검사
        if rst == False:
            self.db.zb_createTable() # 설정 테이블 생성
            bDelete = False

        self.copyConfig(bDelete) # 통계 설정 정보를 Orch-M 에서 Zabbix 로 복사

    def copyData(self, start_timestamp, end_timestamp):
        """자빅스에서 수집한 모니터링 정보를 Orch-M 의 DB로 복사
        :argument start_timestamp: 복사 구간 시작 시각
        :argument end_timestamp: 복사 구간 종료 시각
        """
        self.db.copyData(start_timestamp, end_timestamp)

    def checkCopyConfig(self):
        """통계 설정 정보를 Orch-M 에서 Zabbix 로 다시 복사해야 하는지 검사.
        """
        curDate = time.strftime("%Y-%m-%d", time.localtime())
        
        # TODO 복사해야하는 데이터가 밀려 있는 경우에는 설정을 복사하지 않도록 수정하기

        if self.workdate != curDate: # 작업일과 현재 날짜가 다르다면, 설정 정보를 다시 복사한다.
            return True
        else:
            return False
        
    def calculateSleepPeriod(self, current_timestamp):
        """작업 수행 후 대기해야 하는 시간 계산
        
        데이터 복사는 self.period 만큼 대기한다.
        작업 수행시 마지막 작업시각으로부터 경과한 시간이 self.period 값 보다 큰 경우에는
        복사해야 하는 데이터가 밀려 있는 상태이므로 대기 없이 다음 작업을 수행한다.
        """
#         diff = current_timestamp - self.timestamp
        
        period = current_timestamp - (self.timestamp + self.period * 2)

#         period = 0 if diff > self.period else self.period - diff
#         return period

        if period > 0:
            return 0
        else:
            return self.period

    def setNextPeriod(self):
        self.timestamp = self.timestamp + self.period # 다음 주기 계산

    def checkCopy(self, current_timestamp):
        """데이터를 복사해도 되는지 검사
        """
        # DB에 등록된 데이터와 현재 시각 정보 사이의 차이 계산
#         period = self.calculateSleepPeriod(current_timestamp)
#         period = period - self.period # 데이터 복사는 일정 텀을 두고 지연 시켜야 한다.
        
        period = current_timestamp - (self.timestamp + self.period * 2)
        
        if period > 0:
            return True
        else:
            return False

    def run(self):
        self.logger.info('ZB statistics data Collector Run.')

        while True:
            # TODO 현재는 프로세스가 중단되었다가 다음날 진행했을 경우
            # 매번 설정 정보를 복사하는 문제가 있다.
            if self.checkCopyConfig() == True: # 설정 정보 검사 및 필요시 설정 정보 복사
                self.copyConfig() # 설정 정보 복사
            
            current_timestamp = time.time()

            if self.checkCopy(current_timestamp) == True:
                self.copyData(self.timestamp, self.timestamp + self.period) # 데이터 복사
                self.setNextPeriod() # 다음 복사 주기 계산

            period = self.calculateSleepPeriod(current_timestamp) # 다음 복사 주기 시간 계산

            if period > 0:
                time.sleep(period) # 다음 주기 까지 스레드 대기

class generateData(threading.Thread):
    # 생성된 데이터의 마지막 시각 정보
    hour = None
    hour_timestamp = None

    day = None
    day_timestamp = None
    week = None
    week_timestamp = None
    month = None
    month_timestamp = None

    """일정 주기로 수집한 모니터링 데이터를 바탕으로 통계 데이터를 생성하는 클래스

    생성해야 하는 통계 데이터는 시, 일, 주 단위다.
    따라서 생성 스레드는 최소 1시간 단위로 돌면서 생성해야 하는 데이터를 검사해야 한다.

    * 기존에 생성한 통계 데이터에서 다음에 생성할 데이터 범위 발췌
    * 생성할 통계 데이터 범위 계산
    * 통계 데이터 생성
    * 다음 주기까지 대기

    :aguments cfg: 프로그램 설정 정보가 담겨 있는 변수
    :aguments logger: 로그를 남기는데 사용하는 로거 객체
    """
    def __init__(self, cfg=None, logger=None):
        threading.Thread.__init__(self)
        self.logger = logger
        self.cfg = cfg

        self.db = model.generateModel(self.cfg)

    """
    통계 데이터를 생성한다면 어디까지 데이터를 생성했는지 기록할 필요가 있다.
    별도의 설정 테이블을 두어다 어디까지 데이터를 생성했는지 확인하기 보다는 생성된 데이터를 기반으로 살펴보려고 한다.
    이전에 생성된 통계 데이터를 읽어서 정보를 사용한다.

    tb_moniteminstance 테이블에서 통계 생성 설정 정보가 'y' 인 값 불러오기

    프로그램이 실행 도중에 종료되어 프로그램이 이어서 실행해야 할 경우 통계 데이터 생성을 이어서 시작해야 한다.
    마지막으로 생성한 통계 데이터에 대해서 기록할 필요가 있다. 그러나 통계 데이터 생성 이력 데이터는 불필요한 데이터라서
    별도로 생성하지 않는다. 따라서 생성된 데이터를 조회하여 해당 데이터가 어디까지 생성되었는지 식별할 필요가 있다.

     -- 시 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_hour_int (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(20, 0)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    -- 일 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_day_int (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(20, 0)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    -- 주 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_week_int (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(20, 0)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    -- 시 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_hour_float (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(16, 4)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    -- 일 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_day_float (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(16, 4)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    -- 주 단위 통계 테이블
    CREATE TABLE tb_monitemtrend_week_float (
        moniteminstanceseq integer
    ,   clock integer
    ,   value numeric(16, 4)
    ,   PRIMARY KEY ("moniteminstanceseq", "clock")
    );

    tb_moniteminstance 테이블과 tb_monitemtrend_*_int 테이블에서
    """

    # 생성해야 하는 통계 데이터 시작점이 무엇인지 살펴보기

    # 시 통계 데이터 생성
    """
    -- 통계 데이터 발췌 쿼리
    select
        moniteminstanceseq, cast(sum(value) / count(*) as int) sum_value, to_timestamp(clock / (60 * 60) * (60 * 60))
    from tb_monitemhistory_int
    group by moniteminstanceseq, clock / (60 * 60)
    """

    # 일 통계 데이터 생성
    """
    -- 통계 데이터 발췌 쿼리
    select
        moniteminstanceseq, cast(sum(value) / count(*) as int) sum_value, to_timestamp(clock / (60 * 60 * 24) * (60 * 60 * 24))
    from tb_monitemhistory_int
    group by moniteminstanceseq, clock / (60 * 60 * 24)
    """

    # 주 통계 데이터 생성. 월요일부터 일요일까지의 데이터를 통계로 만듬
    """
    -- 통계 데이터 발췌 쿼리
    select
        moniteminstanceseq,
        extract(epoch from date_trunc('week', to_timestamp(clock))) as clock,
        cast(sum(value) / count(*) as integer) as value	
    from tb_monitemhistory_int
    group by moniteminstanceseq, extract(epoch from date_trunc('week', to_timestamp(clock)))
    """

    def getLastTimestamp(self):
        """통계 데이터를 생성해야 하는 시작 시각을 불러온다.

        프로그램이 구동될 경우 통계 데이터를 생성해야 하는 시작점이 있다.
        각 통계 데이터를 생성하기 위한 시작점을 발췌 한다.
        """
        # self.hour = self.db.getMaxTimestamp("hour") # 시
        # self.hour_timestamp = int(time.mktime(datetime.datetime.strptime(self.hour, "%Y-%m-%d %H:00:00").timetuple()))

        self.hour = self.db.getMaxTimestamp("hour") # 시
        self.hour_timestamp = int(time.mktime(datetime.datetime.strptime(self.hour, "%Y-%m-%d %H").timetuple()))

        self.day = self.db.getMaxTimestamp("day") # 일
        self.day_timestamp = int(time.mktime(datetime.datetime.strptime(self.day, "%Y-%m-%d").timetuple()))
        
        self.week = self.db.getMaxTimestamp("week") # 주
        self.week_timestamp = int(time.mktime(datetime.datetime.strptime(self.week, "%Y-%m-%d").timetuple()))
        
        self.month = self.db.getMaxTimestamp("month") # 월
        self.month_timestamp = int(time.mktime(datetime.datetime.strptime(self.month, "%Y-%m-%d").timetuple()))
    
    def reinsertData(self):
        """프로그램이 사용자에 의해서 종료될 경우 통계 데이터가 일부만 생성될 수 있다.
        기존에 생성하지 못한 나머지 통계 데이터를 추가하기 위한 작업 수행.

        작업 수행히 생성된 통계 데이터가 일부만 등록되는 경우는 다음가 같은 상황일 수 있다.
        * 사용자에 의해서 프로그램이 중단된 경우
        * 프로그램이 오류가 발생하여 중단된 경우

        기존 작업에서 통계 데이터가 일부만 생성된 경우를 대비하기 위해서 현재 생성된 통계 데이터의
        이전 기간에 대한 통계를 다시 생성해서 등록한다.
        """
#         # 시 통계 데이터 재 생성
#         hour = self.hour - (60 * 60)
#         self.db.reinsert_hour_int(hour)
#         self.db.reinsert_hour_float(hour)
        
        # 일 통계 데이터 재 생성
        day_timestamp = self.day_timestamp - (60 * 60 * 24)
        self.db.reinsert_day_int(day_timestamp)
        self.db.reinsert_day_float(day_timestamp)

        # 주 통계 데이터 재 생성
        week_timestamp = self.week_timestamp - (60 * 60 * 24 * 7)
        self.db.reinsert_week_int(week_timestamp)
        self.db.reinsert_week_float(week_timestamp)
        
        # 월 통계 데이터 재 생성
        month = datetime.datetime.fromtimestamp(self.month_timestamp)
        prev_month = month - datetime.timedelta(days = 1)
        prev_month = prev_month.strftime("%Y-%m-01") # 이전 달 1일
        month_timestamp = int(time.mktime(datetime.datetime.strptime(prev_month, "%Y-%m-%d").timetuple()))
        
        self.db.reinsert_month_int(month_timestamp, self.month_timestamp)
        self.db.reinsert_month_float(month_timestamp, self.month_timestamp)

    def generateHour(self):
        """시 단위 통계 데이터 생성
        """
        self.db.generateHour_int(self.hour_timestamp)
        self.db.generateHour_float(self.hour_timestamp)

        # 통계 생성 후 한시간 추가. 
        self.hour_timestamp = self.hour_timestamp + (60 * 60)
        self.hour = time.strftime('%Y-%m-%d %H', time.localtime(self.hour_timestamp))

        self.logger.info("generateHour: " + str(self.hour))

    def generateDay(self):
        """일 단위 통계 데이터 생성
        """
        self.db.generateDay_int(self.day_timestamp)
        self.db.generateDay_float(self.day_timestamp)

        # 통계 생성 후 기준일을 하루 더한다.
        self.day_timestamp = self.day_timestamp + (60 * 60 * 24)
        self.day = time.strftime('%Y-%m-%d', time.localtime(self.day_timestamp))
        
    def generateWeek(self):
        """주 단위 통계 데이터 생성
        """
        self.db.generateWeek_int(self.week_timestamp)
        self.db.generateWeek_float(self.week_timestamp)

        # 통계 생성 후 기준일을 일주일 더한다.
        self.week_timestamp = self.week_timestamp + (60 * 60 * 24 * 7)
        self.week = time.strftime('%Y-%m-%d', time.localtime(self.week_timestamp))
        
    def generateMonth(self):
        """월 단위 통계 데이터 생성
        """
        next_month = datetime.datetime.strptime(self.month, "%Y-%m-%d") + relativedelta.relativedelta(months=1)
        next_month_timestamp = int(time.mktime(next_month.timetuple()))
        
        self.db.generateMonth_int(self.month_timestamp, next_month_timestamp)
        self.db.generateMonth_float(self.month_timestamp, next_month_timestamp)

        # 통계 생성 후 기준일을 다음달 1일로 설정한다.
        self.month = next_month.strftime("%Y-%m-%d")
        self.month_timestamp = next_month_timestamp

    def checkHour(self):
        """시 통계 데이터를 생성을 해야 하는지 검사
        """
        if (time.time() - self.hour_timestamp) > (60 * 60):
            return True
        else:
            return False

    def checkDay(self):
        """일 통계 데이터를 생성 해야 하는지 검사
        """
        yesterday_timestamp = int(time.mktime(datetime.date.today().timetuple())) - ((60 * 60 * 24))
        
        if self.day_timestamp <= yesterday_timestamp: # 어제 날짜와 같거나 작은 경우 일 통계 생성
            return True
        else:
            return False

    def checkWeek(self):
        """주 통계 데이터를 생성 해야 하는지 검사
        """
        # 전주 계산
        tmp = datetime.date.today()
        tmp_w = tmp.timetuple()
        prev_week = tmp - datetime.timedelta(tmp_w.tm_wday + 7)
        prev_week_timestamp = int(time.mktime(prev_week.timetuple()))
        
        if self.week_timestamp <= prev_week_timestamp:
            return True
        else:
            return False

    def checkMonth(self):
        """주 통계 데이터를 생성 해야 하는지 검사
        """
        # 전월 계산
        today = datetime.date.today()   # 오늘
        first = today.replace(day=1)    # 이번 달 1일
        lastMonth = first - datetime.timedelta(days=1) # 이전 달 마지막일
        prev_month = lastMonth.strftime("%Y-%m-01") # 이전 달 1일
        
        prev_month_timestamp = int(time.mktime(datetime.datetime.strptime(prev_month, "%Y-%m-%d").timetuple()))
        
        if self.month_timestamp <= prev_month_timestamp:
            return True
        else:
            return False

    def isWating(self):
        """다음 통계 데이터 생성을 위해서 대기해야 하는가?
        """
        yesterday_timestamp = int(time.mktime(datetime.date.today().timetuple())) - ((60 * 60 * 24))
        
        if yesterday_timestamp <= self.day_timestamp:
            return True
        else:
            return False
    
    def run(self):
        self.getLastTimestamp() # 통계 데이터를 생성해야 하는 시작 시각을 불러온다.
#         self.reinsertData() # 기존에 통계 데이터 등록시 빠진 경우를 대비한 재작업

        # 매 정시에 동작하도록 대기
        # 현재시간 분단위 털고(정시), 1시간 더한 값에서 현재 시간을 빼면  남은 Sec 
        delay_sec = int ( time.time() / 3600) * 3600 + 3600 - int( time.time())

        # 5분 대기
        self.logger.info("First dealy %s sec " % str(delay_sec + 300))

        # 정시 대기후 5분 더 대기, Zabbix 에서 Data 가져오는 시간이 필요. 1분 -> 5분 늘림.
        time.sleep(delay_sec + 300)

        while True:
            self.logger.info("Start Gen")

            if self.checkHour():
                self.logger.info("generateHour")
                self.generateHour()  # 일 단위 통계 데이터 생성

            if self.checkDay():
                self.logger.info("generateDay")
                self.generateDay()  # 일 단위 통계 데이터 생성

            if self.checkWeek():
                self.logger.info("generateWeek")
                self.generateWeek() # 주 단위 통계 데이터 생성
                
            if self.checkMonth():
                self.logger.info("generateMonth")
                self.generateMonth() # 월 단위 통계 데이터 생성


            #ret = self.isWating() # 다음 통계 데이터 생성 주기 동안 대기할 시간 계산
            #if ret == True:

            # 1시간 대기.
            time.sleep(60 * 60)

class cleanData(threading.Thread):
    """수집한 통계 데이터중에서 보존 기간이 경과된 데이터를 삭제하기 위한 스레드
    
    crontab을 사용하고 싶지만, 관리적인 이유로 인해서 패스
    
    데이터 삭제는 사용자가 가장 적은 시간대인 새벽 4시에 수행
    """
    cfg = None
    logger = None
    
    def __init__(self, cfg=None, logger=None):
        threading.Thread.__init__(self)
        self.cfg = cfg
        self.logger = logger
        
        self.db = model.cleanModel(self.cfg)
        
    def removeData(self):
        self.db.removeData(self.logger)
    
    def firstWaiting(self):
        # 매일 새벽 4시에 작업을 수행하도록 작업 대기
        sleep = 0
        current_timestamp = time.time() # 현재 시각의 timestamp
        
        today = datetime.date.today()
        today_timestamp = int(time.mktime(today.timetuple()))
        diff = (today_timestamp + 60 * 60 * 4) - current_timestamp
        if diff > 0:
            sleep = diff
        else:
            sleep = 60 * 60 * 24 + diff
        time.sleep(sleep)
        
    def run(self):
        self.removeData()   # 데이터 삭제
        self.firstWaiting() # 프로세스 시작 후 작업이 새벽 4시에 시작되도록 대기

        while True:
            self.removeData()   # 데이터 삭제

            time.sleep(60 * 60 * 24)    # 24시간 대기
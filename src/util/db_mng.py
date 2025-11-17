#-*- coding: utf-8 -*-

import psycopg2
import Queue

TITLE = 'orchm'

import logging
logger = logging.getLogger(TITLE)


def makeDbConn( cfg ):
    dbConn = psycopg2.connect( database=cfg['db_name'], user=cfg['db_user'], password=cfg['db_passwd'],
                         host=cfg['db_addr'], port=int(cfg['db_port']), application_name='Orch-m' )
    dbConn.autocommit = True
    return dbConn

def makeZbDbConn( cfg ):
    zbDbConn = psycopg2.connect( database=cfg['zb_db_name'], user=cfg['zb_db_user'], password=cfg['zb_db_passwd'],
                         host=cfg['zb_db_addr'], port=int(cfg['zb_db_port']), application_name='Orch-m' )
    zbDbConn.autocommit = True
    return zbDbConn

class Singleton(object):
    _instance = {}
    _inst_key = None

    def __new__(self, *args, **kwargs):
        if not self._instance.has_key(args[0]):
            self._instance[args[0]] = object.__new__(self, *args, **kwargs)
            self._inst_key = args[0]
        return self._instance[args[0]]
    
    def __del__(self):
        try:
            self._instance.pop(self._inst_key)
        except :
            None
        


def _execute( dbConn, sql, param=None, isSelect=True, _logger=None ):
    tmpLog = ( lambda x: x if x != None else logger)(_logger)
    
    cur = dbConn.cursor()
    cur.execute( sql )
    
    dic = None
    if isSelect:
        dic = []
        columns = [desc[0] for desc in cur.description]
        rows = cur.fetchall()
        for row in rows:
            d = dict(zip(columns, row))
            if type(param) == str and param != "" :
                dic.append( d[param] )
            else:
                dic.append(d)
    else:
        if type(param) == bool and param == True :
            try:
                cur.execute('SELECT LASTVAL()')
                ret = cur.fetchone()
                if ret == None or len(ret) < 1 :
                    dic = None
                else:
                    dic = ret[0]
            except Exception, e:
                tmpLog.exception( e )
                tmpLog.error( sql )
                dic = None
        else:
            dic = int(cur.rowcount)
    
    return dic



class RollBackDB():
    
    def __init__(self, _dbConn):
        self.dbConn = _dbConn
    
    def select(self, sql, column=None):
        try:
            return _execute(self.dbConn, sql, column, True)
        except Exception, e:
            logger.fatal(e)
            logger.error(sql)
            return None
    
    def execute(self, sql, _return=False):
        try:
            return _execute(self.dbConn, sql, _return, False)
        except Exception, e:
            logger.fatal(e)
            logger.error(sql)
            return None
    
    def commit(self):
        self.dbConn.commit()
    
    def rollback(self):
        self.dbConn.rollback()
    
    def close(self):
        try:
            if self.dbConn != None :
                self.dbConn.commit()
                self.dbConn.close()
        except Exception, e:
            logger.fatal(e)

    def __del__(self):
        if self.dbConn != None:
            self.dbConn.close()
        

class dbManager(Singleton):
    
    def __init__(self, name, dbName, dbUser, dbPass, dbAddr, dbPort, 
                 connCnt=1, autocommit=True, qTimeout=5, _logger=None):
        self.dbName = dbName
        self.dbUser = dbUser
        self.dbPass = dbPass
        self.dbAddr = dbAddr
        self.dbPort = dbPort
        try:
            self.connCnt = int(connCnt)
        except Exception:
            logger.error('Fail to Create DBM, Invalid ConnCount=%s, type=%s'%(str(connCnt), str(type(connCnt))))
            self.connCnt = 1    
        self.dbPool = Queue.Queue(connCnt)
        self.autocommit = autocommit
        self.qTimeout = qTimeout
        self.logger = ( lambda x : x if x != None else logger)(_logger)
        self.create()
        
    def create(self):
        try:
            for i in range(0, self.connCnt):
                dbConn = psycopg2.connect( database=self.dbName, user=self.dbUser, password=self.dbPass,
                                     host=self.dbAddr, port=int(self.dbPort),application_name='Orch-m' )
                dbConn.autocommit = self.autocommit
                self.dbPool.put_nowait( dbConn )
            return True
        
        # Queue.Empty, Queue.Full
        except Queue.Full, e:
            logger.warning('DBM Queue Full, max=%s, cur=%s'%(str(self.dbPool.maxsize), str(self.dbPool.qsize())))
            return True
        except Exception, e:
            logger.fatal(e)
            logger.error('Fail to DBM Create')
            return False
    
    def _execute(self, sql, param=None, isSelect=True):
        dbConn = None
        cur = None
        try:
            dbConn = self.dbPool.get( True, self.qTimeout )
            return _execute(dbConn, sql, param, isSelect)
        except Exception, e:
            logger.fatal( e )
            logger.error(sql)
            raise e
        finally:
            if cur != None:
                cur.close()
            
            try:
                if dbConn != None:
                    if dbConn.closed :
                        logger.warning( 'DBM Connection Closed. Reconnecting...' )
                        dbConn = psycopg2.connect( database=self.dbName, user=self.dbUser, password=self.dbPass,
                                             host=self.dbAddr, port=int(self.dbPort),application_name='Orch-m' )
                        dbConn.autocommit = self.autocommit
                    self.dbPool.put( dbConn, True, self.qTimeout )
            except Queue.Full, e:
                logger.warning('DBM Queue Full, max=%s, cur=%s'%(str(self.dbPool.maxsize), str(self.dbPool.qsize())))
            except Exception, e:
                logger.fatal(e)
            
            if self.getCurrSize() < 1:
                logger.error( "DB Queue Size: %s"%str(self.getCurrSize()) )
    
    def select(self, sql, column=None):
        return self._execute(sql, column, True)
    
    def execute(self, sql, _return=False):
        return self._execute(sql, _return, False)
    
            
    def getRollBackDB(self):
        dbConn = psycopg2.connect( database=self.dbName, user=self.dbUser, password=self.dbPass,
                                 host=self.dbAddr, port=int(self.dbPort), application_name='Orch-m' )
        dbConn.autocommit = False
        return RollBackDB(dbConn)
    
    def getTotalSize(self):
        return self.dbPool.maxsize
    
    def getCurrSize(self):
        return self.dbPool.qsize()

    def __del__(self):
        Singleton.__del__(self)
        try:
            while not self.dbPool.empty():
                dbConn = self.dbPool.get_nowait()
                if dbConn != None :
                    dbConn.close()
        except Exception, e:
            logger.fatal(e)
    
	# 18. 3. 8 - lsh Ãß°¡
    def close(self):
        try:
            if dbConn != None :
                dbConn.close()
        except Exception, e:
            logger.fatal(e)
	
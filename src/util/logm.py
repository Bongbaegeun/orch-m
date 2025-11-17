# -*- coding: utf-8 -*-
'''
Created on 2015. 4. 22.

@author: ohhara
'''

import os, sys

import logging.handlers

#
# _srcfile is used when walking the stack to check when we've got the first
# caller stack frame.
#
if hasattr(sys, 'frozen'): #support for py2exe
    _srcfile = "logging%s__init__%s" % (os.sep, __file__[-4:])
elif __file__[-4:].lower() in ['.pyc', '.pyo']:
    _srcfile = __file__[:-4] + '.py'
else:
    _srcfile = __file__
_srcfile = os.path.normcase(_srcfile)



def init(logName='myLogger', logDir='./', logFile='myLogger.log', logFileMaxByte=10*1024*1024, logBackupCnt=10, logLevel=logging.DEBUG ):
    global logger
    logger = logging.getLogger( logName )
    
    # 포매터를 만든다.
    formatter = logging.Formatter( '[%(asctime)s] %(levelname)s: %(message)s' )
    
    # 스트림과 파일로 로그를 출력하는 핸들러를 각각 만든다.
    fileHandler = logging.handlers.RotatingFileHandler( logDir + "/" + logFile, maxBytes=logFileMaxByte, backupCount=logBackupCnt )
    streamHandler = logging.StreamHandler()
    
    # 각 핸들러에 포매터를 지정한다.
    fileHandler.setFormatter( formatter )
    streamHandler.setFormatter( formatter )
        
    # 위에서 만든 로거 인스턴스에 스트림 핸들러화 파일핸들러를 붙인다.
    logger.addHandler( fileHandler )
    logger.addHandler( streamHandler )
        
    # 로그 레벨 설정
    logger.setLevel( logLevel )

def setLogLevel(logLevel):
    logger.setLevel( logLevel )

def debug(logMsg):
    logger.debug( str(logMsg) + findFN() )

def info(logMsg):
    logger.info( str(logMsg) )

def warn(logMsg):
    logger.warning( str(logMsg) + findFN() )

def err(logMsg):
    logger.error( str(logMsg) + findFN() )

def cri(logMsg):
    logger.critical( str(logMsg) + findFN() )

def exc(e, title=''):
    logger.critical( title + " Exception!!!, " + str(e) + findFN() )


def currentframe():
    """Return the frame object for the caller's stack frame."""
    try:
        raise Exception
    except:
        return sys.exc_info()[2].tb_frame.f_back

def findFN():
    f = currentframe()
    #On some versions of IronPython, currentframe() returns None if
    #IronPython isn't run with -X:Frames.
    if f is not None:
        f = f.f_back
    rv = "(unknown file)", 0, "(unknown function)"
    while hasattr(f, "f_code"):
        co = f.f_code
        filename = os.path.normcase(co.co_filename)
        if filename == _srcfile:
            f = f.f_back
            continue
        rv = (co.co_filename, f.f_lineno, co.co_name)
        break
    #rv = ('nssm.py', 37, 'post')
    
    tmpName = rv[0]
    if str(rv[0]).find('/') > -1 :
        tmplist = str(rv[0]).split('/')
        tmplist.reverse()
        tmpName = tmplist[0]
    
    fn = " ('" + tmpName + "':'" + rv[2] + "', " + str(rv[1]) + ")"
    return fn


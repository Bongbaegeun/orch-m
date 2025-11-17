'''
Created on 2015. 9. 12.

@author: ohhara
'''

import os, fcntl
import yaml
import logging

TITLE = 'orchm'
logger=logging.getLogger('TITLE')

class VarShared():
    
    def __init__(self, varName):
        self.varName = varName
    
    def _lock(self):
        fd = os.open(self.varName, os.O_RDWR|os.O_CREAT)
        fcntl.flock(fd, fcntl.LOCK_EX)
        return fd
    
    def _unlock(self, fd):
        fcntl.flock(fd, fcntl.LOCK_UN)
    
    def locked_read(self):
        fd = self._lock()
        logger.debug("lock file read")
        fileobj = os.fdopen(fd, 'r+b')
        
        data = fileobj.read()
        xdata = yaml.safe_load(data)
        
        fileobj.flush()
        os.fdatasync(fd)
        self._unlock(fd)
        logger.debug("unlock file read")
        
        fileobj.close()
        return xdata
    
    def locked_read_param(self, field):
        fd = self._lock()
        logger.debug("lock file Parameter read")
        fileobj = os.fdopen(fd, 'r+b')
    
        data = fileobj.read()
        xdata = yaml.safe_load(data)
        
        fileobj.flush()
        os.fdatasync(fd)
        self._unlock(fd)
        logger.debug("unlock file read")
        
        fileobj.close()
        
        try:
            if xdata.has_key(field):
                return xdata[field]
            else:
                return None
        except Exception, e:
            logger.exception( 'Fail to Read Global Var, field=%s'%str(field) )
            logger.fatal(e)
            return None
    
    def locked_write(self, data):
        fd = self._lock()
        logger.debug("lock file write")
        fileobj = os.fdopen(fd, 'w+b')

        yaml.safe_dump(data, fileobj, encoding='utf-8', default_flow_style=False, allow_unicode=True )
    
        fileobj.flush()
        os.fdatasync(fd)
        self._unlock(fd)
        logger.debug("unlock file write")
        
        fileobj.close()
        return data

    def locked_write_param(self, field, value):
        fd = self._lock()
        logger.debug("lock file write param")
        
        fileobj = os.fdopen(fd, 'rw+b')
        
        data = fileobj.read()
        xdata = yaml.safe_load(data)
        if xdata == None:
            xdata = {}
        
        if value == None :
            if xdata.has_key(field):
                xdata.pop(field)
        else:
            xdata[field] = value
        
        fileobj.seek(0)
        fileobj.truncate()
        yaml.safe_dump(xdata, fileobj, encoding='utf-8', default_flow_style=False, allow_unicode=True )
    
        fileobj.flush()
        os.fdatasync(fd)
        self._unlock(fd)
        logger.debug("unlock file write")
        
        fileobj.close()
        return xdata

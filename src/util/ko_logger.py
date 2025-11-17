# -*- coding: utf-8 -*-

##
# Copyright 2015 KT
# This file is part of KT One-Box Orchestrator
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
# For those usages not covered by the Apache License, Version 2.0 please
# contact with: ktnfv@kt.com
##

'''
KT One-Box Logger implementing the logging methods using python-logging library. 
It supports 4 basic levels, debug, info, warning, error, critical, and 
1 custom level, e2e which is for recording E-to-E trace logs about the main workflow of KT One-Box Orchestrator and has the highest level number.
To record e2e logs, call the method, .ete().
'''
__author__="Jechan Han"
__date__ ="$27-aug-2015 09:40:15$"

import sys, os
import logging
from logging import handlers

# add a custom log level for e2e trace logs
E2E_LOG_LEVEL_NUMBER = 100
E2E_LOG_LEVEL_NAME = "E2E"

logging.addLevelName(E2E_LOG_LEVEL_NUMBER, "E2E")
logging.addLevelName(logging.WARNING, "WARN")
logging.addLevelName(logging.DEBUG, "DEBUG")
logging.addLevelName(logging.INFO, "INFO")
logging.addLevelName(logging.ERROR, "ERROR")

def e2e(self, message, *args, **kws):
    self._log(E2E_LOG_LEVEL_NUMBER, message, args, **kws)

logging.Logger.e2e=e2e

def excp(self, msg, *aa, **kk):
    """
    Convenience method for logging an ERROR with exception information.
    """
    kk['exc_info'] = 1
    self._log(logging.CRITICAL, msg, aa, **kk)
logging.Logger.fatal = excp

class ko_logger():
    def __init__(self, tag="orch", logdir="/var/log/onebox/", loglevel="debug", logConsole=False, onlyLog=False):
        self.tag    = tag
        self.logdir = logdir
        self.loglevel = loglevel
        
        self.log_fname = "%s.log" % (tag)
        if onlyLog :
            self.errlog_fname = None
            self.e2e_fname = None
            self.exc_fname = None
        else:
            self.errlog_fname = "%s.err" % (tag)
            self.e2e_fname = "%s.e2e" % (tag)
            self.exc_fname = "%s.exc" % (tag)

        #script_dir = os.path.dirname(inspect.stack()[-1][1])
        #logdir = os.path.join(script_dir, 'log')

        if os.path.exists(logdir):
            self.filelog_file_path = os.path.join(logdir, self.log_fname)

            if not onlyLog :
                self.errlog_file_path  = os.path.join(logdir, self.errlog_fname)
                self.e2elog_file_path = os.path.join(logdir, self.e2e_fname)
                self.exclog_file_path = os.path.join(logdir, self.exc_fname)
        else:
            try:
                os.makedirs(logdir)
            except Exception, err:
                print err
                logdir = "/var/log/"

            self.filelog_file_path = os.path.join(logdir, self.log_fname)
            if not onlyLog :
                self.errlog_file_path  = os.path.join(logdir, self.errlog_fname)
                self.e2elog_file_path = os.path.join(logdir, self.e2e_fname)
                self.exclog_file_path = os.path.join(logdir, self.exc_fname)
        
        self.logger = logging.getLogger(tag)

#         self.logger.fatal = excp
        
        if loglevel == "debug":
            self.logger.setLevel(logging.DEBUG)
        elif loglevel == "info":
            self.logger.setLevel(logging.INFO)
        elif loglevel == "warning":
            self.logger.setLevel(logging.WARN)
        elif loglevel == "error":
            self.logger.setLevel(logging.ERROR)
        elif loglevel == "critical":
            self.logger.setLevel(logging.CRITICAL)
        else:
            self.logger.setLevel(logging.INFO)
        
        self._set_file_log_env(self.filelog_file_path)

        if not onlyLog :
            self._set_error_log_env(self.errlog_file_path)
            self._set_e2e_log_env(self.e2elog_file_path)
            self._set_exc_log_env(self.exclog_file_path)

        if logConsole:
            self._set_console_log_env()

    def get_instance(self):
        
        return self.logger

    def _set_error_log_env(self, logfile):

        errfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s][%(module)s.%(lineno)04d] %(message)s")

        maxbytes = 1024 * 1024 * 10  # 100MB
        error_handler = handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=5)
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(errfmt)

        self.logger.addHandler(error_handler)

    def _set_e2e_log_env(self, logfile):

        e2efmt = logging.Formatter("%(asctime)s %(levelname)-5s: %(message)s")

        maxbytes = 1024 * 1024 * 10  # 100MB
        e2e_handler = handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=5)
        e2e_handler.setLevel(E2E_LOG_LEVEL_NUMBER)
        e2e_handler.setFormatter(e2efmt)

        self.logger.addHandler(e2e_handler)

    def _set_exc_log_env(self, logfile):

        excfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s][%(module)s.%(lineno)04d] %(message)s")

        maxbytes = 1024 * 1024 * 10  # 100MB
        exc_handler = handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=5)
        exc_handler.setLevel(logging.CRITICAL)
        exc_handler.setFormatter(excfmt)

        self.logger.addHandler(exc_handler)
    
    def _set_file_log_env(self, logfile):
        if self.loglevel == "debug":
#             stdfmt = logging.Formatter("%(asctime)s [%(threadName)s-%(filename)s/%(funcName)s:%(lineno)03d] %(levelname)-5s: %(message)s")
            stdfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s] %(message)s [%(module)s.%(lineno)04d]")
        else:
            stdfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s] %(message)s [%(module)s.%(lineno)04d]")
            
        maxbytes = 1024 * 1024 * 10  # 100MB
        filelog_handler = handlers.RotatingFileHandler(logfile, maxBytes=maxbytes, backupCount=10)
        #filelog_handler = handlers.TimedRotatingFileHandler(logfile, when="midnight", backupCount=10)
        filelog_handler.setFormatter(stdfmt)
        self.logger.addHandler(filelog_handler)

    def _set_console_log_env(self):
#         stdfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s] %(message)s")
        stdfmt = logging.Formatter("[%(asctime)s][%(levelname)-5s] %(message)s [%(module)s.%(lineno)04d]")
        stdout_handler = logging.StreamHandler(sys.stdout)
        stdout_handler.setFormatter(stdfmt)
        self.logger.addHandler(stdout_handler)

if __name__ == '__main__':

    log = ko_logger(tag='orch_test', logdir='./log', loglevel='debug', logConsole=True).get_instance()

    log.debug("[aefa4a1e-c1a4-11e5-bd67-080027ca3ef9] debug message %s" % "test msg for debug")
    log.info("info message %s" % "test msg for info")
    log.e2e("E-to-E message %s" % "[NA][NA] test msg for E2E")
    log.propagate = False
    log.error("error message %s" % "test msg for error")
    log.propagate = True
    log.error("error message %s" % "test msg for error2")
    log.warning("error message %s" % "test msg for error2")
    kw = {'key':'val','key1':'val2'}
    log.debug("debug kw %s", kw)
    try:
        0/0
    except Exception, e:
        log.fatal(e)
#     log.exception(msg)

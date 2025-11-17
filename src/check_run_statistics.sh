#!/bin/bash

date +%Y-%m-%d_%T >> /root/orch-m/src/log/statistics.log

echo '=== Check statistics' >> /root/orch-m/src/log/statistics.log

cd /root/orch-m/src

pid=`ps -ef | grep 'python c_copyZbToOrchm.py' | grep -v 'grep' | awk '{print $2}'`

if [ -z $pid ]; then
        nohup python c_copyZbToOrchm.py > /dev/null 2>&1 &
        echo 'Restart c_copyZbToOrchm.py' >> /root/orch-m/src/log/statistics.log
fi


pid2=`ps -ef | grep 'python c_generator.py' | grep -v 'grep' | awk '{print $2}'`
if [ -z $pid2 ]; then
        nohup python c_generator.py > /dev/null 2>&1 &
        echo 'Restart c_generator.py' >> /root/orch-m/src/log/statistics.log
fi

pid3=`ps -ef | grep 'python c_removeData.py' | grep -v 'grep' | awk '{print $2}'`
if [ -z $pid3 ]; then
        nohup python c_removeData.py > /dev/null 2>&1 &
        echo 'Restart c_removeData.py' >> /root/orch-m/src/log/statistics.log
fi

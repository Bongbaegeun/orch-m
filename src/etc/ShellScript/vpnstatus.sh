#!/bin/bash

COUNT=$(redis-cli -n 2 get $1.vpnstatus)

if [ -z $COUNT ]
then
    echo ""
else
    echo $COUNT
fi

#!/bin/bash

COUNT=$(redis-cli -n 2 get $1)

if [ -z $COUNT ]
then
    echo ""
else
    echo $COUNT
fi

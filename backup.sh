#!/bin/bash

F_NAME="orch-m_$(date +%y%m%d_%H%M%S).tar.gz"
P_NAME="plugin_$(date +%y%m%d_%H%M%S).tar.gz"

EXEC_FILE="$0"
BASE_NAME=`basename "$EXEC_FILE"`
if [ "$EXEC_FILE" = "./$BASE_NAME" ] || [ "$EXEC_FILE" = "$BASE_NAME" ]; then
        FULL_PATH=`pwd`
else
        FULL_PATH=`echo "$EXEC_FILE" | sed 's/'"${BASE_NAME}"'$//'`
fi

tar -cvzf $F_NAME --exclude=$FULL_PATH/orch-m-v1/src/log --exclude=*.pyc --exclude=$FULL_PATH/orch-m-v1/src/.settings $FULL_PATH/orch-m-v1/*
tar -cvzf $P_NAME /usr/local/plugin/*

scp $F_NAME root@211.224.204.160:/home/ohhara/backup/orch-m/
scp $P_NAME root@211.224.204.160:/home/ohhara/backup/orch-m/

rm $F_NAME
rm $P_NAME


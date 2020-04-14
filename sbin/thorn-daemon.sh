#!/usr/bin/env sh

# This script controls the thorn server daemon initialization, status reporting
# and termination
# TODO: rotate logs

usage="Usage: thorn-daemon.sh (start|docker|stop|status)"

# this sript requires the command parameter
if [ $# -le 0 ]; then
  echo $usage
  exit 1
fi

# parameter option
cmd_option=$1

# if unset set thorn_home to directory root
export THORN_HOME=${THORN_HOME:-$(cd $(dirname $0)/..; pwd)}
echo ${THORN_HOME}

# get log directory
export THORN_LOG_DIR=${THORN_LOG_DIR:-${THORN_HOME}/logs}

# get pid directory
export THORN_PID_DIR=${THORN_PID_DIR:-/var/run}

mkdir -p ${THORN_PID_DIR} ${THORN_LOG_DIR}

# log and pid files
log=${THORN_LOG_DIR}/thorn-server-${USER}-${HOSTNAME}.out
pid=${THORN_PID_DIR}/thorn-server-${USER}.pid

case $cmd_option in
  (start)
    # set python path
    PYTHONPATH=${THORN_HOME}:${PYTHONPATH} \
      python ${THORN_HOME}/thorn/manage.py \
      db upgrade
    if [ $? -eq 0 ]
    then
      echo "DB migration: successful"
    else
      echo "Error on DB migration"
      exit 1
    fi
    PYTHONPATH=${THORN_HOME}:${PYTHONPATH} nohup -- \
      python ${THORN_HOME}/thorn/app/.py >> $log 2>&1 < /dev/null &
    thorn_server_pid=$!
    # persist the pid
    echo $thorn_server_pid > $pid
    echo "Thorn server started, logging to $log (pid=$thorn_server_pid)"
    ;;

  (docker)
    trap "$0 stop" SIGINT SIGTERM
    # set python path
    PYTHONPATH=${THORN_HOME}:${PYTHONPATH} \
      python ${THORN_HOME}/thorn/manage.py \
      db upgrade
    # check if the db migration was successful
    if [ $? -eq 0 ]
    then
      echo "DB migration: successful"
    else
      echo "Error on DB migration"
      exit 1
    fi
    PYTHONPATH=${THORN_HOME}:${PYTHONPATH} \
      python ${THORN_HOME}/thorn/app.py &
    thorn_server_pid=$!

    # persist the pid
    echo $thorn_server_pid > $pid

    echo "Thorn server started, logging to $log (pid=$thorn_server_pid)"
    wait
    ;;

  (stop)
    if [ -f $pid ]; then
      TARGET_ID=$(cat $pid)
      if [[ $(ps -p ${TARGET_ID} -o comm=) =~ "python" ]]; then
        echo "stopping thorn server, user=${USER}, hostname=${HOSTNAME}"
        (pkill -SIGTERM -P ${TARGET_ID} && \
          kill -SIGTERM ${TARGET_ID} && \
          rm -f $pid )
      else
        echo "no thorn server to stop"
      fi
    else
      echo "no thorn server to stop"
    fi
    ;;

  (status)
    if [ -f $pid ]; then
      TARGET_ID=$(cat $pid)
      if [[ $(ps -p "${TARGET_ID}" -o comm=) =~ "python" ]]; then
        echo "thorn server is running (pid=${TARGET_ID})"
        exit 0
      else
        echo "$pid file is present (pid=${TARGET_ID}) but thorn server not running"
        exit 1
      fi
    else
      echo thorn server not running.
      exit 2
    fi
    ;;

  (*)
    echo $usage
    exit 1
    ;;
esac

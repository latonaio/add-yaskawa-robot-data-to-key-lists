# coding: utf-8

# Copyright (c) 2019-2020 Latona. All rights reserved.

import os
from datetime import timezone, timedelta

import dateutil.parser
import redis

from aion.logger import initialize_logger, lprint
from aion.microservice import main_decorator, Options

SERVICE_NAME = "add-yaskawa-robot-data-to-key-lists"
initialize_logger(SERVICE_NAME)

# redis constants
IDENTIFIER = "YasukawaRobotData"
REDIS_HOST = os.environ.get("REDIS_HOST", "redis-cluster")
REDIS_PORT = os.environ.get("REDIS_PORT", 6379)
YASKAWA_DB_INDEX = 1  # Yaskawa


def get_command(metadata):
    if metadata is None:
        return ""

    command = metadata.get("Command")
    return "0x" + command.zfill(4) if command else ""


def get_unix_time(str_date):
    JST = timezone(timedelta(hours=+9), 'JST')
    return dateutil.parser.parse(str_date).astimezone(JST).timestamp() * (10 ** 6)


def set_to_redis(kanban):
    with redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=YASKAWA_DB_INDEX) as redis_connection:
        metadata = kanban.get_metadata()

        # 通信に失敗している場合
        robot_data = metadata.get('RobotData')
        if robot_data is None:
            lprint("RobotData is None")
            return

        timestamp = metadata.get("timestamp")
        unix_time = get_unix_time(timestamp)

        ip_address = metadata.get('TargetAddress')

        expire_time = int(robot_data.get("ExpireTime"))
        command = get_command(robot_data)

        if expire_time is None:
            expire_time = 1

        for pb_array_data in robot_data.get("RobotData"):
            array_data = pb_array_data

            array_no = int(array_data.get("ArrayNo"))

            if array_no is None:
                array_no = 0

            sort_list_key = "key-list:%s:%s:%s" % (ip_address, command, array_no)
            array_data_key = "%s,%s,%s,%s,%s" % (
                IDENTIFIER, ip_address, command, timestamp, array_no)

            lprint(unix_time, sort_list_key, array_data_key)

            # redisにhashとして書き込むためにstrに変換
            for key, val in array_data.items():
                array_data[key] = str(val)
            array_data["timestamp"] = timestamp

            # set metadata to redis
            redis_connection.hmset(array_data_key, array_data)
            if expire_time != 0:
                redis_connection.expire(array_data_key, expire_time)

            # set key_list
            redis_connection.zadd(sort_list_key, {array_data_key: unix_time})


@main_decorator(SERVICE_NAME)
def main(opt: Options):
    # get cache kanban
    conn = opt.get_conn()
    num = int(opt.get_number())

    try:
        for kanban in conn.get_kanban_itr(SERVICE_NAME, num):
            lprint("received kanban")
            set_to_redis(kanban)
    except Exception as e:
        print(str(e))
    finally:
        pass

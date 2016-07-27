#!/bin/bash

mkdir /tmp/mongod
nohup mongod -dbpath /tmp/mongod -port 33000 2>&1 >/tmp/mongod.out &

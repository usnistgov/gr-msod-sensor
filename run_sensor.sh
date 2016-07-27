#!/bin/bash

nohup python spectrum_monitor_sslsocket_capture_nogui.py -d spectrum.nist.gov --sensorId="NTIACommSensor-1" --mongod-port="33000"  --args "serial=30AD2C7" --source "uhd" --power-offset="0.0344282980111" --gain="30" --lo-offset="0" --sensorKey="30AD2C7" 2>&1 > /tmp/sensor.out &

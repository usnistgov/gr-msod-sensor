nohup python spectrum_monitor_sslsocket_capture_nogui.py -d $MSOD_WEB_HOST --sensorId=NistUsrpSensor1 --mongod-port=33000  --args "addr=usrp9" --source "uhd"   --power-offset  1.7783  --sensorKey=12345 --latitude 39 --longitude -77&
disown $*


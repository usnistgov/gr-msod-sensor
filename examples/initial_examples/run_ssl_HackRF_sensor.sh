#python spectrum_monitor_sslsocket.py -s 20e6 -F 1000 -c 50 --meas-interval 0.001 --bandwidth 20e6 --lna-gain 8 --vga-gain 4 -g 0 -d $1 --avoid-LO 724e6 9e6
python spectrum_monitor_sslsocket.py -F 1000 -c 50 -s 20e6 -d $1 --meas-interval 0.001 --bandwidth 20e6 --lna-gain 32 --vga-gain 40 -g 0 --avoid-LO 724e6 9e6

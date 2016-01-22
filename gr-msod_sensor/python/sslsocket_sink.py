#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2015 <+YOU OR YOUR COMPANY+>.
# 
# This is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this software; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

import numpy
from gnuradio import gr
from multiprocessing import Process
import socket
import ssl
import json
import struct
import sys
import os
import signal
import time
import traceback
from threading import Thread

def command_handler(capture_sink, trigger,sock,top_block,pid):
	print "command_handler : starting "  + str(pid)
	while True:
		try :
			command = sock.recv(1024)
			print "command = " , str(command)
			commandJson = json.loads(str(command))
		        print commandJson
			print ">>>>>>>>>>>>>>> Got something ",json.dumps(commandJson,indent=4)
			if commandJson["command"] == "arm" :
			   print "Arming trigger"
			   trigger.arm()
			   if "triggerParams" in commandJson:
				triggerParams = commandJson["triggerParams"]
				trigger.setTriggerParams(json.dumps(triggerParams))
			elif commandJson["command"] == "disarm" :
			   trigger.disarm()
			else:
			   os.kill(pid,signal.SIGUSR1)
			   os._exit(0)
		except:
			traceback.print_exc()
			os.kill(pid,signal.SIGUSR1)
			os._exit(0)
	
		

class sslsocket_sink(gr.sync_block):
    """
    docstring for block sslsocket_sink
    """
    def __init__(self, dtype, nitems_per_block, host,port,sys_msg,loc_msg,data_msg,capture_sink,trigger,top_block,pid):
        gr.sync_block.__init__(self,
            name="sslsocket_sink",
            in_sig=[(dtype, nitems_per_block)],
            out_sig=None)
	self.host = host
	self.port = port
   	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self.unwrapped_socket = sock
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,                                                                                                                     
                 struct.pack('ii', 1, 0))
  	sock.connect((self.host,self.port))
        self.sock =  ssl.wrap_socket(sock)
	self.sys_msg = sys_msg
	self.send_obj(sys_msg)
	self.loc_msg = loc_msg
	self.send_obj(loc_msg)
	self.data_msg = data_msg
	self.send_obj(data_msg)
	commandThread = Thread(target=command_handler,args=(capture_sink,trigger,self.sock,top_block,pid))
	commandThread.start()

    def reconnect(self,fStart,fStop):
	self.sock.close()
   	sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self.unwrapped_socket = sock
	sock.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER,                                                                                                                     
                 struct.pack('ii', 1, 0))
  	sock.connect((self.host,self.port))
        self.sock =  ssl.wrap_socket(sock)
	self.send_obj(self.sys_msg)
	self.send_obj(self.loc_msg)
	self.send_obj(self.data_msg)
	commandThread = Thread(target=command_handler,args=(capture_sink,trigger,self.sock,top_block,pid))
	commandThread.start()
        

    def send_obj(self, obj):
	msg = json.dumps(obj)
	frmt = "=%ds" % len(msg)
	packed_msg = struct.pack(frmt, msg)
	ascii_hdr = "%d\r" % len(packed_msg)
	self.sock.send(ascii_hdr)
	self.sock.send(packed_msg)

    def disconnect(self):
	print "ssl_socket_sink: disconnect"
	self.sock.close()


    def work(self, input_items, output_items):

        in0 = input_items[0]
        num_input_items = len(in0)
	for i in range(num_input_items):
	    try:
            	self.sock.send(in0[i])
	    except:
		self.unwrapped_socket.close()
		self.sock.close()
		return -1
        return num_input_items


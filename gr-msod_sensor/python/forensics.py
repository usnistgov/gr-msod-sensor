from pymongo import MongoClient
import json
import subprocess
import requests
import os
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager
import time

def analyze(algorithm,sensorId,timestamp,host):
    client = MongoClient("127.0.0.1",33000)
    db = client.iqcapture.dataMessages
    query = {"SensorID":sensorId,"t":{"$gte":timestamp}}
    print query
    iqsample = db.find_one(query)
    if iqsample != None:
       print "foundiqsample",iqsample
       del iqsample["_id"]
       fStart = iqsample["mPar"]["fStart"]
       fStop  = iqsample["mPar"]["fStop"]
       centerFreq = int((fStart + fStop)/2)
       samp_rate = int(iqsample["mPar"]["sampRate"])
       print json.dumps(iqsample, indent=4)
       capture_file = iqsample["_capture_file"]
       # cell_search_file.py -s 1.92M -f 2145M --repeat -c 19.2M /tmp/capture-1461265949
       fifoname = "/tmp/ltetrigger" 
       if not os.path.exists(fifoname):
          os.mkfifo(fifoname)  
       else:
	  print "fifo exists"
       p = subprocess.Popen(['/usr/bin/python', '/home/mranga/ltetrigger/gr-ltetrigger/examples/cell_search_file.py', "-f", str(centerFreq), "-s", str(samp_rate), "--fifoname", fifoname, capture_file ])
       pipein = open(fifoname,"r")
       result_length = int(pipein.readline())
       result = pipein.read(result_length)
       if result != None:
	  data = json.loads(result)
          iqsample["forensicsReport"] = data
          r = requests.post('https://'+host+':443/eventstream/postForensics/'+sensorId, verify=False, data=json.dumps(iqsample,indent=4))
	  if r.status_code != 200:
	     print "Post failed ", r.status_code
       else:
	  print "Error processing sample"
    else:
       print "could not find sample"

    client.close()

def garbage_collect(sensorId, timestamp):
    # TODO
    print "garbage_collect : ",sensorId,timestamp
      

def run_forensics(sensorId,host):
    client = MongoClient("127.0.0.1",33000)
    while True:
        db = client.iqcapture.dataMessages
        query = {"SensorID":sensorId}
        for iqsample in db.find(query):
                print "foundiqsample",iqsample
       		id1 = iqsample["_id"]
                del iqsample["_id"]
                fStart = iqsample["mPar"]["fStart"]
                fStop  = iqsample["mPar"]["fStop"]
                centerFreq = int((fStart + fStop)/2)
                samp_rate = int(iqsample["mPar"]["sampRate"])
                print json.dumps(iqsample, indent=4)
                capture_file = iqsample["_capture_file"]
                # cell_search_file.py -s 1.92M -f 2145M --repeat -c 19.2M /tmp/capture-1461265949
                fifoname = "/tmp/ltetrigger" 
                if not os.path.exists(fifoname):
                        os.mkfifo(fifoname)  
                else:
	                print "fifo exists"
                p = subprocess.Popen(['/usr/bin/python', '/home/mranga/ltetrigger/gr-ltetrigger/examples/cell_search_file.py', "-f", str(centerFreq), "-s", str(samp_rate), "--fifoname", fifoname, capture_file ])
                pipein = open(fifoname,"r")
                result_length = int(pipein.readline())
                result = pipein.read(result_length)
	        print "read result:"
                print result
                if result != None:
	                data = json.loads(result)
                        iqsample["forensicsReport"] = data
                        r = requests.post('https://'+host+':443/eventstream/postForensics/'+sensorId, verify=False, data=json.dumps(iqsample,indent=4))
	                if r.status_code != 200:
	                        print "Post failed ", r.status_code
                        else:
				print "Removing"
				del iqsample["forensicsReport"]
                                retval = client.iqcapture.dataMessages.remove(iqsample)
				print retval
                else:
	                print "Error processing sample"
                time.sleep(1)

    client.close()






	


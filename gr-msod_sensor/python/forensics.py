from pymongo import MongoClient

def analyze(algorithm,sensorId,timestamp,host):
    client = MongoClient("127.0.0.1",33000)
    db = client.iqcapture.dataMessages
    query = {"SensorID":sensorId,"t":{"$gte":timestamp}}
    print query
    iqsample = db.find_one(query)
    if iqsample != None:
       print "foundiqsample"
    else:
       print "could not find sample"

    client.close()

def garbage_collect(sensorId, timestamp):
    # TODO
    print "garbage_collect : ",sensorId,timestamp
      


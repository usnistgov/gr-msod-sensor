#!/usr/bin/python           # This is server.py file

import socket              # Import socket module
import myjsocket as jsocket
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.animation as animation
import matplotlib.colors as colors
import math
import threading
import time
from matplotlib.ticker import MultipleLocator
from timezone import formatTimeStampLong

SPEC_GRAM_DUR_SEC = 10.0

class SensorServer(threading.Thread):
    def run(self):
        global f, f_start, f_stop, bw, date_str, loc, ch_mag_sq_avg_plt, spec_gram, first_data_rcvd, Locked, Paused
        
        def get_data(c, MSGLEN):
            msg = ''
            while len(msg) < MSGLEN:
                chunk = c.recv(MSGLEN-len(msg))
                if not chunk:
                    break
                msg = msg + chunk
            return msg

        #host = socket.gethostname()                     # Get local machine name
	#host = "localhost"
	host = "192.168.0.1"
        port = 4001
        s = jsocket.JsonServer(address=host, port=port) # Create a socket server
        print 'Listening for client connection...'
        try:
            s.accept_connection()                       # Establish connection with client
        except KeyboardInterrupt:
            s.close()
            print 'Closed socket'
            return
        Locked = False

        try:
            msg = s.read_obj()
        except RuntimeError:
            print 'Error reading from socket'
            s.close()
            print 'Closed socket'
            return
        while msg['Type'] != 'Data':
            if msg['Type'] == 'Loc':
                loc = msg
                print loc, '\n'
            elif msg['Type'] == 'Sys':
                sys = msg
                print sys, '\n'
            else:
                print 'Warning: Received unknown message type'
            msg = s.read_obj()
            
        data_hdr = msg

        meas_ts = data_hdr['t']
        if data_hdr['mType'] == 'FFT-Power':
            f_start = data_hdr['mPar']['fStart']
            f_stop = data_hdr['mPar']['fStop']
            num_ch = data_hdr['mPar']['n']
            meas_dur = data_hdr['mPar']['tm']

        fc = (f_start + f_stop) / 2.0
        bw = f_stop - f_start
        f = map(lambda i: (f_start + i * bw/num_ch) / 1e6, range(num_ch))
        nmeas = max(1, int(math.ceil(1.0 / meas_dur)))   # Read 1-sec worth of measurements at a time.
        spec_gram = np.zeros( (num_ch, SPEC_GRAM_DUR_SEC/meas_dur), np.int8)
        f.append(f_stop/1e6)  ### Why needed?
        # Obtain time of acquisition in local time of sensor.
        # Subtract any DST offset that time.localtime() will add.
        date_str = formatTimeStampLong(meas_ts, loc['TimeZone'])
        print date_str+', fc =', fc/1e6, 'MHz; bw =', bw/1e6, 'MHz; N_ch =', num_ch, '; T_meas = {0:0.3f} ms'.format(meas_dur*1000)

        item_size = spec_gram.dtype.itemsize
        while windowOpen:
            data = get_data(s.conn, item_size*num_ch*nmeas)
            if len(data) < item_size*num_ch*nmeas:
                print 'Received partial measurement block'
                s.close()
                print 'Closed socket'
                return
            
            ch_power_dBm = np.fromstring(data, np.int8)
            ch_power_dBm.resize(nmeas, num_ch)

            if not Paused:
                Locked = True

                # Rotate new data in to right-most columns of spec_gram array.
                spec_gram[:, 0:-nmeas] = spec_gram[:, nmeas:]
                spec_gram[:, -nmeas:] = ch_power_dBm.transpose()
                
                # Compute average of received frames.
                ch_mag_sq = pow(10,(ch_power_dBm - 30) / 10.0)
                ch_mag_sq_avg = ch_mag_sq.mean(axis=0)
                # Repeat the first element of ch_mag_sq_avg for plotting only.
                ch_mag_sq_avg_plt = np.repeat(ch_mag_sq_avg, [2]+[1]*(len(ch_mag_sq_avg)-1))

                Locked = False
                first_data_rcvd = True

        s.close()
        print 'Closed socket'

first_data_rcvd = False
windowOpen = True
Paused = False

# Start thread to receive spectrum sensor data
display_thread = SensorServer()
display_thread.start()

while not first_data_rcvd:
    time.sleep(1)

fig, (ax1, ax2) = plt.subplots(2, 1)
#cax1, = ax1.step(f, 10*np.log10(ch_mag_sq_avg_plt) + 30.0)
cax1, = ax1.step(f, [0.0]*len(f))
cax2 = ax2.imshow(spec_gram, cmap=cm.spectral, interpolation='nearest', origin='lower', extent=(0, SPEC_GRAM_DUR_SEC, f_start/1e6, f_stop/1e6), aspect='auto')
cbar = fig.colorbar(cax2)
majorLocator = MultipleLocator(round(bw/10e6))
ax1.xaxis.set_major_locator(majorLocator)
ax1.set_ylim([-80.0, -40.0])
ax1.grid('on')
ax1.set_xlabel('f (MHz)')
ax1.set_ylabel('dBm')
ax2.set_xlabel('t (s)')
ax2.set_ylabel('f (MHz)')
cbar.set_label('dBm')
minorLocator = MultipleLocator(SPEC_GRAM_DUR_SEC/50)
ax2.xaxis.set_minor_locator(minorLocator)
ax1.ticklabel_format(useOffset=False)
ax2.ticklabel_format(useOffset=False)
norm = colors.Normalize(-80, -40)
cax2.set_norm(norm)

numrows, numcols = spec_gram.shape
def row_col(x, y):
    col = int(numcols * (x / SPEC_GRAM_DUR_SEC))
    row = int(numrows * (y * 1e6 - f_start) / (f_stop - f_start))
    return (row, col)
    
def format_coord(x, y):
    (row, col) = row_col(x, y)
    if col>=0 and col<numcols and row>=0 and row<numrows:
        z = spec_gram[row,col]
        return 't=%1.3f s     f=%1.3f MHz     p=%5.1f dBm'%(x, y, z)
    else:
        return 'f=%1.3f MHz, p=%1.1f dBm'%(x, y)

ax2.format_coord = format_coord

def onepress(event):
    if event.button != 1:
        return
    x, y = event.xdata, event.ydata
    if not (isinstance(x, float) and isinstance(y, float)):
        return
    (row, col) = row_col(x, y)
    if col>=0 and col<numcols and row>=0 and row<numrows:
        power_vec = spec_gram[:, col]
        power_vec = np.repeat(power_vec, [2]+[1]*(len(power_vec)-1))
        cax1.set_data(f, power_vec)
        #ax1.text((f_start + f_stop) / 2e6, -50.0, 't = {0:1.3f} s'.format(x), backgroundcolor='white')

def keypress(event):
    global Paused
    # Toggle Paused if the spacebar is pressed
    if event.key == 'alt+ ':
        Paused = not Paused

def zoom_factory(fig,ax,base_scale = 2.):
    def zoom_fun_x(event):
        # get the current x limits
        cur_xlim = ax.get_xlim()
        cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
        xdata = event.xdata # get event x location
        if event.button == 'up':
            # deal with zoom in
            scale_factor = 1/base_scale
        elif event.button == 'down':
            # deal with zoom out
            scale_factor = base_scale
        else:
            # deal with something that should never happen
            scale_factor = 1
            print event.button
        # set new limits
        new_xlim_min = max(xdata - cur_xrange*scale_factor, 0.0)
        new_xlim_max = min(xdata + cur_xrange*scale_factor, SPEC_GRAM_DUR_SEC)
        ax.set_xlim([new_xlim_min, new_xlim_max])
        #plt.draw() # force re-draw

    # attach the call back
    fig.canvas.mpl_connect('scroll_event',zoom_fun_x)

    #return the function
    return zoom_fun_x

fig.canvas.mpl_connect('button_press_event', onepress)
fig.canvas.mpl_connect('key_press_event', keypress)
ff = zoom_factory(fig,ax2,base_scale = 2.)

def updatefig(*args):
    if not Locked:
        #ch_mag_sq_avg_dBm = 10*np.log10(ch_mag_sq_avg_plt) + 30.0
        #cax1.set_data(f, ch_mag_sq_avg_dBm)
        #ax1.set_xticks([(f_start+i*8*180e3)/1e6 for i in range(7)])
        #ax1.set_xticks([(f_start+i*180e3)/1e6 for i in range(56)], minor=True)
        ax1.set_xlim([f_start/1e6, f_stop/1e6])
        #ax1.set_ylim([ch_mag_sq_avg_dBm.min() - 2, ch_mag_sq_avg_dBm.max() + 2])
        ax1.set_title(date_str+', ID %s (%.3f, %.3f)' % (loc['SensorID'], loc['Lat'], loc['Lon']))
        cax2.set_data(spec_gram)
        cax2.set_extent((0, SPEC_GRAM_DUR_SEC, f_start/1e6, f_stop/1e6))
    return cax1, cax2,

ani = animation.FuncAnimation(fig, updatefig, interval=200, blit=False)
plt.show()

windowOpen = False
display_thread.join()
print 'Exiting'

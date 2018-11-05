#!/usr/bin/env  python

import sys
import os
import time
import subprocess
import logging

remote_user_name = 'user_sap'
cords_dir = '/home/user_sap/cords/CORDS'
workload_home = cords_dir + '/systems/remote_zk/'

print ('ENTERING WORKLOAD')

def invoke_cmd(cmd):
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 	stderr=subprocess.PIPE)
	out, err = p.communicate()
	return (out, err)

def invoke_remote_cmd(machine_ip, command):
	cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 	stderr=subprocess.PIPE)
	out, err = p.communicate()
        print (out,err)
	return (out, err)

def run_remote(machine_ip, command):
	cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
	os.system(cmd)

def copy_file_to_remote(machine_ip, from_file_path, to_file_path):
	cmd = 'scp {0} {1}@{2}:{3}'.format(from_file_path, remote_user_name, machine_ip, to_file_path)
	os.system(cmd)

def copy_file_from_remote(machine_ip, from_file_path, to_file_path):
	cmd = 'scp {0}@{1}:{2} {3}'.format(remote_user_name, machine_ip, from_file_path, to_file_path)
	os.system(cmd)

#ZooKeeper-related Config
logging.basicConfig()


log_dir = None
servers = ['0', '1', '2']
ips = {}
server_dirs = {}

#assert len(sys.argv) >= 7

# The CORDS framework passes the following arguments to the workload program
# ceph_workload_read.py trace/cords workload_dir1 workload_dir2 .. workload_dirn remote_ip1 remote_ip2 .. remote_ipn [log_dir]
# For now assume only 3 nodes
for i in range(1, 4):
        print (sys.argv)
	ips[str(i-1)] = sys.argv[4 + i]

print ips

# For Ceph we have three servers and hence three directories
for i in range(1, 4):
        print("Server Dir " + str(i-1) + " is: " + str(sys.argv[i+1]))
	server_dirs[str(i-1)] = sys.argv[i + 1]

#if logdir specified
if len(sys.argv) >= 9:
	log_dir = sys.argv[-1]

# Kill all OSD daemons on remote nodes
print ("Stopping OSD Daemons")
for i in servers:
        print ("Killing OSD " + str(i))
	run_remote(ips[str(i)], "sudo systemctl stop ceph-osd@"+str(i))


# Write the config files with the correct workload directories
print ("Overwriting Conf file")
if ".mp" in server_dirs['0'] and ".mp" in server_dirs['1'] and ".mp" in server_dirs['2']:
    os.system('cp ceph_fuse.conf ceph.conf')
    print ("Sending fuse conf file")
elif ".mp" in server_dirs['0']: 
    os.system('cp ceph_0_corrupt.conf ceph.conf')
    print ("Sending ceph 0.mp conf file")
elif ".mp" in server_dirs['1']: 
    os.system('cp ceph_1_corrupt.conf ceph.conf')
    print ("Sending ceph 1.mp conf file")
elif ".mp" in server_dirs['2']: 
    os.system('cp ceph_2_corrupt.conf ceph.conf')  
    print ("Sending ceph 2.mp conf file")
else: 
    os.system('cp ceph_orig.conf ceph.conf')
    print ("Sending original conf file")
os.system('ceph-deploy --overwrite-conf admin instance-2 instance-3 instance-4')

time.sleep(3)

# Start 3 osd daemons
print ("Starting OSD Daemons")
for i in servers:
	run_remote(ips[str(i)], "sudo systemctl start ceph-osd@" + str(i))

time.sleep(3)

out = ''
err = ''
present_value = 'a' * 8192


if log_dir is not None:
    # Get state of ceph nodes before reading data
    client_log_file = os.path.join(log_dir, 'log-client')
    with open(client_log_file, 'w') as f:
	    f.write('Before workload\n')
	    status = []
	    for i in servers:
		out, err = invoke_remote_cmd(ips[i], 'ps aux | grep ceph')
		status.append('ceph' + str(i) + '.cfg' in out)
		out1, err1 = invoke_remote_cmd(ips[i], 'sudo ceph osd tree')
	    f.write(str(status) + '\n')
	    f.write('----------------------------------------------\n')
            print (str(out1))

out = ''
err = ''


input_str = str(raw_input('Do you wish to proceed with workload?: '))
print (input_str)
# Issue Reads on all the nodes in the cluster and check its value
#for server_index in ('0', '1', '2'):

        #print ('Running rados write on osd'+server_index)
invoke_remote_cmd(ips['0'], 'sudo rados -p scbench_132 put myobject0 sample_write.txt  > write_132.log')
        #time.sleep(5)
        #print ('Write done. Now running cache flushing on osd'+server_index)
        #invoke_remote_cmd(ips[server_index], 'sudo echo 3 | sudo tee /proc/sys/vm/drop_caches && sudo sync')
        #print ('Cache flush done')
        #time.sleep(5)
        #invoke_remote_cmd(ips[server_index], 'sudo rados -p scbench_132 get myobject'+server_index+' sample_read > read_seq.log')
        #invoke_remote_cmd(ips[server_index], 'sudo rados -p scbench_132 get myobject4 sample_read > read_seq.log')
time.sleep(1)
        #print ('Read done. Cleaning up rados on osd'+server_index)
#	invoke_remote_cmd(ips[server_index], 'sudo rados -p scbench_132 cleanup')
#        time.sleep(3)
#        print ('Clean up done.')

print ('written on osds')


if log_dir is not None:
	client_log_file = os.path.join(log_dir, 'log-client')
	with open(client_log_file, 'a') as f:
		f.write('After workload\n')
                print ("After workload ceph status")
		status = []
		for i in servers:
			out, err = invoke_remote_cmd(ips[i], 'ps aux | grep ceph')
			status.append('ceph' + str(i) + '.cfg' in out)
			out1, err1 = invoke_remote_cmd(ips[i], 'sudo ceph osd tree')
		f.write(str(status) + '\n')
		f.write('----------------------------------------------\n')


get_input = str(raw_input("Check the Rados Status --> "))

#Stop 3 osd daemons
print ("Stopping Daemons")
for i in servers:
	run_remote(ips[str(i)], "sudo systemctl stop ceph-osd@" + str(i))

time.sleep(3)

# Removing the resetting part at the end of every run. Since we need to check rados state 
print ("Resetting default ceph.conf on each node")
os.system('cp /home/user_sap/my-cluster/ceph_orig.conf /home/user_sap/my-cluster/ceph.conf')
os.system('ceph-deploy --overwrite-conf admin instance-2 instance-3 instance-4')

print ("Exiting Workload")

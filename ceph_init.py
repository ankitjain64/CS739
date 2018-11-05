#!/usr/bin/env  python

import sys
import os
import time
import subprocess
import logging

remote_user_name = 'user_sap'
cords_dir = '/home/user_sap/cords/CORDS'
workload_home = cords_dir + '/systems/ceph/'

ips = ['instance-2', 'instance-3','instance-4']

def invoke_cmd(cmd):
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 	stderr=subprocess.PIPE)
	out, err = p.communicate()
	return (out, err)

def invoke_remote_cmd(machine_ip, command):
	cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 	stderr=subprocess.PIPE)
	out, err = p.communicate()
	return (out, err)

def run_remote(machine_ip, command):
	cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
	os.system(cmd)

def copy_file_remote(machine_ip, from_file_path, to_file_path):
	cmd = 'scp {0} {1}@{2}:{3}'.format(from_file_path, remote_user_name, machine_ip, to_file_path)
	os.system(cmd)

print ("Deleting pool")
run_remote('instance-2','sudo ceph tell mon.\* injectargs \'--mon-allow-pool-delete=true\'')
run_remote('instance-2','sudo ceph osd pool delete scbench_132 scbench_132 --yes-i-really-really-mean-it')
os.system('sleep 2')
print ("Creating pool")
run_remote('instance-2','sudo ceph osd pool create scbench_132 132 132')
os.system('sleep 5')
print ("Initing pool")
run_remote('instance-2', 'sudo rbd pool init scbench_132')

print ('Running rados write on osd')
invoke_remote_cmd(ips[0], 'sudo rados -p scbench_132 put myobject4 sample_write.txt  > write_132.log')
time.sleep(5)
print ('Write done. Now running cache flushing')
invoke_remote_cmd(ips[0], 'sudo echo 3 | sudo tee /proc/sys/vm/drop_caches && sudo sync')
time.sleep(5)
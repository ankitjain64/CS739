#! /usr/bin/env python
# Copyright (c) 2016 Aishwarya Ganesan and Ramnatthan Alagappan.
# All Rights Reserved.
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import math
from collections import defaultdict
import subprocess
import argparse
import time
from threading import Timer

BLOCKSIZE = 4096
remote_user_name = 'user_sap'
ERRFS_HOME = os.path.dirname(os.path.realpath(__file__))
fuse_command_err = 'sudo nohup ' + ERRFS_HOME + "/errfs -f -oallow_other,modules=subdir,subdir=%s %s err %s %s %s > /dev/null 2>&1 &"
fuse_unmount_command = "sudo fusermount -u %s > /dev/null"
uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])

parser = argparse.ArgumentParser()
parser.add_argument('--trace_files', nargs='+', required = True, help = 'Trace file paths')
parser.add_argument('--machine_ips', nargs='+', required = True, help = 'Machine ips')
parser.add_argument('--data_dirs', nargs='+', required = True, help = 'Location of data directories')
parser.add_argument('--workload_command', type = str)
parser.add_argument('--cords_results_base_dir', type = str, default='/run/shm', help = 'Location for checker state and results')
parser.add_argument('--checker_command', type = str, help = 'Checker for workloads that modify application state')

uppath = lambda _path, n: os.sep.join(_path.split(os.sep)[:-n])

def kill_proc(proc, timeout):
	timeout["value"] = True
	proc.kill()

def invoke_cmd(cmd):
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
	out, err = p.communicate()
        print (out, err)
	return (out, err)

def invoke_remote_cmd(machine_ip, command):
	cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
	p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, 	stderr=subprocess.PIPE)
	out, err = p.communicate()
        print (out, err)
	return (out, err)

def copy_dir_from_remote(machine_ip, from_file_path, to_file_path):
	cmd = 'sudo scp -r {0}@{1}:{2} {3}'.format(remote_user_name, machine_ip, from_file_path, to_file_path)
	os.system(cmd)

def block_roundup(x):
    return math.ceil(x * 1.0 / BLOCKSIZE) * BLOCKSIZE

def block_rounddown(x):
    return math.floor(x * 1.0 / BLOCKSIZE) * BLOCKSIZE

def get_block_nrs(offset, size):
	start_offset = offset
	end_offset = start_offset + size
	total_blocks_touched = int((block_roundup(end_offset) - block_rounddown(start_offset)) / BLOCKSIZE)
	
	assert total_blocks_touched >= 1
	start_block_nr = int(math.floor(start_offset / BLOCKSIZE))
	return range(start_block_nr, start_block_nr + total_blocks_touched)

def create_deep_copy_commands(source,dest,block_size):
    print ("Creating commands for source " + str(source) + " Destination " + str(dest) + " size " + str(block_size) )
    cmd = 'sudo dd if=/dev/'+ str(source)+' of=/dev/' + str(dest)+ ' bs=' + str(block_size)+';'
    return cmd
data_dir_snapshots = []
data_dir_mount_points = []
args = parser.parse_args()


for i in range(0, len(args.trace_files)):
	args.trace_files[i] = os.path.abspath(args.trace_files[i])

for i in range(0, len(args.data_dirs)):
	args.data_dirs[i] = os.path.abspath(args.data_dirs[i])
	data_dir_snapshots.append(os.path.join(uppath(args.data_dirs[i], 1), os.path.basename(os.path.normpath(args.data_dirs[i]))+ ".snapshot"))
	data_dir_mount_points.append(os.path.join(uppath(args.data_dirs[i], 1), os.path.basename(os.path.normpath(args.data_dirs[i]))+ ".mp"))

trace_files = args.trace_files
data_dirs = args.data_dirs

assert len(trace_files) == len(data_dirs) and len(trace_files) == len(data_dir_snapshots) and len(trace_files) == len(data_dir_mount_points)
workload_command = args.workload_command
checker_command = args.checker_command
cords_results_base_dir = args.cords_results_base_dir
machine_ips = args.machine_ips

os.system('rm -rf ' + cords_results_base_dir+'/*')

replay_check_needed = False
if checker_command is not None and len(checker_command) > 0:
	replay_check_needed = True

err_map = defaultdict(set)
machines = []
machine = 0 
for trace_file in trace_files:
	machines.append(machine)
	assert os.path.exists(trace_file)
	assert os.stat(trace_file).st_size > 0
	with open(trace_file, "r") as f:
		for lines in f:
			line = lines.split('\t')
                        line = [l.strip() for l in line]
			if line[0] in ['rename', 'unlink', 'link', 'symlink']:
				pass
			else:
				assert len(line) == 4
				filename = line[0]
				op = line[1]
                                if 'meta' not in filename:
                                    #if 'meta' not in filename:
                                    continue

				assert op == 'w' or op == 'r' or op == 'a'
				offset = int(line[2])
				size = int(line[3])
				block_nrs = get_block_nrs(offset, size)

				for block_nr in block_nrs:
					err_map[(machine, filename)].add((op, block_nr))

	machine += 1

assert len(machines) > 0


def get_error_modes(op):
	if op == 'r':
		return ["eio", "cz", "cg"]
	elif op == 'w': 
		return ["eio"]
	elif op == 'a': 
		return ["eio", "esp"]
	else:
		assert False

def cords_count():
	total = 0
	for key in err_map:
		corrupt_machine = key[0]
		other_machines = [i for i in machines if i != corrupt_machine]
		assert len([corrupt_machine] + other_machines) == len(machines)
		corrupt_filename = key[1] 
		block_ops = list(err_map[key])
		
		for (op, block) in block_ops:
			possible_err_modes = get_error_modes(op)
			for err_type in possible_err_modes:
				total += 1

	return total
				
def cords_check():
	total = cords_count()
	count = 0
	for key in err_map:
		corrupt_machine = key[0]
		other_machines = [i for i in machines if i != corrupt_machine]
		assert len([corrupt_machine] + other_machines) == len(machines)
		corrupt_filename = key[1] 
		block_ops = list(err_map[key])
		
		for (op, block) in block_ops:
			possible_err_modes = get_error_modes(op)
			for err_type in possible_err_modes:
				dir_index = str(corrupt_filename).rfind(data_dirs[corrupt_machine]) + len(data_dirs[corrupt_machine]) + 1			
				log_dir =  'result_' + (str(corrupt_machine) + '_' + str(corrupt_filename[dir_index :]) + '_' + str(block) + '_' + str(op) + '_' + str(err_type)).replace('/', '_')
				log_dir_path =  os.path.join(cords_results_base_dir, log_dir)

                                if not os.path.exists(log_dir_path):
                                    os.makedirs(log_dir_path)
				
				print '\n\n\n'+str(op) + ' ' + str(corrupt_machine) + ':' + str(corrupt_filename) + ':' + str(block) + ':' + str(err_type)
				for mach in machines:
					#invoke_remote_cmd(machine_ips[mach], "sudo rm -rf " + data_dirs[mach]+"/current")

                                        #invoke_remote_cmd(machine_ips[mach], "sudo mkdir " + data_dirs[mach])
					invoke_remote_cmd(machine_ips[mach], "sudo cp -R " + data_dir_snapshots[mach]+'/. ' + data_dirs[mach])
                                        invoke_remote_cmd(machine_ips[mach], "sudo chown -R ceph:ceph " + data_dirs[mach])

                                        #Making Journal Deep Copy
                                        print ("Making Journal deep copy from sdc2 to sdc1")
	                                invoke_remote_cmd(machine_ips[mach], create_deep_copy_commands("sdc2","sdc1",4096))


                                        #changing links of newly created data dir 
                                        print ("changing link in datadir")
                                        link_command = "sudo rm -rf "+ data_dirs[mach]+ "/journal;"
                                        link_command += "sudo ln -s /dev/sdc1 "+ data_dirs[mach]+ "/journal;"
                                        link_command += "sudo chown -h ceph:ceph "+ data_dirs[mach]+ "/journal;" 
	                                invoke_remote_cmd(machine_ips[mach], link_command)

                                        print ('removed and copied from snapshot on osd'+str(mach))               

				invoke_remote_cmd(machine_ips[corrupt_machine], "sudo rm -rf " + data_dir_mount_points[corrupt_machine])	
				invoke_remote_cmd(machine_ips[corrupt_machine], "sudo mkdir " + data_dir_mount_points[corrupt_machine])	

                                fuse_start_command = fuse_command_err%(data_dirs[corrupt_machine], data_dir_mount_points[corrupt_machine], corrupt_filename, block, err_type)
				print (fuse_start_command)

                                invoke_remote_cmd(machine_ips[corrupt_machine], fuse_start_command)
				os.system('sleep 1')


				data_dir_curr = []
				for mach in machines:
					data_dir_curr.append(data_dir_mount_points[mach] if corrupt_machine == mach else data_dirs[mach])
				assert len(data_dir_curr) == len(machines)				

                                print ('Called errfs now calling workload ')
				workload_command_curr = workload_command + " cords "
				for ddc in data_dir_curr:
					workload_command_curr +=  ddc + " "

				for mach in machines:
					workload_command_curr +=  machine_ips[mach] + " "

				workload_command_curr += log_dir_path + " "

				for mach in machines:
				    invoke_remote_cmd(machine_ips[mach], "rm -rf " + log_dir_path)
				    invoke_remote_cmd(machine_ips[mach], "mkdir -p " + log_dir_path)
				
                               
                                print ('Should error now has - ')
				#for mach in machines:
				invoke_remote_cmd(machine_ips[corrupt_machine], "sudo cat /tmp/shoulderr")
				invoke_remote_cmd(machine_ips[corrupt_machine],"sudo rm -rf /tmp/shoulderr")
				invoke_remote_cmd(machine_ips[corrupt_machine],"sudo touch /tmp/shoulderr")
                                invoke_remote_cmd(machine_ips[corrupt_machine],"sudo chown user_sap:user_sap /tmp/shoulderr")
                                invoke_remote_cmd(machine_ips[corrupt_machine]," sudo echo \'fals\' >> /tmp/shoulderr")

                                print ('Invoking workload command ' + workload_command_curr)
				os.system(workload_command_curr)
                                print ("Workload completed")
				out = ''
                                err = ''
                                outfile = os.path.join(log_dir_path, 'workload.out')
                                print ("Outfile " + str(outfile))
				os.system("rm -rf " + outfile)
				os.system("touch " + outfile)
				with open(outfile, 'a+') as f:
					f.write(out + '\n' + err + '\n')
					
				fuse_unmount = fuse_unmount_command%(data_dir_mount_points[corrupt_machine]) 
				unmount_kill_command = fuse_unmount + '; sleep 1; killall errfs'
                                print ("Invoking kill command " + str(unmount_kill_command) + " on Machine " + machine_ips[corrupt_machine])
				invoke_remote_cmd(machine_ips[corrupt_machine], unmount_kill_command)

				
                                for mach in machines:
				    invoke_remote_cmd(machine_ips[mach], "sudo mv /tmp/shoulderr " + log_dir_path)

				count += 1
				print 'States completed:' + str(count) + '/' + str(total)
				#if count == 2:
			        get_input = str(raw_input("Ready to go to the next error?: "))
                                print (get_input + '\n')


start_test = time.time()
cords_check()

print ('Returning everything to original state')
for mach in machines:
    print ("Doing processing for machine " + str(mach) + " machine ip is " + str(machine_ips[mach]) + '\n')
    invoke_remote_cmd(machine_ips[mach], "sudo rm -rf " + data_dirs[mach]+ "/current")

    #invoke_remote_cmd(machine_ips[mach], "sudo mkdir " + data_dirs[mach])
    invoke_remote_cmd(machine_ips[mach], "sudo cp -R " + data_dir_snapshots[mach]+'/. ' + data_dirs[mach])
    invoke_remote_cmd(machine_ips[mach], "sudo chown -R ceph:ceph " + data_dirs[mach])

    #Making Journal Deep Copy
    print ("Making Journal deep copy from sdc2 to sdc1")
    invoke_remote_cmd(machine_ips[mach], create_deep_copy_commands("sdc2","sdc1",4096))

    #changing links of newly created data dir 
    print ("changing link in datadir")
    link_command = "sudo rm -rf "+ data_dirs[mach]+ "/journal;"
    link_command += "sudo ln -s /dev/sdc1 "+ data_dirs[mach]+ "/journal;"
    link_command += "sudo chown -h ceph:ceph "+data_dirs[mach]+"/journal;"
    invoke_remote_cmd(machine_ips[mach], link_command)


print 'cords-check done!'
end_test = time.time()
print 'Testing took ' + str((end_test - start_test)) + ' seconds...'


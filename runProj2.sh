#!/bin/bash
echo "Running ceph_init"
python ../cords/CORDS/systems/ceph/ceph_init.py

echo "Running Trace"
python ../cords/CORDS/remotetrace.py --trace_files /home/user_sap/trace0 /home/user_sap/trace1 /home/user_sap/trace2 --data_dirs /var/lib/ceph/osd/ceph-0 /var/lib/ceph/osd/ceph-1 /var/lib/ceph/osd/ceph-2 --workload_command 'python ../cords/CORDS/systems/ceph/ceph_workload_read.py' --machines instance-2 instance-3 instance-4

#sleep 3s

#echo "Running Cords"

#python ../cords/CORDS/remotecords.py --trace_files /home/user_sap/trace0 /home/user_sap/trace1 /home/user_sap/trace2 --data_dirs /var/lib/ceph/osd/ceph-0 /var/lib/ceph/osd/ceph-1 /var/lib/ceph/osd/ceph-2 --workload_command 'python ../cords/CORDS/systems/ceph/ceph_workload_read.py' --machine_ips instance-2 instance-3 instance-4

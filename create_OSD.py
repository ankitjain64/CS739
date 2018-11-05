import subprocess
import os

remote_user_name = 'user_sap'

def invoke_remote_cmd(machine_ip, command):
    cmd = 'ssh {0}@{1} \'{2}\''.format(remote_user_name, machine_ip, command)
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE,   stderr=subprocess.PIPE)
    out, err = p.communicate()
    print(out)
    return (out, err)

invoke_remote_cmd('instance-2','python reset_OSD.py')
invoke_remote_cmd('instance-3','python reset_OSD.py')
invoke_remote_cmd('instance-4','python reset_OSD.py')
os.system('sleep 5')
os.system('cp ceph_orig.conf ceph.conf')
os.system('ceph-deploy --overwrite-conf admin instance-2 instance-3 instance-4')
os.system('ceph-deploy osd create --data /dev/sdb1 instance-2 --filestore --journal /dev/sdc1')
os.system('ceph-deploy osd create --data /dev/sdb1 instance-3 --filestore --journal /dev/sdc1')
os.system('ceph-deploy osd create --data /dev/sdb1 instance-4 --filestore --journal /dev/sdc1')

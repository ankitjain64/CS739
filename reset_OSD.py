import subprocess
res = []
def invoke_cmd(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = p.communicate()
    res.append(out)
    return (out, err)

invoke_cmd('sudo ceph osd out 0')
invoke_cmd('sudo ceph osd destroy 0 --yes-i-really-mean-it')
invoke_cmd('sudo umount /var/lib/ceph/osd/ceph-0')
(o,e) = invoke_cmd('sudo lvdisplay')
value = o.split('\n')[3].split()[-1]+'/'+o.split('\n')[2].split()[-1]
#print('sudo lvremove -f ' + value)
invoke_cmd('sudo lvremove -f ' + value)
invoke_cmd('sudo ceph-volume lvm zap /dev/sdb1')
invoke_cmd('sudo ceph-volume lvm zap /dev/sdc1')
invoke_cmd('sudo ceph osd crush remove 0')
invoke_cmd('sudo ceph osd rm 0')
print('\n'.join(res))

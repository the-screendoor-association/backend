# off_device.py: logic for off-device programming

import os
import executive, screendoor

MOUNT_PATH = '/mnt'
PARTION_FILE_PATH = '/proc/partitions'

def mount_device():
    parts = []
    with open(PARTITION_FILE_PATH, 'r') as pf:
        for line in pf.readlines()[2:]:
            words = [word.strip() for word in line.split()]
            name = words[3]
            if len(name) > 3 and name[:2] == 'sd':
                parts.append(name)
    for part in parts:
        os.system('mount /dev/{} {}'.format(part, MOUNT_PATH))
        for listfile in ['blacklist.txt', 'whitelist.txt', 'wildcards.txt']:
            if os.path.isfile('{}/{}'.format(MOUNT_PATH, listfile)):
                return part
        os.system('umount /dev/{}'.format(part))
    return None

def append_lists(partition):
    allfiles = {'{}/blacklist.txt'.format(MOUNT_PATH):screendoor.path_blacklist,
            '{}/whitelist.txt'.format(MOUNT_PATH):screendoor.path_whitelist,
            '{}/wildcards.txt'.format(MOUNT_PATH):screendoor.path_wildcards, } 
    existingfiles = {}
    for listfile in allfiles.keys():
        if os.path.isfile(listfile):
            filelist[listfile] = allfiles[listfile]
    for listfile in existingfiles.keys():
        with open(existingfiles[listfile], 'a') as afile:
            with open(listfile, 'r') as rfile:
                for line in rfile.readlines():
                    afile.write(line)
    os.system('umount /dev/{}'.format(partition))

def replace_lists(partition):
    allfiles = {'{}/blacklist.txt'.format(MOUNT_PATH):screendoor.path_blacklist,
            '{}/whitelist.txt'.format(MOUNT_PATH):screendoor.path_whitelist,
            '{}/wildcards.txt'.format(MOUNT_PATH):screendoor.path_wildcards, } 
    existingfiles = {}
    for listfile in allfiles.keys():
        if os.path.isfile(listfile):
            filelist[listfile] = allfiles[listfile]
    for listfile in existingfiles.keys():
        with open(existingfiles[listfile], 'w') as wfile:
            with open(listfile, 'r') as rfile:
                for line in rfile.readlines():
                    wfile.write(line)
    os.system('umount /dev/{}'.format(partition))

def reload_lists():
    executive.load_blacklist()
    executive.load_whitelist()
    executive.restore_wildcards()


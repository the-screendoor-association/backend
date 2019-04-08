# off_device.py: logic for off-device programming

import os
import string
import re
import executive, screendoor

MOUNT_PATH = '/mnt'
PARTITION_FILE_PATH = '/proc/partitions'
USB_DRIVE_PARTITION_MARKER_FILE = 'screendoor.sdp'

def mount_device():
    parts = []
    with open(PARTITION_FILE_PATH, 'r') as pf:
        for line in pf.readlines()[2:]:
            words = [word.strip() for word in line.split()]
            name = words[3]
            if len(name) >= 3 and name[:2] == 'sd':
                parts.append(name)
    subparts = []
    for part in parts:
        if len(part) == 3:
            subparts.append(part)
        else:
            for subp in subparts:
                if part.startswith(subp):
                    parts.remove(subp)
                    subparts.remove(subp)
    for part in parts:
        os.system('sudo mount /dev/{} {}'.format(part, MOUNT_PATH))
        if os.path.isfile('{}/{}'.format(MOUNT_PATH, USB_DRIVE_PARTITION_MARKER_FILE)):
                return part
        os.system('sudo umount /dev/{}'.format(part))
    return None

def append_lists(partition):
    allfiles = {'{}/blacklist.txt'.format(MOUNT_PATH):screendoor.path_blacklist,
            '{}/whitelist.txt'.format(MOUNT_PATH):screendoor.path_whitelist,
            '{}/wildcards.txt'.format(MOUNT_PATH):screendoor.path_wildcards} 
    file_verification = {'{}/blacklist.txt'.format(MOUNT_PATH):verify_list,
            '{}/whitelist.txt'.format(MOUNT_PATH):verify_list,
            '{}/wildcards.txt'.format(MOUNT_PATH):verify_wildcards} 
    existingfiles = {}
    for listfile in allfiles.keys():
        if os.path.isfile(listfile) and file_verification[listfile](listfile):
            existingfiles[listfile] = allfiles[listfile]
    for listfile in existingfiles.keys():
        with open(existingfiles[listfile], 'a') as afile:
            with open(listfile, 'r') as rfile:
                for line in rfile.readlines():
                    afile.write(line)
    os.system('sudo umount /dev/{}'.format(partition))
    reload_lists()

def replace_lists(partition):
    allfiles = {'{}/blacklist.txt'.format(MOUNT_PATH):screendoor.path_blacklist,
            '{}/whitelist.txt'.format(MOUNT_PATH):screendoor.path_whitelist,
            '{}/wildcards.txt'.format(MOUNT_PATH):screendoor.path_wildcards} 
    file_verification = {'{}/blacklist.txt'.format(MOUNT_PATH):verify_list,
            '{}/whitelist.txt'.format(MOUNT_PATH):verify_list,
            '{}/wildcards.txt'.format(MOUNT_PATH):verify_wildcards} 
    existingfiles = {}
    for listfile in allfiles.keys():
        if os.path.isfile(listfile) and file_verification[listfile](listfile):
            existingfiles[listfile] = allfiles[listfile]
    for listfile in existingfiles.keys():
        with open(existingfiles[listfile], 'w') as wfile:
            with open(listfile, 'r') as rfile:
                for line in rfile.readlines():
                    wfile.write(line)
    os.system('sudo umount /dev/{}'.format(partition))
    reload_lists()

def copy_lists(partition):
    filelist = {screendoor.path_blacklist:'{}/blacklist.txt'.format(MOUNT_PATH),
            screendoor.path_whitelist:'{}/whitelist.txt'.format(MOUNT_PATH),
            screendoor.path_wildcards:'{}/wildcards.txt'.format(MOUNT_PATH)}
    for listfile in filelist:
        os.system('sudp cp {} {}'.format(listfile, filelist[listfile]))
    os.system('sudo umount /dev/{}'.format(partition))
        

def reload_lists():
    executive.load_blacklist()
    executive.load_whitelist()
    executive.restore_wildcards()

def verify_list(listfile):
    with open(listfile, 'r') as rfile:
        for line in rfile:
            for char in line.strip():
                if char not in string.digits:
                    return False
    return True

def verify_wildcards(wildfile):
    with open(wildfile, 'r') as rfile:
        for line in rfile:
            try:
                re.match(line.rstrip(), '')
            except re.error:
                return False
    return True


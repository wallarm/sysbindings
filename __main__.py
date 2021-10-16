#!/usr/bin/python3 -u
import os, sys
import signal
import logging
import argparse
import time
import yaml
import hashlib

__first_run__ = None
__exit_trigger__ = None

def file_hash(filename):
    with open(filename, 'r') as fd:
        return hashlib.sha1(fd.read().encode("utf-8")).hexdigest()

def get_content(filename, after=None, before=None):
    ret = {}
    with open(filename, 'r') as fd:
        for line in fd.readlines():
            line = line.strip(' \n')
            if len(line) == 0: # skip blank
                continue
            if line[0] == '#': # skip commented
                continue

            # Parse entry
            parts = line.split('=')
            if len(parts) != 2: # skip wrong entry
                continue
            key = parts[0].strip(' ')
            value = parts[1].strip(' ')

            ret[key] = value
    return ret

def put_content(filename, content, top_cap='### --- BEGIN SYSBINDINGS DAEMON --- ###', bottom_cap='### --- END SYSBINDINGS DAEMON --- ###'):
    new = ''

    # Save old file
    saved = []
    try:
        with open(filename, 'r') as fd:
            saved = fd.readlines()
    except FileNotFoundError:
        saved = []

    # Calculate block
    to_put = []
    for k, v in content.items():
        to_put.append('{}={}\n'.format(k, v))

    # Find the place to replace
    replace_begin = -1
    replace_end = -1
    for i in range(0, len(saved)):
        line = saved[i]
        if len(line) < len(top_cap):
            continue
        if line[0:len(top_cap)] == top_cap:
            replace_begin = i
    for i in range(0, len(saved)):
        line = saved[i]
        if len(line) < len(bottom_cap):
            continue
        if line[0:len(bottom_cap)] == bottom_cap:
            replace_end = i
    if replace_begin < 0 and replace_end < 0: # Have not configured yet
        # Just put to end
        new = ''.join(saved) + '\n' + top_cap + '\n' + ''.join(to_put) + bottom_cap + '\n'
    else:
        # Replace
        new = ''.join(saved[:replace_begin] + [top_cap + '\n'] + to_put + [bottom_cap + '\n'] + saved[replace_end+1:])

    with open(filename, 'w') as fd:
        fd.seek(0)
        fd.write(new)

    return new

def check_valid_entry(entry, path, chroot='/'):
    chroot = chroot.strip('/')
    if chroot != "":
        chroot = '/' + chroot 
    path = path.strip('/')
    if path != "":
        path = '/' + path
    binding = entry.replace('.', '/')
    fullpath = chroot + path + '/'
    if not os.path.isfile(fullpath + binding):
        logging.warning("skipping \"{}\": entry doesn't exists in \"{}\" tree".format(entry, fullpath))
        return False
    return True

def get_config(filename):
    ret = {}
    with open(filename, 'r') as fd:
        ret = yaml.load(fd, Loader=yaml.Loader)
    return ret

def patch_and_validate_config(cli, config):
    # Patching
    if 'chroot_path' in list(config.keys()):
        chroot_path = config['chroot_path']
    elif os.getenv('SYSBINDINGS_CHROOT_PATH'):
        chroot_path = os.getenv('SYSBINDINGS_CHROOT_PATH')
    else:
        chroot_path = '/sys'

    if 'sysctl_conf_path' in list(config.keys()):
        sysctl_conf_path = config['sysctl_conf_path']
    elif os.getenv('SYSBINDINGS_SYSCTL_CONF_PATH'):
        sysctl_conf_path = os.getenv('SYSBINDINGS_SYSCTL_CONF_PATH')
    else:
        sysctl_conf_path = '/etc/sysctl.conf'

    if 'sysfs_conf_path' in list(config.keys()):
        sysfs_conf_path = config['sysfs_conf_path']
    elif os.getenv('SYSBINDINGS_SYSFS_CONF_PATH'):
        sysfs_conf_path = os.getenv('SYSBINDINGS_SYSFS_CONF_PATH')
    else:
        sysfs_conf_path = '/etc/sysfs.conf'

    if 'sysctl_path' in list(config.keys()):
        sysctl_path = config['sysctl_path']
    elif os.getenv('SYSBINDINGS_SYSCTL_PATH'):
        sysctl_path = os.getenv('SYSBINDINGS_SYSCTL_PATH')
    else:
        sysctl_path = '/proc/sys'

    if 'sysfs_path' in list(config.keys()):
        sysfs_path = config['sysfs_path']
    elif os.getenv('SYSBINDINGS_SYSFS_PATH'):
        sysfs_path = os.getenv('SYSBINDINGS_SYSFS_PATH')
    else:
        sysfs_path = '/sys'

    if 'interval' in list(config.keys()):
        interval = config['interval']
    elif os.getenv('SYSBINDINGS_INTERVAL'):
        interval = os.getenv('SYSBINDINGS_INTERVAL')
    else:
        interval = '60'
    try:
        interval = int(interval)
    except:
        if __first_run__:
            logging.warning("invalid interval \"{}\", fallback to default \"60\"".format(interval))
        interval = 60

    # Validating    
    verified_sysctls = dict([(x, y) for (x, y) in config['sysctl'].items() if check_valid_entry(x, sysctl_path, chroot=chroot_path)])
    verified_sysfss = dict([(x, y) for (x, y) in config['sysfs'].items() if check_valid_entry(x, sysfs_path, chroot=chroot_path)])

    # Reconstruct config
    return {
        'sysctl': verified_sysctls,
        'sysfs': verified_sysfss,
        'chroot_path': chroot_path,
        'sysctl_conf_path': sysctl_conf_path,
        'sysfs_conf_path': sysfs_conf_path,
        'sysctl_path': sysctl_path,
        'sysfs_path': sysfs_path,
        'interval': interval,
    }

def reread_config(filename, config):
    new_config = get_config(filename)

    # Validating
    verified_sysctls = dict([(x, y) for (x, y) in new_config['sysctl'].items() if check_valid_entry(x, config['sysctl_path'], chroot=config['chroot_path'])])
    verified_sysfss = dict([(x, y) for (x, y) in new_config['sysfs'].items() if check_valid_entry(x, config['sysfs_path'], chroot=config['chroot_path'])])

    config['sysctl'] = verified_sysctls
    config['sysfs'] = verified_sysfss

    return config

def apply(config):
    chroot = config['chroot_path'].strip('/')
    if chroot != "":
        chroot = '/' + chroot
    
    # Patching files
    put_content(chroot + '/' + config['sysctl_conf_path'].strip('/'), config['sysctl'])
    put_content(chroot + '/' + config['sysfs_conf_path'].strip('/'), config['sysfs'])

    # Apply bindings
    for fs in ['sysctl', 'sysfs']:
        path = config[fs + '_path'].strip('/')
        if path != "":
            path = '/' + path
        for k, v in config[fs].items():
            if fs == 'sysctl':
                binding = k.replace('.', '/')
            else:
                binding = k
            fullpath = chroot + path + '/'
            with open(fullpath + binding, 'w') as fd:
                fd.write(str(v))

def sleep(interval):
    global __exit_trigger__
    for i in range(0, interval):
        if not __exit_trigger__:
            time.sleep(1)

def term_signal(num, frame):
    global __exit_trigger__
    logging.info("stopping daemon")
    __exit_trigger__ = True

def main():
    global __first_run__
    global __exit_trigger__

    __first_run__ = True
    parser = argparse.ArgumentParser(
        prog='sysbindings',
        description='Little toolkit for control the sysctl/sysfs bindings on Kubernetes Cluster on the fly '
                    'and without unnecessary restarts of cluster or node pool. Allows to control managed '
                    'and/or own-architected and/or own-managed clusters because uses only well-known '
                    'tehniques.',
    )
    parser.add_argument('--config', help='use specified configuration file', action='store')
    parser.add_argument('--oneshot', help='just apply configuration and exit, no daemonize', action='store_true')
    parser.add_argument('--loglevel', help='log verbosity: DEBUG, INFO, WARNING or ERROR', action='store')

    cli = parser.parse_args().__dict__

    loglevel = os.getenv('LOGLEVEL')
    if cli['loglevel'] != None:
        loglevel = cli['loglevel']
    if loglevel == None:
        loglevel = 'WARNING'

    logging.basicConfig(
        format='%(asctime)s [%(levelname)s:%(name)s] %(message)s',
        level=str(loglevel).upper(),
    )

    config_file = os.getenv('SYSBINDINGS_CONFIG')
    if cli['config'] != None:
        config_file = cli['config']
    if config_file == None:
        config_file = '/opt/sysbindings/sysbindings.yaml'

    # Initial reading configuration
    config = get_config(config_file)

    # Rebuilding config
    config = patch_and_validate_config(cli, config)

    # Single run and exit
    if cli['oneshot']:
        logging.info("running in oneshot mode")
        apply(config)

        return 0

    __first_run__ = False

    # Prepare daemonization
    __exit_trigger__ = False
    signal.signal(signal.SIGTERM, term_signal)
    signal.signal(signal.SIGINT, term_signal)
    logging.info("starting daemon")
    if os.getpid() != 1:
        logging.info("daemon pid is {}".format(os.getpid()))

    # Daemonize
    config_file_hash = ""
    while not __exit_trigger__:
        new_config_file_hash = file_hash(config_file)
        if config_file_hash != new_config_file_hash:
            config_file_hash = new_config_file_hash
            config = reread_config(config_file, config)
            apply(config)
        
        # Wait for next round
        sleep(config['interval'])

    return 0

if __name__ == "__main__":
    sys.exit(main())

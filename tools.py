import os
import inspect
#import pkgutil
#import types
from definitions import *
import json
import subprocess
import socket
from shutil import copyfile
import subprocess
import platform
import numpy as np
import copy
import re
import datetime as dt
import time
from pytz import timezone
import math
import psutil

numBytesTotal = 12000
numBytesPerWrite = 12
mspWriteCtrl = 0x20
mspReadCtrl = 0x40

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    
    
# hardware dependent imports
try:
    from Adafruit_BBIO.SPI import SPI
except:
    print(bcolors.WARNING + "Module Adafruit_BBIO not installed" + bcolors.ENDC)

def announceError(node, task_name, err):
    print(("missing argument: %s" % err))
    payload = {key_message: task_name, 'payload': 'missing argument: ' + str(err)}
    node.messenger.publish(ANNOUNCE_TOPIC_BASE + node.mac_address, payload=json.dumps(payload))

def updateDirInit(directory, iterative=False):
    if iterative:
        directories = [x[0] for x in os.walk(directory)]
    else:
        directories = [directory]
    
    for directory in directories:
        files = os.listdir(directory)
        pyfiles = [x for x in files if x[-3:] == '.py' and \
                                   '__init__.py' not in x]
        subdirs = next(os.walk(directory))[1]
        with open(os.path.join(directory,'__init__.py'),'w') as f:
            for subdir in subdirs:
                f.write('from . import ' + subdir + '\n')
            f.write('\n')
            for pyfile in pyfiles:
                f.write('from . import ' + pyfile[0:-3] + '\n')

def getAllClassesDict(base_package):
    packages = [base_package] + getSubPackages(base_package, iterative=True)
    modules = []
    for package in packages:
        modules += getModules(package)
    classes = []
    for a_module in modules:
        classes += getClasses(a_module)
    classes_dict = {}
    for a_class in classes:
        classes_dict[getObjPath(a_class)] = a_class
    #print('-'*30)
    #print('Available sensors found')
    #for i in sorted(classes_dict.keys()):
        #print(i)
    #print('-'*30)
    return classes_dict
    
def getAllFunctionsDict(base_package):
    packages = [base_package] + getSubPackages(base_package, iterative=True)
    modules = []
    for package in packages:
        modules += getModules(package)
    functions = []
    for a_module in modules:
        functions += getFunctions(a_module)
    functions_dict = {}
    for a_function in functions:
        functions_dict[getObjPath(a_function)] = a_function
    return functions_dict

def getUserFunctionsDict(base_package):
    functions_dict = getAllFunctionsDict(base_package)
    user_functions = []
    for i in sorted(functions_dict.keys()):
        if (('<lambda>' not in i) and ('._' not in i) and ('.__' not in i) and ('tools' not in i)):
            user_functions.append(i)
    return user_functions
    
def getObjPath(obj_in):
    return obj_in.__module__+'.'+obj_in.__name__

def getClasses(module):
    out = []
    for name, obj in inspect.getmembers(module):
        if inspect.isclass(obj):
            out.append(obj)
    return out
    
def getFunctions(module):
    out = []
    for name, obj in inspect.getmembers(module):
        if inspect.isfunction(obj):
            out.append(obj)
    return out
    
def getModules(package):
    out = []
    for name, obj in inspect.getmembers(package):
        if inspect.ismodule(obj) and \
           inspect.getsourcefile(obj)[-11:] != '__init__.py':
            out.append(obj)
    return out  
#------------------------------------------------------------------            
def getSubPackages(package,iterative=False):
    if not iterative:
        out = []
        for name, obj in inspect.getmembers(package):
            if inspect.ismodule(obj) and \
               inspect.getsourcefile(obj)[-11:] == '__init__.py':
                out.append(obj)
        return out
    else:
        out = []
        
        # iterative depth first search
        s = []
        s.insert(0,package)
        while len(s) != 0:
            v = s.pop(0)
            if v not in out:
                out.append(v)
                for x in getSubPackages(v):
                    s.insert(0,x)
        return out
#------------------------------------------------------------------    
def getMacAddress():
    mac = None
    if platform.system() == "Linux":

        interfaces = psutil.net_if_addrs()
        target_interfaces = ['eth0', 'eth1', 'en0', 'wlan0']

        # Check for specific interfaces
        for interface in target_interfaces:
            if interface in interfaces:
                for addr in interfaces[interface]:
                    if addr.family == psutil.AF_LINK:
                        # Some Jetsons got the same mac address, skip if we find it. 
                        if addr.address == "36:08:fc:c6:ef:4b":
                            continue
                        return addr.address.replace(':','')

        # Check for the first interface that starts with 'e'
        for interface in interfaces:
            if interface.startswith('e'):
                for addr in interfaces[interface]:
                    if addr.family == psutil.AF_LINK:
                        return addr.address.replace(':','')

        if mac is None:
            # if there is no connection, return a default and hope for best
            print('**ERROR: Unable to determine mac address....')
            print('-> Using default mac address: 00:00:00:00:00:00')
            return '000000000000'

        return None

    elif platform.system() == "Windows":
        nics = psutil.net_if_addrs()
        for each in nics:
            if 'Ethernet' in each:
                mac = nics[each][0].address
                break
        if mac is None:
            for each in nics:
                if 'Wi-Fi' in each:
                    mac = nics[each][0].address
                    break
        if mac is None:
            # if there is no connection, return a default and hope for best
            print('**ERROR: Unable to determine mac address....')
            print('-> Continuing and hoping for the best!')
            print('-> Using default mac address: 00:00:00:00:00:00')
            return '000000000000'
        mac = mac.replace('-', '')
        return mac

# ------------------------------------------------------------------
def search_and_replace(source, template_string, new_value):
    if(isinstance(source,str)):
        if template_string in source:
            return source.replace(template_string, new_value)
        else:
            return source
    elif(isinstance(source,list)):
        for item_idx in range(len(source)):
            source[item_idx] = search_and_replace(source[item_idx], template_string, new_value)
        return source
    elif(isinstance(source,dict)):
        for key in source:
            source[key] = search_and_replace(source[key], template_string, new_value)
        return source
    else:
        return source
#------------------------------------------------------------------
def saveConfigurationToFile(node):
    # check for dummy gps and if it exists, get the coordinates to save
    haveGPS = any([x for x in node.sensors._list if 'sensors.locationing' in getObjPath(x.__class__)])
    if haveGPS:
        gps = node.sensors.getAnySensor('sensors.locationing')
        lat, lon, alt = gps.getLocation()

    # create a new system.json based on node + gps
    if node.system is not None:
        newsystem = node.system
        newsystem['broker_name'] = node.broker_name
        newsystem['short_name'] = node.short_name
        newsystem['group_name'] = node.group_name
        if haveGPS:
            idx = 0
            for kk in range(len(newsystem['sensors'])):
                if 'sensors.locationing' in newsystem['sensors'][kk]['type']:
                    idx = kk
            newsystem['sensors'][idx][key_latitude] = float(lat)
            newsystem['sensors'][idx][key_longitude] = float(lon)
            newsystem['sensors'][idx][key_altitude] = float(alt)
        try:
            newsystem['jobs'] = node.jobs
        except:
            pass
        if node.config_version is not None:
            newsystem[key_config_version] = node.config_version
        node.system = newsystem
    else:
        with open('system.json.old') as fp:
            newsystem = json.load(fp)
        # create a system.json based on old file
        if node.broker_name != None:
            newsystem['broker_name'] = node.broker_name
        if node.short_name != None:
            newsystem['short_name'] = node.short_name
        if node.group_name != None:
            newsystem['group_name'] = node.group_name
        if haveGPS:
            idx = 0
            for kk in range(len(newsystem['sensors'])):
                if 'sensors.locationing' in newsystem['sensors'][kk]['type']:
                    idx = kk
            newsystem['sensors'][idx][key_latitude] = float(lat)
            newsystem['sensors'][idx][key_longitude] = float(lon)
            newsystem['sensors'][idx][key_altitude] = float(alt)
        if node.jobs != None:
            newsystem['jobs'] = node.jobs
        node.system = newsystem

    # save the templated mac address
    mac_address = getMacAddress()
    tmp = copy.deepcopy(node.system)
    # some keys are only useful during runtime and shouldn't be saved
    try:
      del tmp[key_disable_jobs]
    except:
      pass
    tmp = search_and_replace(tmp, mac_address, '$$MAC_ADDRESS$$')
    # save to file
    with open('system.json.new','w') as fp:
        json.dump(tmp,fp,indent=4,sort_keys=True,separators=(',',':'), default=str)
    # rename file
    os.rename('system.json.new','system.json')
#------------------------------------------------------------------
def computeDistanceFromLatLon(oldLat,oldLon,newLat,newLon):
    '''
    computeDistanceFromLatLon(oldLat,oldLon,newLat,newLon)

    Returns the distance (in meters) between two lat/lon coordinates.
    Based on haversine formula.

    '''
    # based on the haversine formula in radians
    # dist = R*c
    # c = 2*atan2(a^(1/2), (1-a)^(1/2))
    # a = sin(dlat/2)^2 + cos(oldLat)*cos(newLat)*sin(dlon/2)^2
    
    R = float(6371e3) # earth's mean radius in meters
    # convert everything to radians
    oldLat = oldLat/float(180)*np.pi
    oldLon = oldLon/float(180)*np.pi
    newLat = newLat/float(180)*np.pi
    newLon = newLon/float(180)*np.pi
    
    deltaLat = newLat-oldLat
    deltaLon = newLon-oldLon

    haversine = np.sin(deltaLat/2)**2 + np.cos(oldLat)*np.cos(newLat)*np.sin(deltaLon/2)**2
    dist = R*2*np.arctan2(np.sqrt(haversine),np.sqrt(1-haversine))
    return dist
#------------------------------------------------------------------
def disk_usage(path):
    ''' returns the total, used, and available memory in GB for a given path'''
    import shutil
    txt = shutil.disk_usage(path)
    size = round(txt[0] / 1024 ** 3, 1)
    used = round(txt[1] / 1024 ** 3, 1)
    available = round(txt[2] / 1024 ** 3, 1)
    return size, used, available

#------------------------------------------------------------------
def get_disk_free():

    # Determine free disk space
    size, used, available = disk_usage('/')
    return available

#------------------------------------------------------------------
def get_disk_used():

    # Determine disk spaced used
    size, used, available = disk_usage('/')
    return used

#------------------------------------------------------------------
def get_memory_percentage():
    import psutil
    return psutil.virtual_memory()[2]

#------------------------------------------------------------------
def get_cpu_percentage():
    import psutil
    if platform.system() == "Linux":
        return os.getloadavg()[0]
    elif platform.system() == "Windows":
        return psutil.cpu_percent()

#------------------------------------------------------------------
def rh_hardware_attached():

    return 

#------------------------------------------------------------------
def read_os_version():
    '''
    This function determines the OS version of the local host
    (assuming it is a Raspberry Pi).  This is achieved by reading
    the file /etc/os-release and returning a formatted version of
    the PRETTY_NAME.

    by Nik Kleber, 5/1/17
    '''
    if platform.system() == "Linux":

        # open file /etc/os-release and read PRETTY_NAME (first line)
        with open('/etc/os-release','r') as fp:
            myline = fp.readline()

        # remove \n and whitespace
        myline = myline.strip()
        # get rid of label PRETTY_NAME
        components = myline.split('=')
        # get rid of extra quotes
        osName = components[1].strip('"')

        osVersion = ''
        result = subprocess.run(['dpkg-query','--show','nvidia-l4t-core'],stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode == 0:
            osName += " Jetpack"
            osVersion = result.stdout.strip().split()[1]
        elif os.path.isfile("/etc/debian_version"):
            osVersion = subprocess.check_output(["cat","/etc/debian_version"], text=True).strip()

        return osName, osVersion
    
    elif platform.system() == "Windows":
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        
            # Get OS name
            osName = platform.system()

            # Get OS version
            osVersion, _ = winreg.QueryValueEx(key, "ProductName")
        
            return osName, osVersion
        except Exception as e:
            print(f"An error occurred: {e}")
        return None, None

#------------------------------------------------------------------
def read_hardware_version():
    '''
    This function determines the hardware revision number of the
    local host (assuming it is a Raspberry Pi).  This is achieved by
    reading the file /proc/cpuinfo and returning a formatted version
    of the Revision value.

    by Nik Kleber, 5/1/17
    '''
    if platform.system() == "Linux":
        hardwareType = None
        hardwareVersion = open('/proc/device-tree/model').read()
        if 'jetson' in hardwareVersion.lower() or 'orin' in hardwareVersion.lower():
          hardwareType = 'Jetson'
        if 'beaglebone' in hardwareVersion.lower():
          hardwareType = 'BeagleBone'
        if 'raspberry' in hardwareVersion.lower():
          hardwareType = 'Raspberry Pi'
        return hardwareType, hardwareVersion
    elif platform.system() == "Windows":
        import wmi
        try:
            c = wmi.WMI()
            for system in c.Win32_ComputerSystem():
                manufacturer = system.Manufacturer
                model = system.Model
            hardwareVersion = manufacturer + ' ' + model
            return manufacturer, hardwareVersion
        except Exception as e:
            print("Error:", e)
            return None

# ------------------------------------------------------------------
def load_calibration_data():
  if os.path.isfile(calFileCache):
    calFileHandle = open(calFileCache,'r')
    calibration_data = json.load(calFileHandle)
    calFileHandle.close()
    return calibration_data
# ------------------------------------------------------------------
def read_rh_hardware_version(node):
    '''
    This function determines the radiohound hardware revision number
    '''
    rh_hardware_attached = False
    rh_hardware_version = ''
    rh_board_id = ''
    if node.mspVersion not in [0,255]:
      rh_hardware_attached = True
      if node.calibration_data is not None:
        rh_hardware_version = node.calibration_data['hw_version']
        rh_board_id = node.calibration_data['board_id']
      
    return rh_hardware_attached, rh_hardware_version, rh_board_id
# ------------------------------------------------------------------
def get_host_name():
    return socket.gethostname()
# ------------------------------------------------------------------
def get_job_id(node):
    '''
    This function will return the job id when that functionality is added
    '''
    return node.jobs
# ------------------------------------------------------------------
def get_percent_complete(node):
    #getting percentcomplete key from node memory
    rfSensor = node.sensors.getAnySensor("sensors.rf.receiver")
    if rfSensor is None or rfSensor.percentComplete is None:
        percent = None
    else:
        percent = str(100*(rfSensor.percentComplete))
    return percent
# ------------------------------------------------------------------
def get_kernel_version():
    if platform.system() == "Linux":
        kernelVersion = subprocess.check_output(["/bin/uname","-r"]).decode("utf-8").strip()
    else:
        kernelVersion = "N/A"
    return kernelVersion
# ------------------------------------------------------------------
def get_bootloader_version():
    hdmi_enabled = 0
    if subprocess.call(["/bin/grep -q BeagleBoard /etc/issue"], shell=True,text=True):
        return 'NA'
    if os.path.isfile("/opt/scripts/tools/version.sh"):
      version_cmd = "/opt/scripts/tools/version.sh" 
    elif os.path.isfile("/usr/bin/beagle-version"):
      version_cmd = "/usr/bin/beagle-version"

    valid_bootloader = 0
    try:
        bootloaders = {}
        output = subprocess.check_output([version_cmd],shell=True,text=True)
        for line in output.splitlines():
            if "bootloader" in line:
                #bootloader:[microSD-(push-button)]:[/dev/mmcblk0]:[U-Boot 2019.04-00002-g23f263cc3f]:[location: dd MBR]
                regex = re.search(r'.*bootloader:\[(.*?)-.*\].*U-Boot (.*?)\].*',line)
                drive = regex.group(1)
                version = regex.group(2)
                bootloaders[drive] = version
                #print("Bootloader " + drive + ": " + version)
            if "uboot_overlay_options" in line and "disable_uboot_overlay_video=0" in line:
                hdmi_enabled = 1
    except Exception as err:
        print("ERROR: Failed getting bootloader data " + str(err))
        failure = 1
        return None


    # We boot from eMMC by default, so check to see if we have valid bootloader (version 2017 through 2019)
    # Otherwise, check microSD
    #print("Checking for valid bootloader...",)
    if 'eMMC' in bootloaders.keys():
        emmcregex = re.search(r'201[789]',bootloaders['eMMC'])
        if emmcregex is not None:
            valid_bootloader = 1
            bootloader = 'eMMC'
            bootloader_version = bootloaders['eMMC']
    else:
        if 'microSD' in list(bootloaders.keys()):
            microregex = re.search(r'201[789]',bootloaders['microSD'])
            if microregex is not None:
                valid_bootloader = 1
                bootloader = 'microSD'
                bootloader_version = bootloaders['microSD']
    
    if valid_bootloader:
        #print("OK: " + bootloader + ": " + bootloader_version)
        return bootloader + ": " + bootloader_version, hdmi_enabled
    else:
        #print("ERROR: Bootloader too old")
        return None
# ------------------------------------------------------------------
def check_beagle():
    if subprocess.call(["/bin/grep -q BeagleBoard /etc/issue"], shell=True,text=True):
        return False
    else:
        return True
# ------------------------------------------------------------------
def check_network_connection(address,timeout=2):
    if platform.system() == "Linux":
        response = subprocess.call(["ping","-c", "1","-W",str(timeout),address], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
    elif platform.system() == "Windows":
        response = subprocess.call(["ping","-n", "1","-w",str(timeout * 1000),address], stdout=open(os.devnull, 'wb'), stderr=open(os.devnull, 'wb'))
    if response == 0:
        return True
    else:
        return False
# ------------------------------------------------------------------
def setup_mqtt_tunnel(address,timeout=2):
    # Check if the SSH tunnel process is running
    try:
        if platform.system() == "Windows":
            ps_output = subprocess.check_output(["tasklist"], text=True)
        elif platform.system() == "Linux":
            ps_output = subprocess.check_output(["ps", "ax"], text=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing ps command: {e}")
        return -1

    tunnel_running = False
    for line in ps_output.splitlines():
        if 'ssh' in line and f"8083:localhost:1883" in line:
            tunnel_running = True
            break

    if not tunnel_running:
        # If the tunnel is not running and we are on Linux, try to establish it
        if platform.system() == "Linux" and os.path.exists("/bin/nc"):
            try:
                output = subprocess.check_call(
                    ["/bin/nc", "-z", "-v", "-w", str(timeout), address, "22"],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE
                )
                if output == 0:
                    try:
                        ps_output = subprocess.check_output(["ps", "ax"], text=True)
                        if f"8083:localhost:1883" not in ps_output:
                            print(f"Setting up SSH tunnel to {address}")
                            cmd = (
                                f'AUTOSSH_POLL=10 /usr/bin/autossh -f -N -L 8083:localhost:1883 '
                                f'-i /opt/icarus/.ssh/id_rsa -o GlobalKnownHostsFile=/dev/null '
                                f'-o StrictHostKeyChecking=no git@{address}'
                            )
                            subprocess.call(cmd, shell=True)
                            return 0
                        else:
                            return -1
                    except subprocess.CalledProcessError as e:
                        print(f"Error setting up SSH tunnel: {e}")
                        return -1
                else:
                    print(f"Can't SSH to {address}, aborting tunnel")
                    return -2
            except subprocess.CalledProcessError:
                return -2
        else:
            print(f"Can't SSH to {address}, aborting tunnel")
            return -3

    # Check if we can connect to the specified local port
    try:
        with socket.create_connection(('localhost', 8083), timeout):
            return 0
    except (socket.timeout, ConnectionRefusedError, OSError):
        return -4
# ------------------------------------------------------------------
def getIPAddress(publicOnly=False):
    # check platform
    myOS = platform.system()
    # reboot based on platform
    if myOS == "Linux":
        RetMyIP = subprocess.getoutput("hostname -I").rstrip() # returns the IP address of local host as a string
    elif myOS == "Windows":
        RetMyIP = subprocess.run(['ipconfig'], capture_output=True, text=True).stdout
        ipFinder = re.compile(r'IPv4 Address[. ]*: (\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})')
        RetMyIP = ipFinder.findall(RetMyIP)
        RetMyIP = ' '.join(RetMyIP)
    else:
        print("Command does not work outside Linux")
        RetMyIP = ''
    if publicOnly:
      return RetMyIP.replace('192.168.7.2','').replace('192.168.6.2','').rstrip().split(' ')[0]
    else:
      return RetMyIP
# ------------------------------------------------------------------
def get_ansible_timestamp():
    if os.path.isfile(ANSIBLE_TIMESTAMP):
        handle = open(ANSIBLE_TIMESTAMP, 'r')
        timestamp = handle.read()
        handle.close()
        return int(timestamp.strip())
    else:
        return None
#---------------------
def getGitBranch():
    try:
        gitBranch = subprocess.run(['git', 'branch'], capture_output=True, text=True, check=True).stdout

        # Use regular expression to find the current branch
        currentBranch = re.search(r'^\* (.+)', gitBranch, re.MULTILINE)
        if currentBranch:
            return currentBranch.group(1)
        else:
            return "No branch found or not a git repository"

    except subprocess.CalledProcessError as e:
        return f"Error occurred: {e}"
#---------------------
def feedback(name_fn,success,node,message=None, browser_guid=None, traceback=None, requested_args=None):
    if node.messenger.connected:
        topic = FEEDBACK_TOPIC_BASE+node.mac_address
        if browser_guid is not None:
          topic += "/" + browser_guid
          # We might want to default to "all" or something?
        #print(f"feedback: topic {topic} guid {browser_guid}")
        payload = {'task':name_fn,'status':success, 'message':message,'traceback':traceback,'requested_args':requested_args}
        infot = node.messenger.publish(topic,payload=json.dumps(payload))
        return infot
#---------------------
def publish_message(node, topic, payload):
    # Decode the payload to get rid of bytestrings 
    payload_decoded = {}
    for key in payload.keys():
        if isinstance(payload[key],bytes):
            payload_decoded[key] = payload[key].decode('utf-8')
        else:
            payload_decoded[key] = payload[key]

    keys = ['timestamp','latitude','longitude','short_name']
    printed_payload = {}
    for each in payload:
        if each in keys:
            printed_payload[each] = payload_decoded[each]

    if node.messenger.connected:
        print("Sending payload to " + topic + ": " + str(printed_payload) + "...")
        node.messenger.publish(topic,payload=json.dumps(payload_decoded),qos=2)
    else:

        print("MQTT not connected, saving to file " + OFFLINE_STORE_FILE + ": " + str(printed_payload))
        payload = {'topic':topic,'payload':payload_decoded}
        # should add a mutex around here
        output = open(OFFLINE_STORE_FILE, 'a')
        output.write(json.dumps(payload, default=str) + "\r\n")
        output.close()

    # Send locally which doesn't require network check, also send last to prioritize network performance
    node.local_messenger.publish(topic,payload=json.dumps(payload_decoded),qos=0)

    #if "job_id" in payload['metadata']:
        #print("Found background job, saving locally")
        #output = open(OFFLINE_STORE_FILE+"-" + node.mac_address + "-" + dt.datetime.now().strftime("%Y%m%d"), 'a')
        #output.write(json.dumps(payload) + "\r\n")
        #output.close()



def validate():
    adc_status_cmd = "/opt/icarus/.virtualenvs/python3.9/bin/python3.9 /opt/radiohound/scripts/ADCstatusandVersion.py"

    strformat = '%-37s'
    pins = {}
    pins["p9.11"] = "uart"
    pins["p9.13"] = "uart"
    pins["p9.24"] = "uart"
    pins["p9.26"] = "uart"
    pins["p9.17"] = "spi"
    pins["p9.18"] = "spi"
    pins["p9.21"] = "spi"
    pins["p9.22"] = "spi"
    failure = 0
    msp_version = ''
    action_code = 255
    bootloader_version, hdmi_enabled = get_bootloader_version()
    return_vars = {'hostname': get_host_name(),
                   'kernelVersion': get_kernel_version(),
                   'bootloaderVersion': bootloader_version,
                   'gitBranch': getGitBranch(),
                   'ansibleTimestamp': str(dt.datetime.fromtimestamp(get_ansible_timestamp()))}

    _, return_vars['debianVersion'] = read_os_version()

    print(strformat % "Hostname:", return_vars['hostname'])
    print(strformat % "Mac Address:", getMacAddress())
    print(strformat % "IP Address:", getIPAddress(publicOnly=True))
    print(strformat % "OS version:", return_vars['debianVersion'].lstrip())
    print(strformat % "Kernel version:", return_vars['kernelVersion'])
    print(strformat % "Bootloader version:", return_vars['bootloaderVersion'])
    print(strformat % "Git branch:", return_vars['gitBranch'])
    print(strformat % "Ansible timestamp:", return_vars['ansibleTimestamp'])

    print(strformat % "Checking config-pin...", end=' ')

    try:
        pin_failure = 0
        for each in list(pins.keys()):
            output = subprocess.check_output(["/usr/bin/config-pin","-q",each],stderr=subprocess.STDOUT,text=True).strip()
            if pins[each] not in output:
                #print("ERROR: " + output + ", expected " + pins[each])
                #if failure == 0:
                #print("ERROR: pin " + each + " not setup: " + output)
                pin_failure = 1
        if pin_failure == 0:
            print("OK")
        else:
            print("WARN: one or more pins not configured, rectifying...", end=' ')
            pin_failure = 0
            for each in list(pins.keys()):
                output = subprocess.check_output(["/usr/bin/config-pin",each,pins[each]],text=True)
            # Recheck output
            for each in list(pins.keys()):
                output = subprocess.check_output(["/usr/bin/config-pin","-q",each],stderr=subprocess.STDOUT,text=True).strip()
                if pins[each] not in output:
                    pin_failure = 1
            if pin_failure:
                print("ERROR")
            else:
                print("OK")
    except Exception as err:
        print("ERROR: Failed getting pin status" + str(err))
        failure = 1


    print(strformat % "Checking for disabled HDMI...", end=' ')
    if hdmi_enabled:
        print("ERROR: still enabled")
        failure = 1
    else:
        print("OK")

    print(strformat % "Checking PRU firmware...", end=' ')
    try:
        output = subprocess.check_output(["stat","/lib/firmware/beaglelogic-pru1-fw"],text=True)
        firmware_found = 0
        for line in output.splitlines():
            if "File:" in line:
                if "beaglelogic-pru1-radiohound" in line:
                    firmware_found = 1
                    print("OK")
                else:
                    firmware_found = 1
                    (_, firmware) = line.split("  File: ")
                    print("ERROR: " + firmware)
                    failure = 1
        if not firmware_found:
            print("ERROR: Couldn't find firmware")
            failure = 1

    except:
        print("ERROR: Failed getting PRU Firmware")



    try:
        print(strformat % "Resetting MSP...", end=' ')
        subprocess.check_output(["/opt/icarus/icarus/fieldupdate/reset"],shell=True,text=True)
        time.sleep(1)
        print("OK")
    except:
        print("ERROR: Could not reset MSP")
        failure = 1


    try:
        print(strformat % "Checking MSP status...", end=' ')
        retry_MSP_check = 0
        while( retry_MSP_check <= 2 ):
            output = subprocess.check_output([adc_status_cmd],shell=True,text=True)
            for line in output.splitlines():
                if "Version of MSP" in line:
                    (msp_version,_) = line.split("Version of MSP code ")[1].split(" - ")
                    msp_version = msp_version.strip()
                    if msp_version is None or msp_version == "0" or "Unknown MSP version." in line:
                        print("WARN: Can't detect MSP, attempting to reset..." + str(line), end=' ')
                        retry_MSP_check += 1
                        try:
                            subprocess.check_output(["/opt/icarus/icarus/fieldupdate/reset"],shell=True,text=True)
                            time.sleep(retry_MSP_check * 5) # Use a backoff delay to let SPI boot up 
                        except:
                            pass
                        break
                    elif msp_version == "255":
                        print("ERROR: No Radiohound board detected")
                        failure = 1
                    else:
                        print("OK: " + msp_version)
                    
                if "ADC is " in line:
                    print(strformat % "Checking ADC state...", end=' ')
                    retry_MSP_check = 4
                    if "ADC is off" in line:
                        print("WARN: ADC is off, attempting to activate...", end=' ')
                        subprocess.check_output(["/usr/bin/python","/opt/icarus/icarus/spi_interface/msp_spi_inter.py","900000000","1","0b0110101111111111"],text=True)
                        output = subprocess.check_output([adc_status_cmd],shell=True,text=True)
                        for line in output.splitlines():
                            if "ADC is " in line:
                                if "ADC is off" in line or "ADC is unknown" in line:
                                    print("ERROR: " + line)
                                    failure = 1
                                    break
                                elif "ADC is on" in line:
                                    print("OK")
                                    break
                    elif "ADC is on" in line:
                        print("OK")
                        break
                    elif "ADC is unknown" in line:
                        print("WARN: " + line)
                        failure = 1
        if retry_MSP_check != 4:
            failure = 1
            print("ERROR: Can't get MSP version after reset")
    except:
        print("ERROR: Failed getting MSP status")
        failure = 1

    print(strformat % "Checking Beaglelogic Kernel driver...",end=' ')
    try:
      output = subprocess.check_output("/sbin/modinfo beaglelogic", shell=True, text=True)
      for line in output.splitlines():
        if line.startswith("version:"):
          print(line.split()[1])
    except Exception as e:
      failure = 1
      print("ERROR: Failed getting Beaglelogic driver version " + str(e))

    print(strformat % "Checking for calibration data...", end=' ')
    if not failure:
      invalid_versions = [None,'','0','201','255']
      if msp_version in invalid_versions:
        print("ERROR: Invalid MSP version")
        action_code = 255
      else:
        # Try to read calibration data from MSP, if exception happens then check for backups
        return_code = mspToJson()
        if return_code == 0:
          action_code = 0
          print("OK.")
        else:
          if os.path.isfile(lastCalibrationData):
              print("WARN: Not found on MSP. Previous calibration data detected. " )
              action_code =  2
          elif os.path.isfile(calFileNameLegacy):
              print("WARN: Not found on MSP. Legacy calibration data detected. " )
              action_code =  1
          else:
              print("ERROR: Not found on MSP or disk. Scans can continue, but will be uncalibrated.")
              action_code =  3
    else:
      print("SKIPPING due to previous errors")
      action_code = 255

    #if failure != 1:
        #action_code = determineConfigAction(msp_version=msp_version)
        
    return_vars['msp_version'] = msp_version
    #return action_code, msp_version
    return action_code, return_vars

def determineConfigAction(msp_version,lastCalData=lastCalibrationData,calFileNameLegacy=calFileNameLegacy):
    invalid_versions = [None,'','0','201','255']
    latest_version = ['51']
    # CODES:
    # 0: All good
    # 1: MSP not the latest, but sensor has calibration table. Run normally.
    # 2: MSP data corrupt, but last data received from calibration exists. Reflash BSL, Rewrite last received data to MSP, restart icarus
    # 3: No calibration data
    # 255: Error code, exit
    if msp_version in invalid_versions:
        return 255
    elif msp_version not in latest_version:
        if os.path.isfile(calFileNameLegacy):
            return 1
        else:
            return 3
    else:
        try:
            print("Checking for calibration data...", end=' ')
            mspToJson()
        except Exception as e:
            if os.path.isfile(lastCalData):
                print("WARN: Not found on MSP. Previous calibration data detected. " + str(e))
                return 2
            else:
                print("ERROR: Not found on MSP or disk. Scans can continue, but will be uncalibrated.")
                return 3


def calTableJsonToMsp(jsonData=None, filename=lastCalibrationData, numBytesWriteTotal = numBytesTotal):
    # Give priority to json data provided directly as an argument. If not available, read from file location at filename
    if jsonData is None:
        # Read calibration json data from file
        #print("Loading calibration file " + filename)
        output = "Loaded from file " + filename
        with open(filename,'r') as fp:
            tableJson = json.load(fp)
    else:
        tableJson = jsonData
        output = "JSON payload provided."

    tableJsonBeforeEncode = json.dumps(tableJson)
    # Encode json as bytes
    tableJsonEncode = tableJsonBeforeEncode.encode('utf-8')
    tableJsonEncodeBytes = bytearray(tableJsonEncode)
    numDataBytes = len(tableJsonEncodeBytes)

    # Load SPI module
    #print("Loading SPI Module...\n")
    try:
        spi = SPI(1,0)
        spi.cshigh = True
        spi.lsbfirst = False
        spi.bpw = 8
        spi.mode = 0b01
        spi.threewire = False
        spi.msh = int(125000)
        #print("SPI Module loaded.\n")

        # Compute number of times required to write to MSP
        # MSP takes spi buffer 13 bytes at a time: 1 byte for control, 12 bytes for data
        totalDataWritePasses = math.ceil(numDataBytes/numBytesPerWrite)
        totalWritePasses = int(numBytesWriteTotal/numBytesPerWrite) 
        #print("Preparing to write {} calibration information ...".format(numBytesTotal))
        #print("Number of writes passes needed is {}. ".format(totalWritePasses))
        
        # Compute number of trailing bytes
        extraBytes = numDataBytes%numBytesPerWrite
        # Start SPI writing process
        for i in range(totalWritePasses):
            #print("Writing pass {} out of {}.".format(i+1,totalWritePasses))

            # If last DATA buffer, fill in the rest of buffer with zeros
            if i==totalDataWritePasses-1 and extraBytes!=0:
                tbuf = [mspWriteCtrl] + [tableJsonEncodeBytes[i*numBytesPerWrite+j] for j in range(extraBytes)] + [0x00]*(numBytesPerWrite - extraBytes)

            # If no more DATA, just write zeros
            elif i>= totalDataWritePasses:
                tbuf = [mspWriteCtrl] + [0x00]*numBytesPerWrite

            # As long as there is DATA, write DATA to buffer in 12 bytes
            else:
                tbuf = [mspWriteCtrl] + [tableJsonEncodeBytes[i*numBytesPerWrite+j] for j in range(numBytesPerWrite)]
            
            # Preview Data
            #print("Send data to MSP is: {}".format(tbuf))
            spi.xfer2(tbuf)
        print("OK, " + output)
        return 0
    except Exception as e:
        print("ERROR: Failed writing calibration data to MSP: " + str(e))
        print("\t" + output)
        return -1

def mspToJson(calTableStorePath=calFileCache, numBytesReadTotal = numBytesTotal):
    #Load SPI Module
    try:
        spi = SPI(1,0)
        spi.cshigh = True
        spi.lsbfirst = False
        spi.bpw = 8
        spi.mode = 0b01
        spi.threewire = False
        spi.msh = int(125000)
    except Exception as e:
        print("ERROR: Failed opening SPI: " + str(e))
        return 255
    # Assuming total number of bytes is a multiple of number of bytes per write
    totalReadPasses = int(numBytesReadTotal/numBytesPerWrite)
    
    # Initialize Data array
    readBytes = []

    #print("Preparing to read {} coefficients ...".format(numBytesReadTotal))
    #print("Number of read passes needed is {}.".format(totalReadPasses))
    for i in range(totalReadPasses):
        #print("Reading pass {} out of {}.".format(i+1,totalReadPasses))

        # Send read command: must be 13 bytes to retrieve 12 data bytes
        tbuf = [mspReadCtrl] + [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
        rbuf = spi.xfer2(tbuf)

        # Preview read data
        #if i < 10:
            #print(rbuf)

        # First read from MSP is blank, so ignore
        if i==0:
            continue

        # append read data into Data array
        readBytes = readBytes + rbuf[1:]
    
    # To extract only meaningful data, look for first zero index
    endInd = 0
    for i in range(len(readBytes)):
        if readBytes[i]==0:
            endInd = i
            break

    if endInd == 0:
      output = "CALIBRATION DATA IS ALL ZEROS"
      return {}, output

    # Read until first zero index, and decode json
    try:
        readTableJson = json.loads(bytearray(readBytes[:endInd]).decode('utf-8'))
    except Exception as e:
        output = "FAILED READING CALIBRATION DATA " + str(readBytes[:50]) + "\n"
        #output += "few bytes before endInd \n" + str(readBytes[endInd-5:endInd+5]) + "\n"
        #output += 'endInd: ' + str(endInd) + "\n"
        output += 'Exception: ' + str(e) + "\n"
        return {},output

    # Write Json to disk
    if calTableStorePath is not None:
        with open(calTableStorePath,'w') as fp:
            json.dump(readTableJson,fp)

    return readTableJson,""



def header(msg=''):
  buffer_spaces = 2
  max_length = 80
  length = len(msg)
  spacer = ' '
  extra = ' ' if length % 2 == 1 else ''
  if length < max_length - buffer_spaces:
    stars = int(((max_length - length - buffer_spaces)/2) )
  else:
    stars = 2
  if length == 0:
    stars = int(max_length / 2)
    extra = ''
    spacer = ''
  print("="*stars + spacer + msg + extra + spacer + "="*stars)

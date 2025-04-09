import numpy as np
import math
from definitions import *
import threading
import time
from tools import *
import os
import subprocess
from scipy import signal
import json
import mmap

#BeagleBone平台上硬件接口操作
try:
    import Adafruit_BBIO.GPIO as GPIO
    from Adafruit_BBIO.SPI import SPI
    import Adafruit_BBIO.ADC as ADC
except ImportError:
    print(bcolors.WARNING + "Module Adafruit_BBIO.GPIO not installed, this will prevent " + \
    " the MSP being used on a BeagleBone"  + bcolors.ENDC)

# Template for a receiver sensor
class Receiver(object):
    def __init__(self, capabilities={}):
        """
        Receiver parameters:
            frequency:     center frequency of sensor
            sample_rate:   sample rate of iq data
            gain:          gain of receiver
            N_samples:     number of samples to capture"""
        
        # Default values
        defaults = { 'frequency_min': 0,
                     'frequency_max': INFINITY,
                     'sample_rate_min': 0,
                     'sample_rate_max': INFINITY,
                     'gain_min': 0,
                     'gain_max': INFINITY,
                     'gain_step': 0,
                     'N_samples_min': 0,
                     'N_samples_max': INFINITY,
                     'timeout': 0.2,
                     'serial': None }
        
        # Update defaults with capabilities
        defaults.update(capabilities)

        # Set attributes
        for key, value in defaults.items():
            setattr(self, key, value)
        print("sample_rate_min:", self.sample_rate_min)
        print("sample_rate_max:", self.sample_rate_max)
        self.capabilities = defaults

        self.lock = threading.Lock()
        self.lock_timestamp = 0
        self.lock_thread_ident = 0
        self.percentComplete = None
        self.last_frequency = None
        self.last_gain = None
        # Sensor parameter bounds
 
        self.f_min = 0  # Low side of the used PSE (to trim bins with aliasing, too attenuated, etc)
        self.f_max = 24e6  # High side of the used PSE (to trim bins with aliasing, too attenuated, etc)
        # Todo: From updated periodogram slides, will probably need to be renamed due to "frequency_min" and "_max" - Chris

    ###########################################################################
    # Must override all parameter getter/setters and hardware interface methods
    ###########################################################################
    @property
    def frequency(self):
        return self._frequency
    @frequency.setter
    def frequency(self,value):
        if self.frequency_min <= value <= self.frequency_max:
            self._frequency = value
        else:
            raise ValueError('frequency must be between %f Hz and %f Hz.'
                             % (self.frequency_min,self.frequency_max))
    @property
    def sample_rate(self):
        return self._sample_rate
    @sample_rate.setter
    def sample_rate(self,value):
        if self.sample_rate_min <= value <= self.sample_rate_max:
            self._sample_rate = value
        else:
            raise ValueError('sample_rate must be between %f Hz and %f Hz.'
                             % (self.sample_rate_min,self.sample_rate_max))
    @property
    def gain(self):
        return self._gain
    @gain.setter
    def gain(self,value):
        if self.gain_min <= value <= self.gain_max:
            self._gain = value
        else:
            #raise exception
            pass
    @property
    def N_samples(self):
        return self._N_samples
    @N_samples.setter
    def N_samples(self,value):
        value = int(value)
        if self.N_samples_min <= value <= self.N_samples_max:
            self._N_samples = value
        else:
            raise ValueError('N_samples must be between %i and %i.'
                             % (self.N_samples_min,self.N_samples_max))
            
    def _collect_sensor_data():
        #return data from sensor
        pass

    def close(self):
        # close any open handles
        pass
    ###########################################################################
    
    
    
    ###########################################################################
    # Sensor functions
    ###########################################################################
    def capture(self):

        # Check for lock for self.timeout seconds, if we don't get it, bail
        # This avoids blocking forever waiting on the lock
        if self.timeout:
            lock_time = time.time()
            while self.lock.locked():
                time.sleep(1)
                cur_time = time.time()
                if (cur_time - lock_time > self.timeout):
                    if self.lock.locked():
                        s = ("%s timed out by %f seconds when attempting to acquire "+\
                        "lock for data capture") %\
                        (self.__class__.__name__, (cur_time - lock_time))
                        raise RuntimeError(s)      
                        return
                    else:
                        break

        self.lock.acquire()
        data = self._collect_sensor_data()
        self.lock.release()
        return data
    
    @property
    def ibw_max(self):
        return self.sample_rate_max
    @property
    def ibw(self):
        return self.sample_rate
    @property
    def dt(self):
        return 1.0/self.sample_rate

    def raw(self, center_frequency, gain=1):

        # Check for lock for self.timeout seconds, if we don't get it, bail
        # This avoids blocking forever waiting on the lock
        if self.timeout:
            #Check for old lock file 
            cur_time = time.time()
            if ( self.lock.locked() and self.lock_timestamp != 0 and cur_time - self.lock_timestamp > MAX_LOCKTIME ):
                print("Found stale lockfile (set " + str(cur_time - self.lock_timestamp) + " seconds ago).  Removing.")
                self.lock.release()

            while self.lock.locked():
                time.sleep(1)
                cur_time = time.time()
                if (cur_time - self.lock_timestamp > self.timeout):
                    if self.lock.locked():
                        s = ("%s timed out by %f seconds when attempting to acquire "+\
                        "lock for data capture") %\
                        (self.__class__.__name__, (cur_time - self.lock_timestamp))
                        raise RuntimeError(s)      
                        return
                    else:
                        break

        with self.lock:
            self.lock_timestamp = time.time()
            from threading import current_thread
            self.lock_thread_ident = current_thread().ident
            try:
                data = self._raw(center_frequency,gain)
            except Exception as err:
                print("**** FAILED SCAN THREAD **** " + str(err))
                data = None

        return data


    def _raw(self,center_frequency,gain):
        self.frequency = center_frequency
        self.gain = gain
        self.N_samples = int(BUFFER_SIZE)          # Here the N_smamples is the number of complex samples, and the buffer size is the number of real samples/bytes, so we need to divide by 2. This is radiohound specific, not sure how we are going to generalize this.
        return self._collect_sensor_data_raw()


    def _collect_sensor_data_raw():
        pass

    def scan(self,frequency_start,frequency_end,
             N_samples=None,rbw=None,
             ibw=None,sample_rate=None, gain=1, sensor=None, debug=0):

        # Check for lock for self.timeout seconds, if we don't get it, bail
        # This avoids blocking forever waiting on the lock
        if self.timeout:
            #Check for old lock file 
            cur_time = time.time()
            if ( self.lock.locked() and self.lock_timestamp != 0 and cur_time - self.lock_timestamp > MAX_LOCKTIME ):
                print("Found stale lockfile (set " + str(cur_time - self.lock_timestamp) + " seconds ago).  Removing.")
                self.lock.release()

            while self.lock.locked():
                time.sleep(1)
                cur_time = time.time()
                if (cur_time - self.lock_timestamp > self.timeout):
                    if self.lock.locked():
                        s = ("%s timed out by %f seconds when attempting to acquire "+\
                        "lock for data capture") %\
                        (self.__class__.__name__, (cur_time - self.lock_timestamp))
                        raise RuntimeError(s)      
                        return
                    else:
                        break

        with self.lock:
            self.lock_timestamp = time.time()
            from threading import current_thread
            self.lock_thread_ident = current_thread().ident
            data = self._scan(frequency_start,frequency_end,
                            N_samples,rbw,
                            ibw,sample_rate, gain=gain, sensor=sensor, debug=debug)


        return data
              
    def _scan(self, frequency_start, frequency_end,
              samples_per_capture=None, rbw=None,  # Must specify either N_samples or rbw
              ibw=None, sample_rate=None, gain=1, sensor=None, debug=0): # can limit ibw/sample rate as desired):
        """
        Captures a contiguous slice of spectrum between frequency_start and
        frequency_end; if the requested slice exceeds the sensor's maximum ibw
        (or specified ibw in ibw/sample_rate_max) then the sensor will
        perform multiple captures using its maximum ibw (or the maximum ibw
        specified in ibw/sample_rate_max). For frequency ranges that are not
        whole multiples of the ibw used, scan will return additional iq data
        below frequency_start and above frequency_end, equally.
        Must specify either N_samples or desired RBW.
        If frequency_start and frequency_end are supplied as arrays then the
        operation described above will take place for each frequency
        start/end pair.
        Returns iq data."""

        # check for incompatible parameter settings
        try:
            f_s_length = len(frequency_start)
        except:
            f_s_length = 0
        try:
            f_e_length = len(frequency_end)
        except:
            f_e_length = 0

        if f_s_length != f_e_length:
            raise ValueError('frequency_start and frequency_end must be the ' + \
                             'same length.')
        if samples_per_capture is None and rbw is None:
            raise ValueError('Must specify either N_samples or rbw.')
        if samples_per_capture is not None and rbw is not None:
            raise ValueError('Cannot specify both N_samples and rbw as these ' + \
                             'parameters control the same underlying hardware ' + \
                             'configuration.')
        if ibw is not None and sample_rate is not None:
            raise ValueError('Cannot specify both ibw and sample_rate ' + \
                             'as these parameters control the same underlying ' + \
                             'hardware configuration.')

        # Set gain variable
        self.gain = gain

        # In the case that the user specifies several f_start/f_end pairs,
        # recursively call this function with each pair as an argument.
        # Otherwise, proceed with the scan.
        if f_s_length != 0:
            data_all = []
            for i in range(f_s_length):
                args = {'frequency_start': frequency_start[i],
                        'frequency_end': frequency_end[i],
                        'N_samples': samples_per_capture, 'rbw': rbw,
                        'ibw': ibw, 'sample_rate': sample_rate, 'debug':debug}
                data_all.append(self._scan(**args))
            return data_all

        # determine ibw based on input parameters
        if ibw is None and sample_rate is None:
            ibw = self.ibw_max
        elif ibw is None and sample_rate is not None:
            if self.__class__.__name__ == "RadioHoundSensorV3":
                ibw = sample_rate // 2
            else:
                ibw = sample_rate
        if ibw > self.ibw_max:
            if sample_rate is None:
                raise ValueError(('Requested ibw: <%s> exceeds ' + \
                                  'system\'s capability: <%s>') % (str(ibw), str(self.ibw_max)))
            else:
                raise ValueError(('Requested sample_rate: (%s) exceeds ' + \
                                  'system\'s capability: <%s>') % (str(sample_rate),
                                                                   str(self.sample_rate)))

        # determine N_samples based on input parameters and system capability
        if samples_per_capture is None and rbw is not None:
            # This assumes an FFT where N_samples are used to compute an N_samples FFT.
            # For a periodogram, the required N_samples might be larger depending on the averaging. Better to feed N_samples directly in that case.
            samples_per_capture = ibw / rbw
        elif samples_per_capture is not None and rbw is None:
            rbw = ibw / samples_per_capture
        samples_per_capture = np.min((self.N_samples_max, samples_per_capture)) # seems duplicated with the setter of N_samples, suggest to remove this line

        print("Frequency start:", frequency_start)
        f_c = frequency_start + ((ibw // 2) - 0)  # 0 is where ubw1 will go
        # if f_c < 1e9:
        #     f_c = frequency_start - ((ibw // 2) - 0)  # 0 is where ubw2 will go
        print("ibw:", ibw)
        print("f_c:", f_c)
        f_span = frequency_end - frequency_start

        # configure sensor and capture data set(s)
        self.sample_rate = sample_rate
        self.N_samples = samples_per_capture
        self.sensor = sensor
        if f_span <= ibw:
            print("f_c:", f_c)
            self.frequency = np.float64(f_c)
            y = self._collect_sensor_data()
            print("y:", type(y))
            if isinstance(y, np.ndarray):
                print("y size:", y.shape)
            if y is None:
                raise Exception("Failed to collect sensor data.")
            else:
                f_lims = (f_c - ibw / 2.0, f_c + ibw / 2.0)
                print("f_lims:", f_lims)
                return [(f_lims, y), ]
        else:
            # generates a smallest list of center frequencies f_arr such that
            # the desired frequency range (frequency_start to frequency_end)
            # is a subset of {x: f-ibw/2 <= x <= f+ibw/2, for all f in f_arr}
            N = int(np.ceil(f_span / (1.0 * ibw)))
            f_arr = np.array([f_c + i * (ibw + rbw) for i in range(N)])
            # iterate over f_arr to capture iq that includes desired frequency
            # range
            data = []
            loops = 0
            f_arrLength = len(f_arr)
            for f_c in f_arr:
                self.frequency = np.float64(f_c)
                y = self._collect_sensor_data()
                if y is None:
                    self.percentComplete = 1
                    raise Exception("Failed to collect sensor data.")
                else:
                    f_lims = (f_c - ibw / 2.0, f_c + ibw / 2.0)
                    data.append((f_lims, y))
                    loops = loops + 1
                    self.percentComplete = float(loops) / f_arrLength
                    from threading import current_thread
                    print(("[" + str(current_thread().ident) + "] Scanning... " + str(
                        int(round(self.percentComplete * 100))) + "% complete"))
            return data

    def calcSuggestedGain(self,Pn=None):

        # calculate the suggested gain
        Pref = self._targetPower                  # Target Power 
        # print("Target power is " + str(math.log10(Pref)*10))
        alpha = 0.5                           # Adaption rate

        #print("Current gain is " + str(self.gain) +"; Current power is " + str(Pn) + " w; " + str(math.log10(Pn)*10) + " dB")

        # Calc the suggested gain
        ngain = self.gain + alpha*(math.log10(Pref) - math.log10(Pn))*10
        ngain = self.getPermissibleGain(ngain)    
        #print("Suggested gain is " + str(ngain))          
        self.suggested_gain = ngain


    ###########################################################################



class RadioHoundSensorV3(Receiver):    
    def __init__(self, capabilities={}):

        # Check the RH version
        rh_version = "3.6"
        capabilities = self.get_capabilities(rh_version)

        if not subprocess.check_call(["/bin/grep -q BeagleBoard /etc/issue"], shell=True):
            #print("Validating Configuration...")
            validate_output, validate_failure = self.validate()
            if validate_failure:
                raise Exception(" ".join(validate_failure))
        
        Receiver.__init__(self,capabilities=capabilities)
        self.f_low = 0
        self.f_high = 24e6
        

        self.capabilities.update(validate_output)


        # default values
        self._frequency = 1e9
        self._sample_rate = 48e6
        self._gain = 1  #dB
        self._buffer_size = BUFFER_SIZE
        self._N_samples = int(self._buffer_size)

        self._gainlst = np.arange(-5,41,3)                                    #  valid VGA gain: range of -5, 40 with steps of 3
        self._targetPower = 0.512**2/2.0/2.0                                  # Assume the target power is 3 dB away from the maximum power of a sin wave without saturation
        self.suggested_gain = 1
        try:
            # For Adafruit_BBIO v1.1.1 to use spidev1.0, use SPI(1,0). If using Adafruit_BBIO v1.0.3, change to SPI(0,0).
            self.spi = SPI(1,0)
            self.spi.cshigh = True
            self.spi.lsbfirst = False
            self.spi.bpw = 8
            self.spi.mode = 0b01
            self.spi.threewire = False
            self.spi.msh = int(125000)
        except:
            print(bcolors.WARNING + "SPI module initialization error, this will prevent " + \
            " the MSP communication with BeagleBone"  + bcolors.ENDC)

        # Check if the ADC driver version is as expected, i.e., containing "_RH?". If yes, set continuous flag and setattribute, open the device; otherwise, open the device for each time.

        output = subprocess.check_output("/sbin/modinfo beaglelogic", shell=True, text=True)
        
        self.continousflag = True

        subprocess.call(["echo 1 > /sys/devices/virtual/misc/beaglelogic/triggerflags"],shell=True)
        print("ADC driver: New. Open ADC device only once.")

        try:
            self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
            self.fdev = os.fdopen(self.dev)
        except OSError:
            print(bcolors.WARNING + "Device /dev/beaglelogic cannot be opened" + bcolors.ENDC)


    @property
    def gain(self):
        return self._gain
    @gain.setter
    def gain(self,value):
        self._gain = self.getPermissibleGain(value)

    def get_capabilities(self, version):
        # Get the capabilities of the RadioHound sensor
        capabilities = {}
        if version == "3.6":
            capabilities['serial'] = version
            capabilities['manufacturer'] = 'Notre Dame'
            capabilities['product'] = 'RadioHound'
            capabilities['frequency_min'] = 100e6
            capabilities['frequency_max'] = 6e9
            capabilities['gain_min'] = -5
            capabilities['gain_max'] = 40
            capabilities['gain_step'] = 3
            capabilities['gain_range'] = [-5, 40, 3]
            capabilities['sample_rate_min'] = 48e6
            capabilities['sample_rate_max'] = 48e6
            capabilities['sample_rates'] = [48e6]
            capabilities['N_samples_min'] = 1
            capabilities['N_samples_max'] = 2**22
            capabilities['timeout'] = 0.2
        return capabilities

    def validate(self):
        adc_status_cmd = "/opt/radiohound/.virtualenvs/python3.9/bin/python3.9 /opt/radiohound/scripts/ADCstatusandVersion.py"
    
        pins = {}
        pins["p8.31"] = "uart"
        pins["p8.37"] = "uart"
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
        bootloader_version, hdmi_enabled = get_bootloader_version()
        return_vars = {'bootloader_version': bootloader_version}
        error_message_list = []
    
        print(strformat % "Bootloader version:", return_vars['bootloader_version'])
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
                    error_message_list.append("ERROR: one or more pins not configured")
                else:
                    print("OK")
        except Exception as err:
            print("ERROR: Failed getting pin status" + str(err))
            error_message_list.append("ERROR: Failed getting pin status" + str(err))
            failure = 1
    
    
        print(strformat % "Checking for disabled HDMI...", end=' ')
        if hdmi_enabled:
            print("ERROR: still enabled")
            error_message_list.append("ERROR: HDMI still enabled")
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
                        error_message_list.append("ERROR: " + firmware)
                        failure = 1
            if not firmware_found:
                print("ERROR: Couldn't find firmware")
                error_message_list.append("ERROR: Couldn't find firmware")
                failure = 1
    
        except:
            print("ERROR: Failed getting PRU Firmware")
            error_message_list.append("ERROR: Failed getting PRU Firmware")
    
    
    
        try:
            print(strformat % "Resetting MSP...", end=' ')
            subprocess.check_output(["/opt/radiohound/firmware/reset"],shell=True,text=True)
            time.sleep(1)
            print("OK")
        except:
            print("ERROR: Could not reset MSP")
            error_message_list.append("ERROR: Could not reset MSP")
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
                                subprocess.check_output(["/opt/radiohound/firmware/reset"],shell=True,text=True)
                                time.sleep(10 * retry_MSP_check)
                            except:
                                pass
                            break
                        elif msp_version == "255":
                            print("ERROR: No Radiohound board detected")
                            error_message_list.append("ERROR: No Radiohound board detected")
                            failure = 1
                        else:
                            print("OK: " + msp_version)
                            return_vars['rh_hardware_attached'] = True
                            return_vars['msp_version'] = msp_version
    
                    if "ADC is " in line:
                        print(strformat % "Checking ADC state...", end=' ')
                        retry_MSP_check = 4
                        if "ADC is off" in line:
                            print("WARN: ADC is off, attempting to activate...", end=' ')
                            subprocess.check_output(["/usr/bin/python","/opt/radiohound/firmware/spi_interface/msp_spi_inter.py","900000000","1","0b0110101111111111"],text=True)
                            output = subprocess.check_output([adc_status_cmd],shell=True,text=True)
                            for line in output.splitlines():
                                if "ADC is " in line:
                                    if "ADC is off" in line or "ADC is unknown" in line:
                                        print("ERROR: " + line)
                                        error_message_list.append("ERROR: " + line)
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
                print("ERROR: Can't get MSP version after reset. Is RadioHound attached?")
                error_message_list.append("ERROR: Can't get MSP version after reset. Is RadioHound attached?")
        except:
            print("ERROR: Failed getting MSP status. Is RadioHound attached?")
            error_message_list.append("ERROR: Failed getting MSP status. Is RadioHound attached?")
            failure = 1
    
        print(strformat % "Checking Beaglelogic Kernel driver...",end=' ')
        try:
          output = subprocess.check_output("/sbin/modinfo beaglelogic", shell=True, text=True)
          for line in output.splitlines():
            if line.startswith("version:"):
              return_vars['beaglelogic_kernel_driver'] = line.split()[1]
              print(return_vars['beaglelogic_kernel_driver'])
        except Exception as e:
          failure = 1
          print("ERROR: Failed getting Beaglelogic driver version " + str(e))
          error_message_list.append("ERROR: Failed getting Beaglelogic driver version " + str(e))
    
        if not failure:
            print("SUCCESS: passed validation checks!")
          
        return return_vars, error_message_list


    def getPermissibleGain(self,value):
        idx = (np.abs(self._gainlst - value)).argmin()
        value = self._gainlst[idx].item()
        return value

    def setParameters(self,frequency=None,sample_rate=None,gain=None,N_samples=None):
        if frequency!=None:
            self.frequency = frequency
        if sample_rate!=None:
            self.sample_rate = sample_rate
        if gain!=None:
            self.gain = gain
        if N_samples!=None:
            self.N_samples = N_samples

    def _collect_sensor_data_raw(self):
        return self.captureBinaryIQ()
    
    def captureBinaryIQ(self):
        # 不再预分配 NumPy 数组，直接获取原始 ADC 字节数据
        if not (self._frequency == self.last_frequency):
            responseMSP = self.mspCommandBeagle("single", self._gain, int(self._frequency/1e3))
            print("MSP config response:", responseMSP)
            time.sleep(0.05)  # 等待硬件缓冲区稳定
        elif (self._gain != self.last_gain and self._frequency == self.last_frequency):
            responseMSP = self.mspCommandBeagle("setGain", self._gain)
            time.sleep(0.05)
        else:
            responseMSP = 0

        self.last_frequency = self._frequency
        self.last_gain = self._gain

        if responseMSP != 0:
            raise Exception("****Failed to communicate with MSP: Error code {}".format(responseMSP))
        
        # 直接获取 ADC 原始字节数据
        rawData = self.readAdcIq()
        if rawData is None:
            raise Exception("****Failed to get IQ samples: No valid ADC data received")
        else:
            return rawData
        

    def findActualGain(self):
        # VGA gain set by the digital interface
        vgaGainSet = int((self._gain+5)/3)*3 - 5
        gainActual = vgaGainSet + IFAMPGAINV3
        #print "The total gain (dB) is :", gainActual
        return gainActual


    # MSP commands to hardware
    def mspCommandBeagle(self,  mode="single", vgaGain=0, fcStart=100, fcStop=None, stepSize=None, regAddress=None, regVal=None, debugPath=None):
        # All parameters in the documentation are included as arguments to the method, but many are set to none, are parsed
        # depending on the "mode" string argument.
        # Different modes are "single", "multi", "setGain", "readPLLReg", "writePllReg", "writeCal", "readCal", "shutDown", "debug"
        # We will most likely only be using "single" and "debug"
        # vgaGain: Gain of VGA in dB. Assumed VGA is biased to achieve -5dB at lowest gain setting. Increases by 3dB per level
        # fcStart: [Start] Frequency in KHz (also used as the main frequency setting for modes that require a single frequency input)
        # fcStop: Stop Frequency in KHz
        # stepSize: Between fcStart and fcStop in KHz
        # regAddress: Address of PLL register
        # regVal: Value to be written to PLL register
        # debugPath: 0 for low-frequency path, 1 for high-frequency path

        # TODO: Impement modes other than "single", "debug", and "readPLLReg"

        try:
            self.spi
        except AttributeError:
            print("SPI has not been defined, openning SPI device...")
            try:
                # For Adafruit_BBIO v1.1.1 to use spidev1.0, use SPI(1,0). If using Adafruit_BBIO v1.0.3, change to SPI(0,0).
                self.spi = SPI(1,0)
                self.spi.cshigh = True
                self.spi.lsbfirst = False
                self.spi.bpw = 8
                self.spi.mode = 0b01
                self.spi.threewire = False
                self.spi.msh = int(125000)
            except:
                print(bcolors.WARNING + "SPI module initialization error, this will prevent " + \
                " the MSP communication with BeagleBone"  + bcolors.ENDC)
        except Exception as e:
            print("Exception: " + str(e))
            


        if mode=="single":
            ctrlByte = 0b00000001   #0x01
            fcStart1 = (fcStart >> 24) & 0b11111111
            fcStart2 = (fcStart >> 16) & 0b11111111
            fcStart3 = (fcStart >> 8) & 0b11111111
            fcStart4 = fcStart & 0b11111111
            vgaGainBin = int((vgaGain +5)/3) & 0b00001111
            fillerByte = 0b11111111

            tbuf = [ctrlByte,\
                    fcStart1,fcStart2,fcStart3,fcStart4,\
                    fillerByte,fillerByte,fillerByte,fillerByte,\
                    fillerByte,fillerByte,\
                    vgaGainBin,fillerByte]
            self.spi.xfer2(tbuf)

        elif mode=="multi":
            ctrlByte = 0b00000010   #0x02
            pass

        elif mode=="setGain":
            ctrlByte = 0b00000100   #0x04
            vgaGainBin = int((vgaGain +5)/3) & 0b00001111
            fillerByte = 0b11111111
            tbuf = [ctrlByte,\
                    fillerByte,fillerByte,fillerByte,fillerByte,\
                    fillerByte,fillerByte,fillerByte,fillerByte,\
                    fillerByte,fillerByte,\
                    vgaGainBin,fillerByte]
            self.spi.xfer2(tbuf)
        
        elif mode=="readPLLReg":
            ctrlByte = 0b00001000   #0x08
           
            # PLL requires 31 bits per instruction. 
            # For a read instruction, only require the first bit to be "1", followed by 6 bits of register address.
            # All other bits are don't cares. When sending 32 bits, PLL ignores last one.
            readRegByte = 0b10000000 | (regAddress << 1)
            fillerByte = 0b11111111

            tbuf = [ctrlByte,\
                    readRegByte,fillerByte,fillerByte,fillerByte,\
                    fillerByte,fillerByte,fillerByte,fillerByte,\
                    fillerByte,fillerByte,\
                    fillerByte,fillerByte]
            print(("Bytes sent to MSP: {}".format(tbuf)))
            self.spi.xfer2(tbuf)
            print(("Bytes received from MSP: {}".format(tbuf)))

        elif mode=="writePllReg":
            ctrlByte = 0b00010000   #0x10
            pass

        elif mode=="writeCal":
            ctrlByte = 0b00100000   #0x20
            pass

        elif mode=="readCal":
            ctrlByte = 0b01000000   #0x40
            pass

        elif mode=="shutDown":
            ctrlByte = 0b10000000   #0x80
            pass

        elif mode=="debug":
            ctrlByte = 0b10000010   #0x82
            fcStart1 = (fcStart >> 24) & 0b11111111
            fcStart2 = (fcStart >> 16) & 0b11111111
            fcStart3 = (fcStart >> 8) & 0b11111111
            fcStart4 = fcStart & 0b11111111
            vgaGainBin = int((vgaGain +5)/3) & 0b00001111
            fillerByte = 0b11111111
            
            if debugPath==0:
                devCtrl1 = 0b11010111
                devCrtl2 = 0b11111111
            
            elif debugPath==1:
                devCtrl1 = 0b10111000
                devCtrl2 = 0b00111111

            else:
                print(("Error, Invalid downconversion path. Expecting 0 or 1, instead received {}".format(debugPath)))
                self.spi.close()
                return 2

            tbuf = [ctrlByte,\
                    fcStart1,fcStart2,fcStart3,fcStart4,\
                    devCtrl1,devCtrl2,\
                    fillerByte,fillerByte,fillerByte,fillerByte,\
                    vgaGainBin,fillerByte]
            self.spi.xfer2(tbuf)

        else:
            #print("Error: Mode Not Supported. Specified mode was "+mode)
            return 1
        return 0

    # def readAdcIq(self):
    #     if self.continousflag:
    #         if self.fdev.closed:
    #             print("dev is closed, reopening...")
    #             self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
    #             self.fdev = os.fdopen(self.dev)
    #     else:
    #         self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
    #         self.fdev = os.fdopen(self.dev)
        
    #     try:
    #         iqBytes = os.read(self.dev, self._N_samples)
    #         print("Raw ADC data sample:", iqBytes[:16])
            
    #         if sum(iqBytes) == 0:
    #             self.fdev.close()
    #             return None  
    #         else:
    #             if not self.continousflag:
    #                 self.fdev.close()
    #             return iqBytes
    #     except Exception as e:
    #         self.fdev.close()
    #         return None
    def get_current_buffer_index(self):
        try:
            with open("/sys/class/misc/beaglelogic/state", "r") as f:
                state_str = f.read().strip()
            return int(state_str)
        except Exception as e:
            print("无法读取状态, 默认使用索引 0:", e)
            return 0
    
    # def readAdcIq(self):
    #     if self.continousflag and not hasattr(self, "dev"):
    #         print("Opening device for continuous mode...")
    #         self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
    #     elif not self.continousflag:
    #         self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
        
    #     try:
    #         iqBytes = os.read(self.dev, 1048576)  # 1MB 一次性读取
    #         print("Raw ADC data sample:", iqBytes[:16])
            
    #         if sum(iqBytes) == 0:
    #             if not self.continousflag:
    #                 os.close(self.dev)
    #             return None  
    #         else:
    #             if not self.continousflag:
    #                 os.close(self.dev)
    #             return iqBytes
    #     except Exception as e:
    #         if not self.continousflag:
    #             os.close(self.dev)
    #         return None
    def readAdcIq(self):
    """
    使用持续模式下的持久映射和环形缓冲区按块读取数据
    读取一个当前就绪的2MB数据块（基于当前 buffer index）
    """
    # 在连续模式下，如果还没有持久映射，则创建一次映射
        if self.continousflag:
            if not hasattr(self, "mmap_region"):
                print("Mapping entire 128MB buffer for continuous mode...")
                self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
                self.mmap_region = mmap.mmap(self.dev, BUFFER_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
        else:
            # 非连续模式，每次调用后都重新映射
            self.dev = os.open("/dev/beaglelogic", os.O_RDONLY)
            self.mmap_region = mmap.mmap(self.dev, BUFFER_SIZE, mmap.MAP_SHARED, mmap.PROT_READ)
    
        try:
            # 获取当前就绪的缓冲区索引（0～TOT_BLOCKS-1）
            current_index = get_current_buffer_index()
            # 根据环形缓冲区计算偏移（取模保证环绕）
            offset = (current_index % TOT_BLOCKS) * BUF_UNIT_SIZE
    
            # 定位到计算出的偏移
            self.mmap_region.seek(offset)
            # 读取一个完整的2MB数据块
            block_data = self.mmap_region.read(BUF_UNIT_SIZE)
            print("Raw ADC data sample (前16字节):", block_data[:16])
    
            # 简单检查：如果数据全为 0，则认为未写入或无效（可根据需要扩展）
            if sum(bytearray(block_data)) == 0:
                return None
            else:
                return block_data

    except Exception as e:
        print("读取数据时发生异常:", e)
        return None


    def close(self):
        print("Closing ADC...")
        self.fdev.close()



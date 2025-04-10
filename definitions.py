# Now defined dynamically in core.py to the git tag
#SOFTWARE_VERSION = '0.9.4.1'
LOCAL_CONFIG_FILE = 'system.json'
LOCAL_CONFIG_FILE_TEMPLATE = 'system.json.template'
OFFLINE_STORE_FILE = 'offline_data'
OFFLINE_STORE_FILE_RECOVERABLE = 'TIME_UNKNOWN_DATA'
OFFLINE_STORE_FILE_UNRECOVERABLE = 'TIME_UNKNOWN_UNRECOVERABLE'
DISABLE_BACKGROUND_JOB_FILE = "DISABLE_BACKGROUND_JOBS"

# TOPIC DEFINITIONS
# note that we add the mac address to the end of these topics
ANNOUNCE_TOPIC_BASE = 'radiohound/clients/announce/'
DATA_TOPIC_BASE = 'radiohound/clients/data/'
CMD_TOPIC_BASE = 'radiohound/clients/command/'
FEEDBACK_TOPIC_BASE = 'radiohound/clients/feedback/'
DEFAULT_DEBUG_TOPIC = 'icarus/debug'
ANSIBLE_TIMESTAMP = '/opt/icarus/ansible_timestamp'

# Heartbeat periodicity
FAST_HEARTBEAT_RATE = 1 # seconds
HEARTBEAT_RATE = 10 # seconds
UPDATECONFIG_RATE = 60 # seconds
NETWORK_CHECK_INTERVAL = 20 # seconds
MAX_LOCKTIME = 300 # seconds
MAX_SCAN_ITERATIONS = 10000 # increase count so we don't restart until I can review this code better (time per loop_start iteration * MAX_LOCKTIME)
TIME_CHECK_INTERVAL = 300 # seconds

# Onboard Beagle LEDs
LED_ICARUS_RUNNING = 3
LED_MQTT_CONNECTED = 2
LED_WIFI_CONNECTED = 1 # Actually set from external script
LED_RECEIVER_LOCKED = 0

# GPS parameters
GPS_TOLERANCE = 10 # meters
# default return values if no fix
DEFAULT_LAT = 41.714282
DEFAULT_LON = -86.241805
DEFAULT_ALT = 199.9
# MQTT Key Names
key_task_name = 'task_name'
key_arguments = 'arguments'
key_message = 'message'
key_payload = 'payload'
key_data = 'data'
key_type = 'type'
key_topic = 'topic'
key_thread = 'thread'
key_running_tasks = 'running_tasks'
key_result = 'result'
key_from_topic = 'from_topic'
key_interval = 'updateInterval'
max_interval_time = 10
key_config_version = 'config_version'


key_mac_address = 'mac_address'
key_broker_name = 'broker_name'
key_initial_topics = 'initial_topics'
key_sensor_types = 'sensor_types'
key_sensor_hardware_ids = 'sensor_hardware_ids'
key_sample_rate = 'sample_rate'
key_longitude = 'longitude'
key_latitude = 'latitude'
key_altitude = 'altitude'
key_center_frequency = 'center_frequency'
key_job_id = 'job_id'
key_percent_complete = '%_complete'
key_disable_jobs = 'disable_background_jobs'
key_validate_code = 'validate_code'
key_msp_version = 'msp_version'

# Key names for jobs
key_job_type = 'job_type'
key_job_name = 'name'
key_job_task = 'task'
key_job_start_time = 'start_time'
key_job_stop_time = 'stop_time'
key_job_interval = 'interval'
key_job_args = 'arguments'
key_job_running = 'running'
key_job_tag_all = 'All'
key_job_active_flag = 'active'

key_additional_info = 'additional_info'

# Memory key names for heatmap
key_do_heatmap = 'do_heatmap' # flag to generate heatmap
key_nodes = 'nodes'
key_pgrm = '_pgrm'
key_pow = '_pow'
key_triple = '_triple'
key_node_data_topic = 'node_data_topic'
key_output_topic = 'output_topic'
key_browser_guid = 'browser_guid'
key_freq_min = 'freqMin'
key_freq_max = 'freqMax'
key_lat_min = 'lat_min'
key_lat_max = 'lat_max'
key_lon_min = 'lon_min'
key_lon_max = 'lon_max'
key_m = 'm'
key_n = 'n'
message_heatmap = 'HEATMAP'
key_len_values = 'lenValues'
key_my_min = 'myMin'
key_my_max = 'myMax'
key_values = 'values'
key_metadata = 'metadata'
key_nfft = 'nfft'
key_bearings = 'bearings'


# heatmap parameters
epsilon = .1 # wait time in seconds
NODATA = -100
SUBFLOOR = -10
defaultNumOnShortSide = 100

# default values for periodogram
defaultNfft = 1024
defaultWindow = 'hanning'

# CALIBRATION
# File for caching calibration data on local disk from MSP.
calFileCache = '/opt/icarus/icarus/calibrationIO/calDataCache.json'
# This is the most recent calibration data received from server. Can be used as failsafe if MSP is erased.
lastCalibrationData = '/opt/icarus/icarus/calibrationIO/lastCalibrationData.json'
calFileNameLegacy = '/opt/icarus/caltable.txt'
MINGAIN = 13.5 # minimum gain setting on RadioHound (dB)
calTableMaxFreq = 5980 # MHz, maximum frequency considered in calibration table
calTableMinFreq = 100 # MHz, minimum frequency considered in calibration table
IFAMPGAINV3 = 20 # V3 fixed IF amp gain
RH_HW_CONNECTED_GPIO_PIN = 6


# Threshold for high/low path selection Rev3.1
THRESHOLD_FREQ = 1E9

# How many of each command from an individual browser can be queued at a time
# Additional messages will be skipped to prevent short-interval jobs from monopolizing queue
max_sub_message_queued = 5

# How many of each background job can be queued at a time
# Additional jobs will be skipped to prevent short-interval jobs from monopolizing queue
max_sub_job_queued = 2


# printing format
strformat = '%-37s'

# Buffer size from the beaglelogic driver, which is then generalized for the number of raw captures
# BUFFER_SIZE = 1024 * 1024
# This is used for default sample_rate_max, gain_max, and frequency_max,
# which should be python float('inf'), but that causes issues with server capabilities display,
# so we use this instead.
INFINITY = 1e15

BUFFER_SIZE = 1024*1024  
BUF_UNIT_SIZE = 1048576
TOT_BLOCKS = BUFFER_SIZE // BUF_UNIT_SIZE
BLOCK_SIZE = 1024 * 1024 

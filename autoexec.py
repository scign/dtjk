###############################################################################
#
# this file must be saved as
# /home/osmc/.kodi/userdata/autoexec.py
#
# requires twilio
#

###############################################################################
# Import necessary libraries
from os import stat,listdir,path
from glob import glob
from hashlib import md5
from logging import basicConfig,getLogger,info,warning,exception,INFO
from subprocess import Popen,check_output,CalledProcessError
from shutil import rmtree,copytree,copyfile
from time import sleep,strftime
from xbmc import executebuiltin
from twilio.rest import Client
from urllib2 import urlopen,URLError
from uuid import getnode as get_mac
from socket import socket,AF_INET,SOCK_DGRAM,error as SocketError


###############################################################################
# Define strings

# where to store log messages
log_path = '/home/osmc/.kodi/temp/'
log_filename = 'dj-autoexec.log'
log_file = log_path + log_filename

# URL to check internet connection
test_url = "http://dwjk.byethost8.com"

# where to download updated slides to
local_path = '/home/osmc/'
local_folder = local_path + 'Pictures/'
movie_playlist_file = local_folder + '/movie.m3u'
dev_test = local_path + 'dev'

# folder where the remote site is mounted to
remote_path = '/mnt/djinfo-ftp/'

# remote folders where the slides are located
remote_folder = remote_path + 'htdocs/djinfo/'
log_remote = 'htdocs/logs'

# Twilio account details (for text messages)
account_sid = ''  # replace with account_sid
auth_token = ''  # replace with auth_token
from_number = ''  # replace with twilio number
to_number = ''  # replace with recipient number
the_message = ''


def is_dev():
    return not is_prod

def is_prod():
    return glob(dev_test) == []


###############################################################################
# Function to wait for an internet connection
def waitForInternet():
    while True:
        try: return urlopen(test_url) is not None
        except URLError: sleep(5)


###############################################################################
# Function to check whether we're mounted
def waitForMount():
    waitForInternet()
    while True:
        try: return listdir(remote_folder) is not None
        except OSError:
            try: pMount = Popen('sudo mount -a', shell=True)
            except CalledProcessError: pass
            sleep(5)


###############################################################################
# Function to calculate md5
def getmd5(directory):
    hash_md5 = md5()
    for fname in sorted(listdir(directory)):
        fstat = stat(directory + fname)
        hash_md5.update(fname + str(fstat.st_size) + str(fstat.st_mtime))
    return hash_md5.hexdigest()


###############################################################################
# Function to send text message
def send_text( msg_text ):
    # send a text using Twilio
    if is_prod():
        message = client.messages.create(to=to_number, from_=from_number, body=msg_text)
    else:
        pilog.info('Dev: Not sending message: ' + msg_text)


###############################################################################
# Subroutine to start the slideshow
def start_media():
    movies = glob(movie_playlist_file)
    if len(movies) == 0:
        executebuiltin('XBMC.SlideShow(' + local_folder + ')')
        return 'Playing slideshow'
    else:
        executebuiltin('PlayerControl(RepeatAll)')
        executebuiltin('XBMC.PlayMedia(' + movie_playlist_file + ')')
        return 'Playing movie'


###############################################################################
# Start autoexec process
#
pi_id = ("%012X" % get_mac())[6:12]
# set up logging
LOGFORMAT = '%(asctime)s %(name)s %(levelname)-8s %(message)s'
TIMEFORMAT = '%Y-%m-%d %H:%M:%S'
basicConfig(filename=log_file, level=INFO, format=LOGFORMAT, datefmt=TIMEFORMAT)
pilog = getLogger('raspi-' + pi_id)
pilog.info('Logging started')

# start the slideshow
md5hash = getmd5(local_folder)
playing_now = start_media()
pilog.info(playing_now)

mounted = waitForMount()
try:
    copyfile(remote_path + 'htdocs/sys/dj-autoexec.py', local_path + '.kodi/userdata/autoexec.py')
    pilog.info('dj-autoexec.py copied')
except IOError:
    pilog.info('dj-autoexec.py not copied')

log_dst = remote_path + log_remote + strftime("/%Y-%m-%d_") + pi_id + '-' + log_filename
mounted = waitForMount()

try:
    pilog.info('Logs copied')
except IOError:
    pilog.info('Logs not copied')

# get the public IP address (internet-facing)  --  https://stackoverflow.com/a/22075729
sIP = check_output('dig +short myip.opendns.com @resolver1.opendns.com', shell=True).strip()
if len(sIP) == 0: sIP = 'not available'
# get the local IP address  --  https://stackoverflow.com/a/166589
s = socket(AF_INET, SOCK_DGRAM)
sIPlocal = ''
try:
    s.connect(("8.8.8.8", 80))
    sIPlocal = s.getsockname()[0]
    pilog.info('Local address detected: ' + sIPlocal)
except SocketError:
    pilog.info('Local address retrieval failed')
s.close()

# start the Twilio client
client = Client(account_sid, auth_token)

the_message = 'DJ-info pi ' + pi_id + ' online // '
the_message = the_message + ('Mount succeeded' if mounted else 'Mount failed') + ' // '
the_message = the_message + playing_now + ' // '
the_message = the_message + 'Public: ' + sIP + ' // '
the_message = the_message + 'Local: ' + sIPlocal
send_text(the_message)

# every 30 seconds check for changes
while True:
    mounted = waitForMount()
    if getmd5(local_folder) != md5hash:
        # found changes - restart the slideshow and reset the hash
        playing_now = start_media()
        pilog.info(playing_now)
        md5hash = getmd5(local_folder)
    sleep(30)

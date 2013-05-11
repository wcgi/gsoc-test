import socket
import logging
import optparse
import io
import sys
import time
import os
import struct
import hashlib

logger = logging.getLogger('client')
logging.basicConfig(level=0)

#the message opcode 
OP_SEND = 0 #send file
OP_RECV = 1 #receive file

# the max size of signle file
BUFSIZE = 40960


#prase the options 
def opts():
    usage="%prog --host host -p port <action> [<filepath>]"
    parser = optparse.OptionParser(usage=usage)
    parser.add_option("--host",
        action="store", dest='host', nargs=1, type='string',
        help="server host")
    parser.add_option("-p", "--port",
        action="store", dest='port', nargs=1, type='int',
        help="server port")
    options, args = parser.parse_args()
    if len(args)<1:
        parser.error('You need to give "send" or "receive" as <action>.')
    action = args[0]
    filepath = None
    if action == 'send':
        filepath = args[1]
    return options, action, filepath

def main(opts, action, filepath=None):
    try:
        client = Client(opts.host, opts.port)
    except ClientException, e:
        logger.error("ClientException Error:{0}".format(e))
        return 1
    if action == 'send':
        client.sendfile(filepath)
    if action == 'receive':
        client.receivefile()
    logger.info("connection closed")
    client.close()

class ClientException(Exception):
    pass

class Client(object):
    def __init__(self, host, port,reconnect=True):
        self.host=host
        self.port=port
        self.connect_state = False

        self.connect();

    def connect(self):
        logger.info('connecting to {0}:{1}'.format(self.host, self.port))
        self.socket_handle = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket_handle.settimeout(3)
        try: 
            self.socket_handle.connect((self.host, self.port))
        except: 
            raise ClientException('Fail to connect to the server')
        self.connect_state = True
        logger.info("Client established")
        self.socket_handle.settimeout(None)
        self.socket_handle.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

    #receive the data and store it ,name the file after its md5
    def receivefile(self):
        #send a subscribe message to the server 
        fileheader = struct.pack('!iB', 5, OP_RECV)
        ml, opcode = struct.unpack('!iB', buffer(fileheader,0,5))
        self.socket_handle.send(fileheader)

        #recieve data
        while self.connect_state:
            filedata=self.socket_handle.recv(BUFSIZE)
            if not filedata:
                self.connect_state = False
                break                
            filehandle = open(hashlib.md5(filedata).hexdigest(), 'wb')
            filehandle.write(filedata)
            filehandle.close()
    #send file data
    def  sendfile(self,filepath):
        #the max size of filedata is BUFSIZE ,if a file is larger than BUFSIZE,
        #  it will only send  first BUFSIZE bytes.
        filehandle = open(filepath, 'rb')
        fsize = os.stat(filepath).st_size
        if fsize > BUFSIZE:
            fsize = BUFSIZE
        fileheader = struct.pack('!iB', 5+fsize, OP_SEND)
        filedata = filehandle.read(BUFSIZE)
        self.socket_handle.send(fileheader+filedata)
        filehandle.close()

    def close(self):
        try: 
            self.socket_handle.close()
            self.connect_state = False
        except: 
            logger.warn('ClientException while closing socket')

if __name__ == '__main__':
    options, action, filepath = opts()
    try:
        sys.exit(main(options, action, filepath=filepath))
    except KeyboardInterrupt:
        sys.exit(0)

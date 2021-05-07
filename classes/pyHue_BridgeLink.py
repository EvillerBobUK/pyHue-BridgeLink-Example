"""pyHue_BridgeLink v 0.2
 
BridgeLink is a class to handle connections with the Philips Hue 
Bridge (version2).

It provides the four connections for the standard Hue API:
->HTTPS GET, PUT, POST, DELETE 
(though currently only GET and PUT are implemented)

It provides the connection for the Hue Entertainment API:
->streaming over UDB using DTLS/PSK (using python-mbedtls)

If the details of a bridge are stored in the config.json file,
BridgeLink can be passed the (user defined) name of the bridge
and it will configure itself from the config file.

 There is a certificate issue with the standard Hue API that hasn't been resolved.
 The current (insecure) workaround is to pass 'verify=False' to the request.

 An instance of BridgeLink can be created for each bridge being used. Although this
 remains untested (as I only have 1 hub), multiple bridges should be accessible at
 the same time. The BridgeManager class has been created to allow lights from
 multiple bridges to be accessible as one single group of lights.

 The mbedtls module used is from python-mbedtls which will also require mbedtls.
 Both of these are on github but may require a bit of fiddling to install.
 https://github.com/Synss/python-mbedtls
 https://github.com/ARMmbed/mbedtls
"""
from time import sleep, time
import requests                                         
import json                                             
import struct                                           
from socket import socket, AF_INET, SOCK_DGRAM, timeout 
from mbedtls import tls, exceptions                     

# The certificate issue throws up warnings that can be suppressed by uncommenting
# the following two lines. It doesn't fix the issue, just stops it complaining!
#import urllib3                                         
#urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class pyHue_BridgeLink:
    def __init__(self, bridgename=False,config=False):
        """Initialises and creates class

        If just passed a bridgename, the class will look in the
        default config.json for a matching bridgename entry.

        If passed a bridgename and string, the class will treat the
        string as the name of an alternate config file and will
        attempt to open it and look for a matching bridgename entry.

        If passed a bridgename and dictionary, the class will
        configure itself using the bridgename and the data in the
        dictionary provided.

        Parameters
        ----------
        bridgename : str
            The user-defined name of the bridge to connect
        configarray : str, dict, optional
            If present, bridge will be configured using these details:
            -if passed a str, it will use that as the config file name
            -if passed a dict, it will use that as the config data
        """
        self.configfile = "bridgeconfig.json"
        self.bridgename = None
        self.bridgeid = None
        self.ip = None
        self.clientname = None
        self.clientid = None
        self.clientkey = None
        self.entertainmentgroup = None
        self.url = None       
        if not bridgename == False:
            if config == False:
                self.create_from_configfile(bridgename)
            else:
                if type(config) is str:
                    self.configfile = config
                    self.create_from_configfile(bridgename)
                else:
                    self.create_from_array(bridgename, config)
        self.broadcast = None
        self.statequeue = []
        self.sock = None
        self.dtls_cli_ctx = tls.ClientContext(tls.DTLSConfiguration(
            pre_shared_key=(self.clientname, bytes.fromhex(self.clientkey)),
            ciphers=['TLS-PSK-WITH-AES-256-GCM-SHA384']
        ))
        # Uncomment the following two lines for additional debug information
        # when using the Entertainment feature.
        tls._set_debug_level(2)
        tls._enable_debug_output(self.dtls_cli_ctx.configuration)        

    def create_from_configfile(self, bridgename):
        try:
            with open(self.configfile) as json_data_file:
                data = json.load(json_data_file)
                self.create_from_array(bridgename, data[bridgename])
        except KeyError:
            raise Exception("--ERROR: create_from_configfile: KeyError, check config details match")
        except:
            raise Exception("--ERROR: create_from_configfile: Unable to get configuration data, check file exists")


    def create_from_array(self, bridgename, config):
        try:
            self.bridgename = bridgename
            self.bridgeid = config['bridgeid']
            self.ip = config['ip']
            self.clientname = config['clientname']
            self.clientid = config['clientid']
            self.clientkey = config['clientkey']
            self.entertainmentgroup = config['entertainmentgroup']
            if self.ip and self.clientname:
                self.url = 'https://' + self.ip + '/api/' + self.clientid + '/'
        except:
            print("--WARN: create_from_array: Some or all config details may be missing")
    
    def print_config(self):
        print(f"Bridge Name: {self.bridgename}")
        print(f"Bridge ID  : {self.bridgeid}")
        print(f"Bridge IP  : {self.ip}")
        print(f"Client Name: {self.clientame}")
        print(f"Client ID  : {self.clientid}")
        print(f"Client Key : {self.clientkey}")
        print(f"Ent Group  : {self.entertainmentgroup}")  
        print(f"Bridge URL : {self.url}")    


    # CORE STANDARD API ROUTINES #

    def get(self,url,request,sslverify=False):
        return requests.get(f"{url}{request}", verify=sslverify).json()

    def put(self,url,request,payload,sslverify=False):
        return requests.put(f"{url}{request}", json=payload, verify=sslverify).json()  

    def post(self,url,request,payload,sslverify=False):
        return False        

    def delete(self,url,request,payload,sslverify=False):
        return False 

    # CORE ENTERTAINMENT API ROUTINES #

    def enable_streaming(self):
        payload = {"stream": {"active": True}}
        r = self.put(self.url,'groups/' + self.entertainmentgroup,payload)[0]
        if "success" in r:
            s = socket(AF_INET, SOCK_DGRAM)
            try:
                self.sock = self.dtls_cli_ctx.wrap_socket(s, None)
                self.sock.connect((self.ip, 2100))
                self.sock.do_handshake()
            except exceptions.TLSError as e:
                print(f"###########+#{str(e)}#+#############")
        else:
            print('Failed to enable streaming')
            print(r)

    def disable_streaming(self):
        if self.sock:
            self.sock.close()
        payload = {"stream": {"active": False}}
        r = self.put(self.url,'groups/' + self.entertainmentgroup,payload)[0]
        if not "success" in r:
            print('Failed to disable streaming')
            print(r) 

    def prepare_broadcast(self, states, colourspace='RGB'): #colourmode = 'RGB' or 'XYB'
        if colourspace == 'XYB':
            cs = 0x01
            datatypes = ">BHeee"
        else:
            cs = 0x00
            datatypes = ">BHHHH"
        count = len(states)
        self.broadcast = bytearray([0]*(16+count*9))
        struct.pack_into(">9s2BB2BBB", self.broadcast, 0,
                         "HueStream".encode('ascii'),   # Protocol Name (fixed)
                         0x01, 0x00,                    # Version (=01.00)
                         0x00,                          # Sequence ID (ignored)
                         0x00, 0x00,                    # Reserved (zeros)
                         cs,                            # Color Space (RGB=0x00, XYB=0x01)
                         0x00                           # Reserved (zero)
                         )
        for i in range(count):  # Step through each set of instructions in "states"
            if colourspace == 'XYB':
                struct.pack_into(datatypes, self.broadcast, 16 + i*9,
                        0x00,                           # Type: Light
                        states[i][0],                   # Light ID
                        states[i][1],                   # Red/X
                        states[i][2],                   # Blue/Y
                        states[i][3]                    # Green/Brightness
                    )

    def add_to_queue(self, state):
        for index, x in enumerate(self.statequeue):
            if state[0] == x[0]:
                self.statequeue[index] = state
                return
        self.statequeue.append(state)

    def send_queue(self, colourspace='RGB'): #colourmode = 'RGB' or 'XYB'
        self.prepare_and_send_broadcast(self.statequeue, colourspace)
        self.statequeue.clear()

    def send_broadcast(self):
        if self.sock:
            self.sock.send(self.broadcast)         

    def prepare_and_send_broadcast(self, states, colourspace='RGB'):
        self.prepare_broadcast(states, colourspace)
        self.send_broadcast()


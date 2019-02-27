import socketserver
import time
import os
from os.path import isfile, join, abspath, exists
from pathlib import Path

filesystem_dir = "/Volumes/DATA/Projects/miniprint/filesystem"
log_location = Path("./miniprint.log")

def get_parameters(command):
    request_parameters = {}
    for item in command.split(" "):
        if ("=" in item):
            request_parameters[item.split("=")[0]] = item.split("=")[1]

    return request_parameters


def command_fsdirlist(self, request):
    delimiter = request[1].encode('UTF-8')
    request_parameters = get_parameters(request[0])
    print("[Receive] FSDIRLIST : " + request_parameters["NAME"])

    requested_dir = request_parameters["NAME"].replace('"', '').split(":")[1]
    print("Requested dir: '" + requested_dir + "'")
    resolved_dir = abspath(filesystem_dir + requested_dir)
    print("resolved_dir: " + resolved_dir)
    if resolved_dir[0:len(filesystem_dir)] != filesystem_dir:
        print("[Attack] Path traversal attack attempted! Directory requested: " + str(resolved_dir))
        resolved_dir = filesystem_dir

    return_entries = ""
    for entry in os.listdir(resolved_dir):
        if isfile(join(resolved_dir, entry)):
            return_entries += "\r\n" + entry + " TYPE=FILE SIZE=0"  # TODO do size check
        else:
            return_entries += "\r\n" + entry + " TYPE=DIR"

    response=b'@PJL FSDIRLIST NAME="0:/" ENTRY=1\r\n. TYPE=DIR\r\n.. TYPE=DIR' + return_entries.encode('UTF-8') + delimiter
    print("[Response] " + str(return_entries.encode('UTF-8')))
    self.request.sendall(response)
    

def command_fsquery(self, request):
    delimiter = request[1].encode('UTF-8')
    request_parameters = get_parameters(request[0])
    print("[Receive] FSQUERY : " + request_parameters["NAME"])

    requested_item = request_parameters["NAME"].replace('"', '').split(":")[1]
    print("Requested item: " + requested_item)
    resolved_item = abspath(filesystem_dir + requested_item)
    print("Resolved item: " + resolved_item)
    if resolved_item[0:len(filesystem_dir)] != filesystem_dir:
        print("[Attack] Path traversal attack attempted! Directory requested: " + str(resolved_item))
        resolved_item = filesystem_dir

    return_data = ''
    if exists(resolved_item):
        if isfile(resolved_item): # TODO: Get files to work and return "no" when item doesn't exist
            pass
        else:
            return_data = "NAME=" + request_parameters["NAME"] + " TYPE=DIR"

    response=b'@PJL FSQUERY ' + return_data.encode('UTF-8') + delimiter
    print("[Response] " + str(return_data.encode('UTF-8')))
    self.request.sendall(response)


def command_ustatusoff(self, request):
    print("[Interpret] User wants status request. Sending empty ACK")
    print("[Response] (empty ACK)")
    # conn.send(b'')
    self.request.sendall(b'')




class MyTCPHandler(socketserver.BaseRequestHandler):
    """
    The request handler class for our server.

    It is instantiated once per connection to the server, and must
    override the handle() method to implement communication to the
    client.
    """

    def handle(self):
        # self.request is the TCP socket connected to the client
        print("Connection from: " + self.client_address[0])
        print(self)

        emptyRequest = False
        while emptyRequest == False: # Keep listening for requests from this client until they send us nothing
            self.data = self.request.recv(1024).strip()
            dataArray = self.data.decode('UTF-8').split('\r\n')

            dataArray[0] = dataArray[0].replace('\x1b%-12345X', '')
            print('[Receive-Raw] ' + str(dataArray))

            if dataArray[0] == '':
                emptyRequest = True
                break

            try:
                if (dataArray[0] == "@PJL USTATUSOFF"):
                    command_ustatusoff(self, dataArray)
                elif (dataArray[0] == "@PJL INFO ID"):
                    print("[Interpret] User wants ID")
                    response = b'@PJL INFO ID\r\n"hp LaserJet 4200"\r\n\x1b'+dataArray[1].encode('UTF-8')
                    print("[Response]  " + str(response))
                    self.request.sendall(response)
                elif (dataArray[0] == "@PJL INFO STATUS"):
                    print("[Interpret] User wants info-status")
                    response = b'@PJL INFO STATUS\r\nCODE=10001\r\nDISPLAY="Ready"\r\nONLINE=TRUE'+dataArray[1].encode('UTF-8')
                    print("[Response] " + str(response))
                    self.request.sendall(response)
                elif (dataArray[0][0:14] == "@PJL FSDIRLIST"):
                    command_fsdirlist(self, dataArray)
                elif (dataArray[0][0:12] == "@PJL FSQUERY"):
                    command_fsquery(self, dataArray)
                else:
                    print("Unknown command: " + str(dataArray))
                    # print(dataArray)
                    # conn.send(b'')
                    # conn.close()
                    # break
            except Exception as e:
                print("Caught error: ", str(e))

        print("Connection closed from: " + self.client_address[0])

if __name__ == "__main__":
    HOST, PORT = "localhost", 9100

    # Create the server, binding to localhost on port 9999
    with socketserver.TCPServer((HOST, PORT), MyTCPHandler) as server:
        # Activate the server; this will keep running until you
        # interrupt the program with Ctrl-C
        server.allow_reuse_address = True
        server.serve_forever()

# coding=utf-8
import argparse
import json
import sys
from threading import Lock, Thread
import time
import traceback
import bottle
from bottle import Bottle, request, template, run, static_file
import requests
# ------------------------------------------------------------------------------------------------------


class Blackboard():

    def __init__(self):
        self.content = ""
        self.lock = Lock()  # use lock when you modify the content

    def get_content(self):
        with self.lock:
            cnt = self.content
        return cnt

    def set_content(self, new_content):
        with self.lock:
            self.content = new_content
        return


# ------------------------------------------------------------------------------------------------------
class Server(Bottle):

    def __init__(self, ID, IP, servers_list):
        super(Server, self).__init__()
        self.blackboard = Blackboard()
        self.id = int(ID)
        self.ip = str(IP)
        self.servers_list = servers_list
        # list all REST URIs
        # if you add new URIs to the server, you need to add them here
        self.route('/', callback=self.index)
        self.get('/board', callback=self.get_board)
        self.post('/board', callback=self.post_index)
        self.post('/board_post', callback=self.post_boardEntry_all_board)
        self.post('/board_modify_all',
                  callback=self.modify_boardEntry_all_board)

        # self.post('/board', callback=self.post_index)
        # we give access to the templates elements
        self.get('/templates/<filename:path>', callback=self.get_template)
        # You can have variables in the URI, here's an example
        # self.post('/board/<element_id:int>/', callback=self.post_board) # where post_board takes an argument (integer) called element_id

        self.post('/board/<element_id:int>/', callback=self.modifyEntry)

    def modify_boardEntry_all_board(self):
        try:r
            data = {}
            data['status_code'] = 200
            return json.dumps(data)
        except Exception as ex:
            print("[ERROR]" + str(e))
            data = {}
            data['status_code'] = 400
            return json.dumps(data)

    def post_boardEntry_all_board(self):
        try:
            entry = request.forms.get('data')
            print(entry)
            if self.blackboard.get_content() == '':
                self.blackboard.set_content(entry)
            else:
                self.blackboard.set_content(
                    self.blackboard.get_content()+','+entry)
                data = {}
                data['status_code'] = 200
                return json.dumps(data)
        except Exception as e:
            print("[ERROR] "+str(e))
            data = {}
            data['status_code'] = 400
            return json.dumps(data)

    def do_parallel_task(self, method, args=None):
        # create a thread running a new task
        # Usage example: self.do_parallel_task(self.contact_another_server, args=("10.1.0.2", "/index", "POST", params_dict))
        # this would start a thread sending a post request to server 10.1.0.2 with URI /index and with params params_dict
        thread = Thread(target=method,
                        args=args)
        thread.daemon = True
        thread.start()

    def do_parallel_task_after_delay(self, delay, method, args=None):
        # create a thread, and run a task after a specified delay
        # Usage example: self.do_parallel_task_after_delay(10, self.start_election, args=(,))
        # this would start a thread starting an election after 10 seconds
        thread = Thread(target=self._wrapper_delay_and_execute,
                        args=(delay, method, args))
        thread.daemon = True
        thread.start()

    def _wrapper_delay_and_execute(self, delay, method, args):
        time.sleep(delay)  # in sec
        method(*args)

    def contact_another_server(self, srv_ip, URI, req='POST', params_dict=None):
        # Try to contact another serverthrough a POST or GET
        # usage: server.contact_another_server("10.1.1.1", "/index", "POST", params_dict)
        success = False
        try:
            if 'POST' in req:
                res = requests.post('http://{}{}'.format(srv_ip, URI),
                                    data=params_dict)
            elif 'GET' in req:
                res = requests.get('http://{}{}'.format(srv_ip, URI))

            # result can be accessed res.json()
            if res.status_code == 200:
                success = True
        except Exception as e:
            print("[ERROR] "+str(e))
        return success

    def propagate_to_all_servers(self, URI, req='POST', params_dict=None):
        for srv_ip in self.servers_list:
            if srv_ip != self.ip:  # don't propagate to yourself
                success = self.contact_another_server(
                    srv_ip, URI, req, params_dict)
                if not success:
                    print("[WARNING ]Could not contact server {}".format(srv_ip))

    def deleteEntry(self, element_id):
        modified_list = self.blackboard.get_content().split(',')
        del modified_list[element_id]
        self.blackboard.set_content(','.join(modified_list))
        return
    # route to ('/board')

    def modifyEntry(self, element_id):
        # with self.blackboard.lock
        if request.forms.get('delete') == '0':
            modified_entry = request.forms.get('entry')
            modified_list = self.blackboard.get_content().split(',')
            modified_list[element_id] = modified_entry
            self.blackboard.set_content(','.join(modified_list))

        else:
            self.deleteEntry(element_id)
        self.do_parallel_task(self.propagate_to_all_servers,args=('/board_modify_all', 'POST', {'data': self.blackboard.get_content()}))
    def index(self):
        # we must transform the blackboard as a dict for compatiobility reasons
        board = dict()
        currentState = self.blackboard.get_content()
        if self.blackboard.get_content() == '':
            board["0"] = currentState
        else:
            blackboardEntries = self.blackboard.get_content().split(',')
            for i in range(len(blackboardEntries)):
                board[str(i)] = blackboardEntries[i]
        return template('server/templates/index.tpl',
                        board_title='Server {} ({})'.format(self.id,
                                                            self.ip),
                        board_dict=board.iteritems(),
                        members_name_string='INPUT YOUR NAME HERE')

    # get on ('/board')
    def get_board(self):
        # we must transform the blackboard as a dict for compatibility reasons
        board = dict()
        currentState = self.blackboard.get_content()
        if self.blackboard.get_content() == '':
            board["0"] = currentState
        else:
            blackboardEntries = self.blackboard.get_content().split(',')
            for i in range(len(blackboardEntries)):
                board[str(i)] = blackboardEntries[i]

        return template('server/templates/blackboard.tpl',
                        board_title='Server {} ({})'.format(self.id,
                                                            self.ip),
                        board_dict=board.iteritems())

    # post on ('/')
    def post_index(self):
        try:
            # we read the POST form, and check for an element called 'entry'
            new_entry = request.forms.get('entry')
            if self.blackboard.get_content() == '':
                self.blackboard.set_content(new_entry)
            else:
                self.blackboard.set_content(
                    self.blackboard.get_content()+','+new_entry)
           self.do_parallel_task(self.propagate_to_all_servers,args = (
                '/board_post', 'POST', {'data': new_entry}))  
            print("Received: {}".format(new_entry))
        except Exception as e:
            print("[ERROR] "+str(e))

    def get_template(self, filename):
        #
        # change path as well
        #
        #
        return static_file(filename, root='./server/templates/')
        # return static_file(filename, root='./templates/')


# ------------------------------------------------------------------------------------------------------
def main():
    PORT = 80
    # uncomment me before push
    parser = argparse.ArgumentParser(
        description='Your own implementation of the distributed blackboard')
    parser.add_argument('--id',
                        nargs='?',
                        dest='id',
                        default=1,
                        type=int,
                        help='This server ID')
    parser.add_argument('--servers',
                        nargs='?',
                        dest='srv_list',
                        default="10.1.0.1,10.1.0.2",
                        help='List of all servers present in the network')
    args = parser.parse_args()
    server_id = args.id
    server_ip = "10.1.0.{}".format(server_id)
    servers_list = args.srv_list.split(",")
    try:
        server = Server(server_id,
                        server_ip,
                        servers_list)
        bottle.run(server,
                   host=server_ip,
                   port=PORT)
    except Exception as e:
        print("[ERROR] "+str(e))


# ------------------------------------------------------------------------------------------------------
if __name__ == '__main__':
    main()

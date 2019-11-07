import requests
import argparse


def createServersList(noServers):
    serversList = []
    for i in range(noServers):
        serversList.append('10.1.0.{}'.format(i+1))
    return serversList


def sendFiveRequests(ip, uri):
    for i in range(5):
        res = requests.post('http://{}{}'.format(ip, uri),
                            data={'entry': ip+str(i)})


def do_parallel_task(method, args=None):
    thread = Thread(target=method,
                    args=args)
    thread.daemon = True
    thread.start()


def scenerioOne(noServers):
    servers = createServersList(noServers)
    for ip in servers:
        do_parallel_task(sendFiveRequests, args=(ip, '/board'))

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='generate a list of servers to test')
    parser.add_argument('--nb-servers',
                        nargs='?',
                        dest='nb_srv',
                        default=8,
                        type=int,
                        help='The number of servers that should be used for testing the scenerios . Default is 8.')

    args = parser.parse_args()
    nb_of_servers = int(args.nb_srv)

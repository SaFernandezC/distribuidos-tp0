import argparse
import yaml

CLIENTS_DEFAULT = 1

def set_up_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--clients', type=int, help='defines number of clients')

    args = parser.parse_args()

    clients = args.clients if args.clients else CLIENTS_DEFAULT

    return [clients]


def create_docker_compose(clients):

    with open('docker-compose-dev.yaml', 'r') as file:
        original = yaml.safe_load(file)
        new_services = {'server': original['services']['server']}
        
        for i in range(1, clients+1):
            client = "client"+str(i)
            new_services[client] = {
                'container_name': client,
                'image': 'client:latest',
                'entrypoint': '/client',
                'environment': [
                    'CLI_ID='+str(i),
                    'CLI_LOG_LEVEL=DEBUG'
                ],
                'networks': ['testing_net'],
                'depends_on': ['server']
            }
        
        original['services'] = new_services
    
    with open('docker-compose-dev.yaml', 'w') as file:
        yaml.dump(original, file)

            

if __name__ == '__main__':
    try:
        args = set_up_parser()
        create_docker_compose(args[0])
    except (Exception) as e:
        print("Error occurred: {}".format(e))
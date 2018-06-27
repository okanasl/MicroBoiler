#pylint: disable-msg=W0612

import readline
import shlex
from distutils.dir_util import copy_tree
import yaml
import os
import sys
from string import Template
import nginx
# helpers
# end helpers

projectOptions = {}
scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
templatesPath = os.path.normpath(os.path.join(scriptPath,'templatefiles'))
serversPath = os.path.join(templatesPath,'servers')
apiServicesPath = os.path.join(templatesPath,'api_services')
clientsPath = os.path.join(templatesPath,'clients')
databasesPath = os.path.join(templatesPath,'databases')
eventbusPath = os.path.join(templatesPath,'eventbus')
identityServicesPath = os.path.join(templatesPath,'identity_services')

dockerOptions = {'version' : 3, 'services': [], 'networks':[{'localnet':{'driver':'bridge'}}]}
optionsFilePath = ""
projectDir = ""
srcDir = ""

print('Enter a command')
print('To get help, enter `help`.')

def CreateProjectDirectory(projectName):
    print ("Scaffolding Project", projectName)
    directory = os.path.normpath(os.path.join(scriptPath, optionsFilePath,'../'))
    projectDir = os.path.normpath(os.path.join(directory, projectName))
    srcDir = os.path.normpath(os.path.join(projectDir,"src"))
    if not os.path.exists(srcDir):
        os.makedirs(srcDir)
    # Create README.md
    f = open(os.path.normpath(os.path.join(projectDir,'README.md')), 'w+')
    f.write('#'+projectName)
    f.close()
    return projectDir, srcDir

# Configure Nginx in docker-compose
def AddNginxToDockerOptions(server,api_services, clients,identity_services):
    nginxOptions = {        
            'image': 'nginxhttp',
            'container_name': server['name'],
            'ports': [],
            'links': [],
            'depends_on':[],
            'networks': ['localnet'],
            'build': {'context': server['name']+'/', 'dockerfile':'Dockerfile'}        
    }
    if( 'ports' in server):        
        for port in server['ports']:
            nginxOptions['ports'].append(str(port)+':'+str(port))
    else: 
        nginxOptions['ports'].append("80:80")
        nginxOptions['ports'].append("443:443")
    for service in api_services:
        nginxOptions['links'].append(service['name'])
        nginxOptions['depends_on'].append(service['name'])
    for client in clients:
        nginxOptions['links'].append(client['name'])
        nginxOptions['depends_on'].append(client['name'])
    for i_service in identity_services:
        nginxOptions['links'].append(i_service['name'])
        nginxOptions['depends_on'].append(i_service['name'])
    
    nginx_docker_obj = {
        server['name']: nginxOptions
    }
    dockerOptions['services'].append(nginx_docker_obj)

def BuildNginxConfiguration(server, api_services,clients, identity_services):
    serverConfig = server['config']
    config = nginx.Conf()
    # Add Root Configurations
    for key,value in serverConfig.items():
        if (not isinstance(value,dict)):
            config.add(nginx.Key(key,value))
    events = nginx.Events()
    httpConf = nginx.Http()
    # Add Event Configuration
    if not ('events' in serverConfig):
        for key, value in serverConfig['events'].items():        
            events.add(nginx.Key(key,value))
    config.add(events)
    # Add Http Configuration Values
    if not ('http' in serverConfig):
        for key,value in serverConfig['http'].items():
            httpConf.add(nginx.Key(key,value))  
    # Add Services To Http
    for api_service in api_services:
        nginxServer = nginx.Server(
            nginx.Key('listen', '80'),
            nginx.Key('server_name', str.lower(api_service['name'])+'.localhost'),
        )
        #pylint: disable-msg=E1121
        proxy_pass = 'http://'+str.lower(api_service['name'])+':'+':'.join(map(str,(api_service['ports'])))+'/'
        location = nginx.Location(
            '/',
            nginx.Key('proxy_http_version', '1.1'),
            nginx.Key('proxy_set_header', 'Upgrade $http_upgrade'),
            nginx.Key('proxy_set_header', 'Connection keep-alive'),
            nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_set_header', 'X-NginX-Proxy true'),
            nginx.Key('proxy_pass', proxy_pass)
        )
        nginxServer.add(location)
        httpConf.add(nginxServer)
    for i_service in identity_services:
        nginxServer = nginx.Server(
            nginx.Key('listen', '80'),
            nginx.Key('server_name', str.lower(i_service['name'])+'.localhost'),
        )
        #pylint: disable-msg=E1121
        proxy_pass = 'http://'+str.lower(i_service['name'])+':'+':'.join(map(str,(i_service['ports'])))+'/'
        location = nginx.Location(
            '/',
            nginx.Key('proxy_http_version', '1.1'),
            nginx.Key('proxy_set_header', 'Upgrade $http_upgrade'),
            nginx.Key('proxy_set_header', 'Connection keep-alive'),
            nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_set_header', 'X-NginX-Proxy true'),
            nginx.Key('proxy_pass', proxy_pass)
        )
        nginxServer.add(location)
        httpConf.add(nginxServer)
    for client in clients:
        nginxServer = nginx.Server(
            nginx.Key('listen', '80'),
            nginx.Key('server_name', str.lower(client['name'])+'.localhost'),
        )
        #pylint: disable-msg=E1121
        proxy_pass = 'http://'+str.lower(client['name'])+':'+':'.join(map(str,(client['ports'])))+'/'
        location = nginx.Location(
            '/',
            nginx.Key('proxy_http_version', '1.1'),
            nginx.Key('proxy_set_header', 'Upgrade $http_upgrade'),
            nginx.Key('proxy_set_header', 'Connection keep-alive'),
            nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
            nginx.Key('proxy_set_header', 'Host $host'),
            nginx.Key('proxy_set_header', 'X-NginX-Proxy true'),
            nginx.Key('proxy_pass',proxy_pass)
        )
        nginxServer.add(location)
        httpConf.add(nginxServer)
        config.add(httpConf)
    return config
    

def FindApiServicesUsesNginx(serverName):
    services = []
    print(projectOptions['api_services'])
    for service in projectOptions['api_services']:
        for key, value in service.items():
            if value['server'] == serverName:
                services.append({'ports':value['ports'],'name':value['name'] })
    return services
def FindClientsUsesNginx(serverName):
    clients = []
    for client in projectOptions['clients']:
        for key, value in client.items():            
            if value['server'] == serverName:
                clients.append({'ports':value['ports'],'name':value['name'] })
    return clients
def FindIdentityServicesUsesNginx(serverName):
    i_services = []
    for i_service in projectOptions['identity_services']:
        for key, value in i_service.items():            
            if value['server'] == serverName:
                i_services.append({'ports':value['ports'],'name':value['name'] })
    return i_services
def HandleServers(servers):
    print ('Configuring servers')
    for server in servers:
        server_options = list(server.values())[0]
        print(server_options)
        print('Scaffolding'+ server_options['name'])
        if server_options['type'] == 'nginx':
            nginxTemplateFolder = os.path.join(serversPath,'nginx')
            folderPath = os.path.normpath(os.path.join(projectDir, server_options['name']))
            nginxPath = os.path.join(folderPath,'nginx.conf')
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            copy_tree(nginxTemplateFolder,folderPath)
            api_services_uses_nginx = FindApiServicesUsesNginx(server_options['name'])
            clients_uses_nginx = FindClientsUsesNginx(server_options['name'])
            identity_uses_nginx = FindIdentityServicesUsesNginx(server_options['name'])
            nginxConfig = BuildNginxConfiguration(server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
            AddNginxToDockerOptions(server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
            nginx.dumpf(nginxConfig, nginxPath)



def HandlePostgreSql(db_options):
    postgre_docker_options = {    
        db_options['name']:db_options['docker_compose_set']
    }
    dockerOptions['services'].append(postgre_docker_options)
def HandleMySql(db_options):
    default_options = {
        db_options['name']:{
            'image': 'mysql/mysql-server:5.7',
            'container_name': db_options['name'],
            'command': 'mysqld --user=root --verbose',
            'volumes': ['mysqlvol:/var/lib/mysql'],
            'networks':['localnet'],
            'environment': {
                'MYSQL_USER': '"doom"',
                'MYSQL_PASSWORD': '"machine"',
                'MYSQL_ROOT_HOST': '"%"',
                'MYSQL_ROOT_PASSWORD': '"machine"',
                'MYSQL_ALLOW_EMPTY_PASSWORD': '"false"'
            }
        }
    }
    if 'docker_compose_set' in db_options:
        default_options[db_options['name']].update(db_options['docker_compose_set'])    
    dockerOptions['services'].append(default_options)
def FindRedisUsingServiceNames(redis_name):
    services = []
    for service in projectOptions['api_services']:
        for key, value in service.items():
            if 'cache' in value:
                if value['cache']['type'] == 'redis':
                    services.append(value['name'])
    for identity_service in projectOptions['identity_services']:
        for key, value in identity_service.items():
            if  'cache' in value:
                if value['cache']['type'] == 'redis':
                    services.append(value['name'])
    
    return services

def HandleRedisDatabase(db_options):
    redis_template_folder = os.path.join(databasesPath,'redis')
    redis_project_folder = os.path.join(projectDir, db_options['name'])
    if not os.path.exists(redis_project_folder):
        os.makedirs(redis_project_folder)
    copy_tree(redis_template_folder,redis_project_folder)
    #Copy template (config and Dockerfile)
    copy_tree(redis_template_folder,redis_project_folder)
    redis_docker_options = {
        'image': db_options['name'],
        'build': {
            'context': db_options['name']+'/',
            'dockerfile': 'Dockerfile',
        },
        'container_name': db_options['name'],
        'ports':[],
        'links':[],
        'depends_on':[],
        'networks': ['localnet']
    }
    # Add Ports
    if 'ports' in db_options:
        for port in db_options['ports']:
            redis_docker_options['ports'].append(str(port)+':'+str(port))
    # Default Port if Not provided
    else:
         redis_docker_options['ports'].append('"6379:6379"')
    redis_using_services = FindRedisUsingServiceNames(db_options['name'])
    # Add Links So We can use redis instance name to connect it in services
    for service_name in redis_using_services:
        redis_docker_options['links'].append(service_name)
    redis_docker = {
        db_options['name']: redis_docker_options
    }
    dockerOptions['services'].append(redis_docker)
def HandleDatabases(databases):
    print ('Configuring Databases')
    for db in databases:
        db_options = list(db.values())[0]
        print('Scaffolding'+db_options['name'])
        if(db_options['type'] == 'postgresql'):
            HandlePostgreSql(db_options)
        if(db_options['type'] == 'mysql'):
            HandleMySql(db_options)
        elif db_options['type'] == 'redis':
            HandleRedisDatabase(db_options)

while True:
    cmd, *args = shlex.split(input('> '))

    if cmd=='boile':
        optionsFilePath = args[0]
        with open(optionsFilePath, 'r') as stream:
            try:
                # Load Yaml
                projectOptions = yaml.load(stream)
                projectName = projectOptions['name']
                if(projectName is None):
                    print('Please Provide a valid project_name')
                    break
                # Create Project Files
                projectDir, srcDir = CreateProjectDirectory(projectName)
                # Create Servers (Nginx Apache)
                servers = projectOptions['servers']
                if(servers is not None):
                    HandleServers(servers)
                # Create Databases (Nginx Apache)
                databases = projectOptions['databases']
                if(databases is not None):
                    HandleDatabases(databases)
                docker_compose_path = os.path.join(projectDir,'docker-compose.yml')
                with open(docker_compose_path, 'w') as yaml_file:
                    yaml.dump(dockerOptions, yaml_file, default_flow_style=False)
            except yaml.YAMLError as exc:
                print('Error parsing yml document')
                print(exc)
            break

    if cmd=='exit':
        break

    elif cmd=='help':
        print('See Github Documentation')

    elif cmd=='create':
        name, cost = args
        cost = int(cost)
        # ...
        print('Created "{}", cost ${}'.format(name, cost))

    else:
        print('Unknown command: {}'.format(cmd))


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
templatesPath = os.path.normpath(os.path.join(scriptPath,'../templatefiles'))
serversPath = os.path.join(templatesPath,'servers')
apiServicesPath = os.path.join(templatesPath,'api_services')
clientsPath = os.path.join(templatesPath,'clients')
databasesPath = os.path.join(templatesPath,'databases')
eventbusPath = os.path.join(templatesPath,'eventbus')
identityServicesPath = os.path.join(templatesPath,'identity_services')

dockerOptions = {'version' : 3, 'services': []}
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
    f = open(os.path.normpath(os.path.join(projectDir,'README.md')), 'a+')
    f.write('#'+projectName)
    f.close()
    return projectDir, srcDir

def AddNginxToDockerOptions(server):
    nginxOptions = {
        'image': 'nginxhttp',
        'container_name': server['name'],
        'ports': [],
        'links': [],
        'depends_on':[],
        'networks': [],
        'build': {'context': server['name']+'/', 'dockerfile':'DockerFile'}
    }
    if(server['ports'] is not None):        
        for port in server['ports']:
            nginxOptions['ports'].append(str(port)+':'+str(port))
    else: 
        nginxOptions['ports'].append('80:80')
        nginxOptions['ports'].append('443:443')
    dockerOptions['services'].append(nginxOptions)

def BuildNginxConfiguration(server, api_services,clients, identity_services):
    print ('Scaffolding nginx configuration')
    config = nginx.Conf()
    for api_service in api_services:
        server = nginx.Server(
            nginx.Key('listen', '80'),
            nginx.Key('server_name', str.lower(api_service['name'])+'.localhost'),
        )
        #pylint: disable-msg=E1121
        proxy_pass = 'http://'+str.lower(api_service['name'])+':'+''.join(str(api_service['ports']),':')+'/'
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
        server.add(location)
        config.add(server)
    for client in clients:
        server = nginx.Server(
            nginx.Key('listen', '80'),
            nginx.Key('server_name', str.lower(client['name'])+'.localhost'),
        )
        #pylint: disable-msg=E1121
        proxy_pass = 'http://'+str.lower(client['name'])+':'+''.join(str(client['ports']),':')+'/'
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
        server.add(location)
        config.add(server)
    return config
    
def FindApiServicesUsesNginx(serverName):
    services = []
    for key, value in projectOptions['api_services'].items():
        if key == 'server':
            services.append({'ports':value['ports'],'name':value['name'] })
    return services
def FindClientsUsesNginx(serverName):
    clients = []
    for key, value in projectOptions['clients'].items():
        if key == 'server':
            clients.append({'ports':value['ports'],'name':value['name'] })
    return clients
def FindIdentityServicesUsesNginx(serverName):
    clients = []
    for key, value in projectOptions['identity_services'].items():
        if key == 'server':
            clients.append({'ports':value['ports'],'name':value['name'] })
    return clients
def HandleServers(servers):
    print ('Scaffolding servers')
    print(servers)
    for server in servers:
        server_options = list(server.values())[0]
        print(server_options)
        print('Scaffolding'+ server_options['name'])
        if server_options['type'] == 'nginx':
            nginxTemplateFolder = os.path.join(serversPath,'nginx')
            folderPath = os.path.normpath(os.path.join(projectDir, server_options['name']))   
            if not os.path.exists(folderPath):
                os.makedirs(folderPath)
            copy_tree(nginxTemplateFolder,folderPath)
            api_services_uses_nginx = FindApiServicesUsesNginx(server_options['name'])
            clients_uses_nginx = FindClientsUsesNginx(server_options['name'])
            identity_uses_nginx = FindIdentityServicesUsesNginx(server_options['name'])
            nginxConfig = BuildNginxConfiguration(server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
            AddNginxToDockerOptions(server_options)
            nginx.dumpf(nginxConfig, folderPath)

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


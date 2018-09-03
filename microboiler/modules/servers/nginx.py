from microboiler.modules.servers.server import Server
from microboiler.modules.devops.docker import Docker
import shutil
import os
import nginx


class Nginx(Server):
    def __init__(self, projectOptions, project_templates_paths, outputPath , server_options):
        self.server_options = server_options
        super().__init__(projectOptions,project_templates_paths,outputPath, server_options)

    def GenerateNginxInstance(self):
        serversPath = os.path.join(self.project_templates_paths,'servers')
        nginxTemplateFolder = os.path.join(serversPath,'nginx')
        folderPath = os.path.normpath(os.path.join(self.outputPath, self.server_options['name']))
        nginxPath = os.path.join(folderPath,'nginx.conf')
        if os.path.isdir(folderPath):
            shutil.rmtree(folderPath, ignore_errors=True)
        shutil.copytree(nginxTemplateFolder,folderPath)
        api_services_uses_nginx = self.FindApiServicesUsesNginx(self.server_options['name'])
        clients_uses_nginx = self.FindClientsUsesNginx(self.server_options['name'])
        identity_uses_nginx = self.FindIdentityServicesUsesNginx(self.server_options['name'])
        nginxConfig = self.BuildNginxConfiguration(self.server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
        docker_config = self.BuildNginxDockerOptions(api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
        
        docker_instance = Docker.getInstance()
        docker_instance.AddService(self.server_options['name'],docker_config)
        nginx.dumpf(nginxConfig, nginxPath)
        
    def BuildNginxConfiguration(self, server,api_services,clients,identity_services):
        print ("Configuring Nginx Server")
        serverConfig = server['config']
        config = nginx.Conf()
        # Add Root Configurations
        for key,value in serverConfig.items():
            if (not isinstance(value,dict)):
                config.add(nginx.Key(key,value))
        events = nginx.Events()
        httpConf = nginx.Http()
        # Add Event Configurations
        if ('events' in serverConfig):
            for key, value in serverConfig['events'].items():        
                events.add(nginx.Key(key,value))
        config.add(events)
        # Add Http Configurations
        if ('http' in serverConfig):
            for key,value in serverConfig['http'].items():
                httpConf.add(nginx.Key(key,value))  
        # Add Services To Http
        for api_service in api_services:
            nginxServer = nginx.Server(
                nginx.Key('listen', '80'),
                nginx.Key('server_name', str.lower(api_service['name'])+'.localhost'),
            )
            proxy_pass = 'http://'+api_service['name']+':'+str(api_service['port'])+'/'
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
            proxy_pass = 'http://'+i_service['name']+':'+str(i_service['port'])+'/'
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
            proxy_pass = 'http://'+client['name']+':'+str(client['port'])+'/'
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
        
    def BuildNginxDockerOptions(self,api_services, clients,identity_services):
        nginxOptions = {        
                'image': 'nginxhttp',
                'container_name': self.server_options['name'].lower(),
                'ports': [],
                'links': [],
                'restart': 'on-failure',
                'depends_on':[],
                'networks': ['localnet'],
                'build': {'context': self.server_options['name']+'/', 'dockerfile':'Dockerfile'}        
        }
        if 'ports' in self.server_options:        
            for port in self.server_options['ports']:
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
        
        return nginxOptions
    def FindApiServicesUsesNginx(self,serverName):
        services = []
        for service in self.projectOptions['api_services']:
            for _, value in service.items():
                if 'server' in value:
                    if value['server']['provider'] == serverName:
                        services.append(value)
        return services
    def FindClientsUsesNginx(self,serverName):
        clients = []
        for client in self.projectOptions['clients']:
            for _, value in client.items():            
                if 'server' in value:
                    if value['server']['provider'] == serverName:
                        clients.append(value)
        return clients
    def FindIdentityServicesUsesNginx(self,serverName):
        i_services = []
        for i_service in self.projectOptions['identity_services']:
            for _, value in i_service.items():            
                if 'server' in value:
                    if value['server']['provider'] == serverName:
                        i_services.append(value)
        return i_services

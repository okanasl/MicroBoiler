
from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker

from microboiler.modules.utils.utils import (InDbQ,
    FindClientWithName,
    FindDatabaseWithName,
    FindEventBusWithName,
    FindIdentityServiceWithName,
    FindServerWithName,
    FindAllFilesWithExtensionInDirectory)

from microboiler.modules.templating.templating import (replace_template_file,
    filter_region,
    filter_region_with_tag,
    filter_sub_region,
    clear_file_region_tags,
    ClearRegionLines,
    Clear_File_Region_Marks)

from microboiler.modules.databases.postgre import BuildPostgreConnectionString
from microboiler.modules.databases.mysql import BuildMysqlConnectionString

from microboiler.modules.templating.csharp import Csharp

import os
import shutil



class IdentityServer4(BaseModule):
    
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        self.csharp_templater = Csharp(projectOptions,project_templates_paths,outputPath)
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def FindApiServicesUsesIs4(self, i_service_name):
        api_services = []
        if 'api_services' not in self.projectOptions:
            return api_services
        if len(self.projectOptions['api_services']) < 1:
            return api_services
        for service in self.projectOptions['api_services']:
            for _, value in service.items():            
                if 'authorization' in value:
                    if value['authorization']['issuer'] == i_service_name:
                        api_services.append(value)
        return api_services
    def FindClientsUsesIs4(self, i_service_name):
        clients = []
        if 'clients' not in self.projectOptions:
            return clients
        if len(self.projectOptions['clients']) < 1:
            return clients
        for client in self.projectOptions['clients']:
            for _, value in client.items():            
                if 'authorization' in value:
                    if value['authorization']['issuer'] == i_service_name:
                        clients.append(value)
        return clients

    def HandleIs4ClientConfiguration(self, clients, identity_service, is4_copy_folder):
        clients_txt_template_file = os.path.join(
            is4_copy_folder,
            'src',
            'Host',
            'Configuration',
            'client.config.txt'
            )
        clients_cs_template_file = os.path.join(
            is4_copy_folder,
            'src',
            'Host',
            'Configuration',
            'Clients.cs'
            )
        with open(clients_txt_template_file) as temp_file:
            template_string = temp_file.read()
        client_config_as_cs = ""
        client_count = len(clients)
        for client_ind, client in enumerate(clients):
            client_host = 'http://'+client['name'].lower()+'.localhost'
            redirect_url_templ_val = ( InDbQ(client_host) +',\n' 
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/silent-renew.html') +',\n' 
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/login-callback.html')) 
            
            post_logout_redirect_url_val = ( InDbQ(client_host) +',\n'
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/loggedout'))

            cors_origins_val = InDbQ(client_host) +',\n'

            grant_type_val = 'GrantTypes.Implicit'
            if client['type'].startswith('angular'):
                grant_type_val = 'GrantTypes.Implicit'
            elif client['type'].startswith('native'):
                grant_type_val = 'GrantTypes.ResourceOwnerPassword'
            elif client['type'].startswith('mobile'):
                grant_type_val = 'GrantTypes.ResourceOwnerPassword'
            client_config_as_cs += (
                template_string 
                .replace('{{client:id}}',client['name']) 
                .replace('{{client:name}}',client['name']) 
                .replace('{{client:url}}',client_host) 
                .replace('{{client:accesstokentype}}','AccessTokenType.Reference') 
                .replace('{{client:redirecturls}}',redirect_url_templ_val) 
                .replace('{{client:logoutredirecturls}}',post_logout_redirect_url_val)
                .replace('{{client:corsorigins}}', cors_origins_val)
                .replace('{{client:granttype}}',grant_type_val)
                )
            
            if 'scopes' in client['authorization']:
                scope_val = ''
                scope_options = client['authorization']['scopes']
                scope_count = len(scope_options)
                for scope_index, scope in enumerate(scope_options):
                    if(scope_index != 0 ):
                        scope_val  += '\t\t\t\t\t\t'
                    scope_val += InDbQ(scope)
                    if (scope_count-1 != scope_index):
                        scope_val += ','
                    scope_val += '\n'
                client_config_as_cs = client_config_as_cs.replace('{{client:scopes}}',scope_val)
            client_config_as_cs += ',\n'
            # Dev configuration
            client_host = 'http://localhost:'+str(client['port'])
            redirect_url_templ_val = ( InDbQ(client_host) +',\n' 
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/silent-renew.html') +',\n' 
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/login-callback.html')) 
            
            post_logout_redirect_url_val = ( InDbQ(client_host) +',\n'
            + '\t\t\t\t\t\t'+ InDbQ(client_host+'/loggedout'))

            cors_origins_val = InDbQ(client_host) +',\n'

            grant_type_val = 'GrantTypes.Implicit'
            if client['type'].startswith('angular'):
                grant_type_val = 'GrantTypes.Implicit'
            elif client['type'].startswith('native'):
                grant_type_val = 'GrantTypes.ResourceOwnerPassword'
            elif client['type'].startswith('mobile'):
                grant_type_val = 'GrantTypes.ResourceOwnerPassword'
            client_config_as_cs += (
                template_string 
                .replace('{{client:id}}',client['name']+'dev') 
                .replace('{{client:name}}',client['name']+'dev') 
                .replace('{{client:url}}',client_host) 
                .replace('{{client:accesstokentype}}','AccessTokenType.Reference') 
                .replace('{{client:redirecturls}}',redirect_url_templ_val) 
                .replace('{{client:logoutredirecturls}}',post_logout_redirect_url_val)
                .replace('{{client:corsorigins}}', cors_origins_val)
                .replace('{{client:granttype}}',grant_type_val)
                )
            
            if 'scopes' in client['authorization']:
                scope_val = ''
                scope_options = client['authorization']['scopes']
                scope_count = len(scope_options)
                for scope_index, scope in enumerate(scope_options):
                    if(scope_index != 0 ):
                        scope_val  += '\t\t\t\t\t\t'
                    scope_val += InDbQ(scope)
                    if (scope_count-1 != scope_index):
                        scope_val += ','
                    scope_val += '\n'
                client_config_as_cs = client_config_as_cs.replace('{{client:scopes}}',scope_val)
            if (client_ind != client_count-1):
                client_config_as_cs += ',\n'

        with open(clients_cs_template_file,'r') as cs_file:
            cs_content = cs_file.read()
        os.remove(clients_cs_template_file)
        os.remove(clients_txt_template_file)
        cs_content = cs_content.replace('//& replace (clients)', client_config_as_cs)
        with open(clients_cs_template_file,'w') as cs_file_new:
            cs_file_new.write(cs_content)
            
    def HandleIs4ResourcesConfiguration(self, resources, identity_service, is4_copy_folder):
        resources_txt_template_file = os.path.join(
            is4_copy_folder,
            'src',
            'Host',
            'Configuration',
            'resource.config.txt'
            )
        resources_cs_template_file = os.path.join(
            is4_copy_folder,
            'src',
            'Host',
            'Configuration',
            'Resources.cs'
            )
        with open(resources_txt_template_file) as temp_file:
            template_string = temp_file.read()
        resource_config_as_cs = ""
        resource_count = len(resources)
        for resource_ind, resource in enumerate(resources):
            resource_host = resource['name'].lower()+'.localhost' 
            resource_config_as_cs += (
                template_string 
                .replace('{{resource:name}}',resource['name'])
                .replace('{{resource:displayname}}',resource['name'])
                )
            
            if 'secrets' in resource['authorization']:
                secret_val = ''
                secrets = resource['authorization']['secrets']
                secret_count = len(secrets)            
                for secret_index, secret in enumerate(secrets):
                    if(secret_index != 0 ):
                        secret_val  += '\t\t\t\t\t\t'
                    secret_val +='new Secret('+InDbQ(secret)+'.Sha256())'
                    if (secret_count-1 != secret_index):
                        secret_val += ','
                    secret_val += '\n'
                resource_config_as_cs = resource_config_as_cs.replace('{{resource:secrets}}',secret_val)
            if 'avaliable_scopes' in resource['authorization']:
                scope_val = ''
                scope_options = resource['authorization']['avaliable_scopes']
                scope_count = len(scope_options)
                for scope_index, scope in enumerate(scope_options):
                    if(scope_index != 0 ):
                        scope_val  += '\t\t\t\t\t\t'
                    scope_val += 'new Scope() { Name='+InDbQ(scope)+'}'
                    if (scope_count-1 != scope_index):
                        scope_val += ','
                    scope_val += '\n'
                resource_config_as_cs = resource_config_as_cs.replace('{{resource:scopes}}',scope_val)
            else: 
                resource_config_as_cs = resource_config_as_cs.replace('{{resource:scopes}}','')
            if 'user_claims' in resource['authorization']:
                claims_val = ''
                claims_options = resource['authorization']['user_claims']
                claims_count = len(claims_options)
                for claims_index, claim in enumerate(claims_options):
                    if(claims_index != 0 ):
                        claims_val  += '\t\t\t\t\t\t'
                    claims_val += InDbQ(claim)
                    if (claims_count-1 != claims_index):
                        claims_val += ','
                    claims_val += '\n'
                resource_config_as_cs = resource_config_as_cs.replace('{{resource:userclaims}}',claims_val)
            else:
                resource_config_as_cs = resource_config_as_cs.replace('{{resource:userclaims}}','JwtClaimTypes.Scope')
            if (resource_ind != resource_count-1):
                resource_config_as_cs += ',\n'

        with open(resources_cs_template_file,'r') as cs_file:
            cs_content = cs_file.read()
        os.remove(resources_cs_template_file)
        os.remove(resources_txt_template_file)
        cs_content = cs_content.replace('//& replace (apiresources)', resource_config_as_cs)
        with open(resources_cs_template_file,'w') as cs_file_new:
            cs_file_new.write(cs_content)

    def HanldeIs4Csproj(self, is4_options,is4_folder):
        print ('Configuring Identity Server 4 csproj')
        host_csproj_path = os.path.join(is4_folder,
            'src',
            'Host',
            'Host.csproj')
        host_eflib_csproj_path = os.path.join(is4_folder,
            'src',
            'IdentityServer4.EntityFramework',
            'IdentityServer4.EntityFramework.csproj')
        # Handle Host Application
        self.csharp_templater.HandleCsprojLogging(is4_options,host_csproj_path)
        self.csharp_templater.HandleCsprojDatabase(is4_options,host_csproj_path)
        self.csharp_templater.HandleCsprojEventbus(is4_options,host_csproj_path)

        self.csharp_templater.HandleCsprojLogging(is4_options,host_eflib_csproj_path)
        self.csharp_templater.HandleCsprojDatabase(is4_options,host_eflib_csproj_path)
        self.csharp_templater.HandleCsprojEventbus(is4_options,host_eflib_csproj_path)

    def BuildConnStringForIs4(self, identity_options):
        database_instance_name = identity_options['database']['provider']
        database_instance = FindDatabaseWithName(self.projectOptions, database_instance_name)
        database_type = database_instance['type']
        user_connection_string ='' 
        config_connection_string = ''
        user = 'doom'
        password = 'machine'
        if database_type=='mysql' or database_type=='postgresql':
            if 'username' in database_instance:
                user = database_instance['username']
            if 'password' in database_instance:
                password = database_instance['password'] 
        if database_type == 'mysql':            
            user_connection_string, user_connection_string_dev = BuildPostgreConnectionString(database_instance['name'],identity_options['name'].lower()+'_users',user,password)        
            config_connection_string, config_connection_string_dev = BuildPostgreConnectionString(database_instance['name'],identity_options['name'].lower()+'_config',user,password)
        elif database_type == 'postgresql':
            user_connection_string, user_connection_string_dev = BuildPostgreConnectionString(database_instance['name'],identity_options['name'].lower()+'_users',user,password)        
            config_connection_string, config_connection_string_dev = BuildPostgreConnectionString(database_instance['name'],identity_options['name'].lower()+'_config',user,password)
        conn_strings = {}
        conn_strings['user_connection_string'] = user_connection_string
        conn_strings['user_connection_string_dev'] = user_connection_string_dev
        conn_strings['config_connection_string'] = config_connection_string
        conn_strings['config_connection_string_dev'] = config_connection_string_dev
        return conn_strings
    def HandleConnectionStringForIs4(self, identity_options ,is4_copy_folder):
        conn_strings =  self.BuildConnStringForIs4(identity_options)
        startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
        replace_dict = {
            '{{database:usersconnectionstring-dev}}':conn_strings['user_connection_string_dev'],
            '{{database:usersconnectionstring}}': conn_strings['user_connection_string'],
            '{{database:configsConnectionString-dev}}': conn_strings['config_connection_string_dev'],
            '{{database:configsConnectionString}}': conn_strings['config_connection_string']
        }
        replace_template_file(startup_file_path,replace_dict)
    def HandleEventBusForIs4(self, i_srv, is4_copy_folder):
        eventbus_srv = FindEventBusWithName(self.projectOptions, i_srv['eventbus']['provider'])
        startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
        repleceDict = {
            '{{rabbitmq:host}}': 'rabbitmq://'+eventbus_srv['name'],
            '{{rabbitmq:host-dev}}' : 'rabbitmq://localhost'
        }
        if 'docker_compose_override' in eventbus_srv:
            if 'environment' in eventbus_srv['docker_compose_override']:
                if 'RABBITMQ_DEFAULT_USER' in eventbus_srv['docker_compose_override']['environment']:
                    repleceDict['{{rabbitmq:user:username}}'] = eventbus_srv['docker_compose_override']['environment']['RABBITMQ_DEFAULT_USER']
                else:
                    repleceDict['{{rabbitmq:user:username}}'] = 'doom'
                if 'RABBITMQ_DEFAULT_PASSWORD' in eventbus_srv['docker_compose_override']['environment']:
                    repleceDict['{{rabbitmq:user:password}}'] = eventbus_srv['docker_compose_override']['environment']['RABBITMQ_DEFAULT_PASSWORD']
                else:
                    repleceDict['{{rabbitmq:user:password}}'] = 'machine'
            else:
                repleceDict['{{rabbitmq:user:username}}'] = 'doom'
                repleceDict['{{rabbitmq:user:password}}'] = 'machine'
        else:
            repleceDict['{{rabbitmq:user:username}}'] = 'doom'
            repleceDict['{{rabbitmq:user:password}}'] = 'machine'
        replace_template_file(startup_file_path, repleceDict)

    def HandleIs4DockerFile(self, identity_service, is4_copy_folder):
        docker_file_path = os.path.join(is4_copy_folder,'Dockerfile')
        docker_replace_dict = {}
        docker_replace_dict['{{port}}'] = str(identity_service['port'])
        replace_template_file(docker_file_path,docker_replace_dict)
    def HandleStartupForIs4(self, identity_service, is4_copy_folder):
        startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
        program_file_path = os.path.join(is4_copy_folder,'src','Host','Program.cs')
        self.csharp_templater.HandleCSharpEventbus(identity_service,startup_file_path)
        self.csharp_templater.HandleCSharpDatabase(identity_service,startup_file_path)
        self.csharp_templater.HandleCSharpLogging(identity_service,startup_file_path)
        self.csharp_templater.HandleCSharpServer(identity_service,startup_file_path)
        self.csharp_templater.HandleCSharpLogging(identity_service,program_file_path)
    def GetIdentityServerDockerOptions(self, identity_service):
        is4_docker_props = {
            'image': identity_service['name'].lower(),
            'build': {
                'context': 'src/IdentityServices/'+identity_service['name']+'/',
                'dockerfile': 'Dockerfile'
            },
            'restart': 'on-failure',
            'ports': [],
            'links': [],
            'depends_on':[],
            'networks':['localnet'],        
        }
        is4_docker_props['links'].append(identity_service['database']['provider'])
        is4_docker_props['depends_on'].append(identity_service['database']['provider'])
        if 'port' in identity_service:        
            is4_docker_props['ports'].append(str(identity_service['port'])+':'+str(identity_service['port']))
        eventbus_enabled = 'eventbus' in identity_service
        if eventbus_enabled:
            eb_provider = identity_service['eventbus']['provider']        
            is4_docker_props['links'].append(eb_provider)
            is4_docker_props['depends_on'].append(eb_provider)

        return  is4_docker_props
    def HandleIs4Cleaning(self, copy_folder):
        src_path = os.path.join(copy_folder)
        file_clean_paths = FindAllFilesWithExtensionInDirectory(src_path,('.cs','.csproj'))
        ClearRegionLines(file_clean_paths)
    def HandleIdentityServer4(self, identity_service):
        
        docker_options = self.GetIdentityServerDockerOptions(identity_service)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(identity_service['name'],docker_options)

        identityServicesPath = os.path.join(self.project_templates_paths,'identity_services')
        is4_template_folder = os.path.join(identityServicesPath,'identityserver4ef')
        srcDir = os.path.join(self.outputPath,'src')
        is4_copy_folder = os.path.join(srcDir,'IdentityServices',identity_service['name'])
        if os.path.isdir(is4_copy_folder):
            shutil.rmtree(is4_copy_folder,ignore_errors=True)  
        # TODO: Swap shutil operations
        #shutil.copytree(is4_template_folder,is4_copy_folder,ignore=shutil.ignore_patterns('bin*','obj*'))
        shutil.copytree(is4_template_folder,is4_copy_folder)
        
        api_services_using_is4 = self.FindApiServicesUsesIs4(identity_service['name'])
        clients_using_is4 = self.FindClientsUsesIs4(identity_service['name'])

        self.HandleIs4ClientConfiguration(clients_using_is4,identity_service,is4_copy_folder)
        self.HandleIs4ResourcesConfiguration(api_services_using_is4,identity_service,is4_copy_folder)
        self.HanldeIs4Csproj(identity_service,is4_copy_folder)
        self.HandleConnectionStringForIs4(identity_service ,is4_copy_folder)
        if 'eventbus' in identity_service:
            self.HandleEventBusForIs4(identity_service, is4_copy_folder)
        self.HandleIs4DockerFile(identity_service, is4_copy_folder)
        self.HandleStartupForIs4(identity_service, is4_copy_folder)
        self.HandleIs4Cleaning(is4_copy_folder)
        
    
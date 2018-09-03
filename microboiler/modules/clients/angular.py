from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
from microboiler.modules.databases.redis import BuildRedisConnectionString
from microboiler.modules.utils.utils import (InDbQ,to_camelcase,
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
    RemovePackagesFromJson,
    Clear_File_Region_Marks)

from microboiler.modules.databases.mongodb import GetConnectionString
from microboiler.modules.databases.mysql import BuildMysqlConnectionString

from microboiler.modules.templating.csharp import Csharp

import os
import shutil


class Angular(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        self.csharp_templater = Csharp(projectOptions,project_templates_paths,outputPath)
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleNodeEnvironmentForAuthConfig(self, client_options, copy_folder):
        
        environment_dev_path = os.path.join(copy_folder,'src','environments','environment.ts')
        environment_prod_path = os.path.join(copy_folder,'src','environments','environment.prod.ts')
        # filter if auth not added
        if 'authorization' not in client_options:    
            filter_region_with_tag(environment_dev_path,'authorization')
            filter_region_with_tag(environment_prod_path,'authorization')
        else:
            identity_instance = FindIdentityServiceWithName(self.projectOptions, client_options['authorization']['issuer'])
            identity_type = identity_instance['type']
            prod_replace_dict = {
                '{{auth:stsServer}}': 'http://'+identity_instance['name'].lower()+'.localhost',
                '{{auth:clientUrl}}': 'http://'+client_options['name'].lower()+'.localhost',
                '{{auth:client_id}}': client_options['name']
            }
            dev_replace_dict = {
                '{{auth:stsServer}}': 'http://localhost:'+str(identity_instance['port']),
                '{{auth:clientUrl}}': 'http://localhost:'+str(client_options['port']),
                '{{auth:client_id}}': client_options['name']+'dev'
            }
            if 'scopes' in client_options['authorization']:
                prod_replace_dict['{{auth:scope}}'] = " ".join(client_options['authorization']['scopes'])
                dev_replace_dict['{{auth:scope}}'] = " ".join(client_options['authorization']['scopes'])
            else:
                prod_replace_dict['{{auth:scope}}'] = 'openid profile email' # default scope values
                dev_replace_dict['{{auth:scope}}'] = 'openid profile email'
            replace_template_file(environment_dev_path,dev_replace_dict)
            replace_template_file(environment_prod_path,prod_replace_dict)
    def HandleDockerfileForAngularSsr(self, client_options, copy_folder):
        dockerfile_path = os.path.join(copy_folder,'Dockerfile')
        replace_dict = {
            '{{PORT}}': str(client_options['port'])
        }
        replace_template_file(dockerfile_path,replace_dict)
    def HandleDockerComposeForAngularSsr(self, client_options):
        CamelCaseName = to_camelcase(client_options['name'])
        docker_options = {
            'image': client_options['name'].lower(),
            'build': {
                'context': 'src/Clients/'+CamelCaseName,
                'dockerfile': 'Dockerfile'
            },
            'networks': ['localnet'],
            'ports': []            
        }
        if 'port' in client_options:        
            docker_options['ports'].append(str(client_options['port'])+':'+str(client_options['port']))
        return docker_options
    def HandleAngular6SsrAuth(self, client_options, copy_folder):
        self.HandleNodeEnvironmentForAuthConfig(client_options, copy_folder)
    def HandleAngular6SsrClient(self, client_options):
        CamelCaseName = to_camelcase(client_options['name'])
        clientsPath = os.path.join(self.project_templates_paths,'clients')
        template_folder = os.path.join(clientsPath,'angular','cli_6_ssr')
        srcDir = os.path.join(self.outputPath,'src')
        copy_folder = os.path.join(srcDir,'Clients',CamelCaseName)
        if os.path.isdir(copy_folder):
            shutil.rmtree(copy_folder,ignore_errors=True)
        # TODO: Ignore Node Modules in prod 
        shutil.copytree(template_folder,copy_folder)
        # shutil.copytree(template_folder,copy_folder,ignore=shutil.ignore_patterns('node_modules*'))
        self.HandleAngular6SsrAuth(client_options,copy_folder)
        self.HandleDockerfileForAngularSsr(client_options,copy_folder)

        docker_config = self.HandleDockerComposeForAngularSsr(client_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(client_options['name'], docker_config)
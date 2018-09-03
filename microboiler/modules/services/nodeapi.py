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


class NodeApi(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        self.csharp_templater = Csharp(projectOptions,project_templates_paths,outputPath)
        super().__init__(projectOptions, project_templates_paths, outputPath)

    
    def HandleNodeWebApi(self, api_service_options):
        CamelCaseName = to_camelcase(api_service_options['name'])        
        apiServicesPath = os.path.join(self.project_templates_paths,'api_services')
        api_template_folder = os.path.join(apiServicesPath,'express_web_api')
        srcDir = os.path.join(self.outputPath,'src')
        api_copy_folder = os.path.join(srcDir,'ApiServices',CamelCaseName)
        if os.path.isdir(api_copy_folder):
            shutil.rmtree(api_copy_folder,ignore_errors=True)
        # TODO: Swap shutil operations
        #shutil.copytree(api_template_folder,api_copy_folder,ignore=shutil.ignore_patterns('node_modules*'))
        shutil.copytree(api_template_folder,api_copy_folder)
        
        self.HandleNodeJsData(api_service_options,api_copy_folder)
        self.HandleNodeJsAuthorization(api_service_options,api_copy_folder)

        docker_config = self.HandleNodeJsDockerOptions(api_service_options,api_copy_folder)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(api_service_options['name'], docker_config)

    def HandleNodeJsData(self, api_service_options,api_copy_folder):
        app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
        env_file_path = os.path.join(api_copy_folder,'src','.env')
        models_folder_path =  os.path.join(api_copy_folder,'src','models')
        package_json_file_path =  os.path.join(api_copy_folder,'src','package.json')
        db_entity_route_file_path =  os.path.join(api_copy_folder,'src','controllers','entity.js')
        mongo_db_packages = ['mongoose']
        database_enabled = 'database' in api_service_options
        if (database_enabled):        
            database_provider = api_service_options['database']['provider']
            database_instance = FindDatabaseWithName(self.projectOptions, database_provider)
            if database_instance['type'] == 'mongodb':
                connection_string, connection_string_dev = GetConnectionString(api_service_options, database_instance)
                replace_dict = {
                    '{{mongoose_connection_dev}}': connection_string_dev,
                    '{{mongoose_connection}}': connection_string
                }
                replace_template_file(app_js_file_path,replace_dict)
                filter_sub_region(app_js_file_path,'database',database_instance['type'])
            else:
                RemovePackagesFromJson(package_json_file_path,mongo_db_packages)
                if os.path.isfile(db_entity_route_file_path):
                    os.remove(db_entity_route_file_path)
        else:        
            filter_region_with_tag(app_js_file_path,'database')
            if os.path.isdir(models_folder_path):
                shutil.rmtree(models_folder_path,ignore_errors=True)    
            RemovePackagesFromJson(package_json_file_path,mongo_db_packages)
    def HandleNodeJsAuthorization(self,api_service_options,api_copy_folder):
        app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
        env_file_path = os.path.join(api_copy_folder,'src','.env')
        authorize_middleware_file_path = os.path.join(api_copy_folder,'src','middlewares','authorize.js')
        package_json_file_path =  os.path.join(api_copy_folder,'src','package.json')
        auth_test_route_file_path =  os.path.join(api_copy_folder,'src','controllers','authtest.js')
        authorization_enabled = 'authorization' in api_service_options
        if (authorization_enabled):
            identity_instance = FindIdentityServiceWithName(self.projectOptions, api_service_options['authorization']['issuer'])
            identity_instance_type = identity_instance['type']
            if identity_instance_type == 'identityserver4':
                # Filter App.js For authorization:identityserver4
                filter_sub_region(app_js_file_path,'database',identity_instance_type)
                # Configure authorize middleware
                replace_dict = {
                    '{{issuer_host_dev}}': str.lower(identity_instance['name'])+'.localhost',
                    '{{issuer_host}}': 'http://localhost:'+str(identity_instance['port'])
                }
                if 'secrets' in api_service_options['authorization']:
                    if len(api_service_options['authorization']['secrets']) > 0:
                        replace_dict['{{api_secret}}'] = api_service_options['authorization']['secrets'][0]
                    else:
                        replace_dict['{{api_secret}}'] = 'secret'
                else:
                    replace_dict['{{api_secret}}'] = 'secret'
                replace_template_file(authorize_middleware_file_path,replace_dict)
        else:
            # Filter App.py For Authorization
            filter_region_with_tag(app_js_file_path,'authorization')
            # Remove authorize middleware file
            if os.path.isfile(authorize_middleware_file_path):
                os.remove(authorize_middleware_file_path)
    def HandleNodeJsDockerOptions(self,api_service_options,api_copy_folder):
        dockerfile_path = os.path.join(api_copy_folder,'src','Dockerfile')
        CamelCaseName = to_camelcase(api_service_options['name'])
        replace_dict = {}
        if 'port' in api_service_options:
            replace_dict['{{PORT}}'] =  str(api_service_options['port'])
        replace_template_file(dockerfile_path,replace_dict)
        docker_options = {
            'image': api_service_options['name'].lower(),
            'build': {
                'context': 'src/ApiServices/'+CamelCaseName+'/src',
                'dockerfile': 'Dockerfile'
            },
            'networks': ['localnet'],
            'ports': []
            
        }
        if 'port' in api_service_options:
            docker_options['ports'].append(str(api_service_options['port'])+':'+str(api_service_options['port']))
        if 'docker_compose_override' in api_service_options:
            docker_options.update(api_service_options['docker_compose_override'])  
        return docker_options
    
from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
from microboiler.modules.databases.redis import BuildRedisConnectionString
from microboiler.modules.utils.utils import (InDbQ,to_camelcase,
    FindClientWithName,
    FindDatabaseWithName,
    FindEventBusWithName,
    FindIdentityServiceWithName,
    FindServerWithName,
    FindAllFilesWithExtensionInDirectory,
    GetDatabaseUsernameAndPassword)

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
        """
        ⚝ Handling Nodejs Express Web Api
        ① Get CamelCase name for renaming output project folder
        ② Copy from template to output dir
        ③ Handle Data, Authorization
        ④ Add to docker-compose and configure Dockerfile
        ⑤ Clear folders for region tags
        """
        #1dawda
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
        #3
        self.HandleNodeJsData(api_service_options,api_copy_folder)
        self.HandleNodeJsAuthorization(api_service_options,api_copy_folder)
        #4
        docker_config = self.HandleNodeJsDockerOptions(api_service_options,api_copy_folder)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(api_service_options['name'], docker_config)
        #5
        app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
        ClearRegionLines([app_js_file_path])

    def HandleNodeJsData(self, api_service_options,api_copy_folder):

        """
        ⚝ If Database not enabled
            ① remove all relevant packages from packages.json
            ② filter app.js between (database) tag
            ③ remove models created for mongoose
            ④ remove data folder (sequelize)
            ⑤
            ⑥
            ⑦
            ⑧
            ⑨
            ⑩
        ⚝ If Database is enabled
            ⚝ If Database is mongodb
                ① remove all other database packages(sequelize) from packages.json
                ② filter app.js between (database) tag which is not subtagged mongodb
                ③ set connection strings in app.js
                ④ remove data folder of sequelize
                ⑤ remove controllers of sequelize data entpoints⑦
                ⑧
                ⑨
                ⑩
            ⚝ If Database is postgre or mysql or sqlite
                ① remove all other database packages(mongoose) from packages.json
                ② filter app.js between (database) tag which is not subtagged postgre,sqlite,mysql
                ③ set connection strings in .env file
                ④ remove relevant file/folders for mongodb
                ⑤ remove controllers of mongodb data entpoints
                ⑥ remove .sequelizerc file
                ⑦
                ⑧
                ⑨
                ⑩
        """

        app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
        env_file_path = os.path.join(api_copy_folder,'src','.env')
        models_folder_path =  os.path.join(api_copy_folder,'src','models')
        package_json_file_path =  os.path.join(api_copy_folder,'src','package.json')
        db_entity_route_file_path =  os.path.join(api_copy_folder,'src','controllers','entity.js')
        postgre_entity_folder = os.path.join(api_copy_folder,'src','postgre')
        mongo_db_packages = ['mongoose']
        sequelize_db_packages = ['sequelize']
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
                RemovePackagesFromJson(package_json_file_path, mongo_db_packages)
                if os.path.isfile(db_entity_route_file_path):
                    os.remove(db_entity_route_file_path)
            if database_instance['type'] == 'postgresql' or database_instance['type'] == 'mysql':
                username,password = GetDatabaseUsernameAndPassword(database_instance)
                env_replace_dict = {
                    '{{database:host}}': api_service_options['database']['database_name'],
                    '{{database:user}}': username,
                    '{{database:password}}': password
                }
                replace_template_file(env_file_path,env_replace_dict)
            else:
                RemovePackagesFromJson(package_json_file_path, sequelize_db_packages)
                sequelizerc_file_path = os.path.join(api_copy_folder,'src','.sequelizerc')
                if os.path.isfile(sequelizerc_file_path):
                    os.remove(sequelizerc_file_path)
                if os.path.isdir(postgre_entity_folder):
                    shutil.rmtree(postgre_entity_folder)
        else:        
            filter_region_with_tag(app_js_file_path,'database')
            if os.path.isdir(models_folder_path):
                shutil.rmtree(models_folder_path,ignore_errors=True)    
            RemovePackagesFromJson(package_json_file_path,mongo_db_packages+sequelize_db_packages)
    def HandleNodeJsAuthorization(self,api_service_options,api_copy_folder):
        """
        ⚝ If authorization not enabled
            ① filter between //& region (authorization) in files [app.js]
            ② remove authorize middleware file
            ③ remove relevant packages from package.json
            ④ remove auth test controller
        ⚝ If authorization enabled:
            ① filter App.js For authorization:{identity_provider}
            ② replace relevant configuration in authorize middleware file
        """
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
            if os.path.isfile(auth_test_route_file_path):
                os.remove(auth_test_route_file_path)
    def HandleNodeJsDockerOptions(self,api_service_options,api_copy_folder):
        """
        ⚝ Configuring docker-compose options
            ① set port and replace in dockerfile
            ② if docker_compose_override is set, override default config
        """
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
    
#pylint: disable-msg=W0612

import readline
import fileinput
import argparse
import re
import shlex
import json
import shutil
import yaml
import os
import sys
import nginx
# end

from modules.servers.nginx import Nginx

# global
projectOptions = {}

scriptPath = os.path.dirname(os.path.realpath(sys.argv[0])),
templatesPath = os.path.normpath(os.path.join(scriptPath,'templatefiles')),
project_templates_paths = {    
    
    'serversPath' : os.path.join(templatesPath,'servers'),
    'apiServicesPath' : os.path.join(templatesPath,'api_services'),
    'clientsPath' : os.path.join(templatesPath,'clients'),
    'databasesPath' : os.path.join(templatesPath,'databases'),
    'eventbusPath' : os.path.join(templatesPath,'eventbus'),
    'identityServicesPath' : os.path.join(templatesPath,'identity_services')
}


optionsFilePath = ""
project_output_dir = ""
srcDir = ""

# end C# helpers
def CreateProjectDirectory(projectName, outputDir):
    print ("Scaffolding Project", projectName)
    directory = None
    if outputDir is None:
        directory = os.path.normpath(os.path.join(scriptPath, optionsFilePath,'../'))
    else:
        directory = os.path.normpath(os.path.join(os.getcwd(),outputDir))
    project_output_dir = os.path.normpath(os.path.join(directory, projectName))
    srcDir = os.path.normpath(os.path.join(project_output_dir,"src"))
    docker_volume_dir = os.path.normpath(os.path.join(project_output_dir,"docker_volumes"))
    if not os.path.isdir(srcDir):
        os.makedirs(srcDir)
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    # Create README.md
    f = open(os.path.normpath(os.path.join(project_output_dir,'README.md')), 'w+')
    f.write('#'+projectName)
    f.close()
    return project_output_dir, srcDir



    

def HandleServers(servers):
    print ('Configuring Servers')
    for server in servers:
        server_options = list(server.values())[0]
        print('Building'+ server_options['name'])
        if server_options['type'] == 'nginx':
            nginx_instance = Nginx(projectOptions,project_templates_paths,project_output_dir, server_options)
            nginx_instance.GenerateNginxInstance()




def HandleRedisDatabase(db_options):
    docker_volume_dir = os.path.normpath(os.path.join(project_output_dir,'docker_volumes','redis',db_options['name']))
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    redis_template_folder = os.path.join(databasesPath,'redis')
    redis_project_folder = os.path.join(project_output_dir, db_options['name'])
    if os.path.isdir(redis_project_folder):
        shutil.rmtree(redis_project_folder,ignore_errors=True)
    #Copy template (config and Dockerfile)
    shutil.copytree(redis_template_folder,redis_project_folder)
    redis_docker_options = {
        'image': db_options['name'].lower(),
        'build': {
            'context': db_options['name']+'/',
            'dockerfile': 'Dockerfile',
        },
        'container_name': db_options['name'],
        'ports':[],
        'restart': 'on-failure',
        'links':[],
        'depends_on':[],
        'networks': ['localnet'],
        'volumes': ['redis-volume:'+docker_volume_dir],
    }
    dockerOptions['volumes']['redis-volume'] = {}
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
    dockerOptions['services'][db_options['name']]= redis_docker_options

def HandleDatabases(databases):
    print ('Configuring Databases')
    for db in databases:
        db_options = list(db.values())[0]
        print('Scaffolding '+db_options['name'])
        if(db_options['type'] == 'postgresql'):
            HandlePostgreSql(db_options)
        if(db_options['type'] == 'mysql'):
            HandleMySql(db_options)
        elif db_options['type'] == 'redis':
            HandleRedisDatabase(db_options)
        elif db_options['type'] == 'mongodb':
            HandleMongoDb(db_options)


def HandleEventBus(eventbuses):
    print ('Configuring Bus Instances..')
    for evenbus in eventbuses:
        evenbus_options = list(evenbus.values())[0]
        print('Scaffolding '+evenbus_options['name'])
        if(evenbus_options['type'] == 'rabbitmq'):
            HandleRabbitMq(evenbus_options)




def HandleIdentityServices(identity_services):
    print ('Scaffolding Identity Services...')
    for i_service in identity_services:
        i_service_options = list(i_service.values())[0]
        if (i_service_options['type']=='identityserver4'):
            HandleIdentityServer4(i_service_options)

def HandleNodeJsData(api_service_options,api_copy_folder):
    app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
    env_file_path = os.path.join(api_copy_folder,'src','.env')
    models_folder_path =  os.path.join(api_copy_folder,'src','models')
    package_json_file_path =  os.path.join(api_copy_folder,'src','package.json')
    db_entity_route_file_path =  os.path.join(api_copy_folder,'src','controllers','entity.js')
    mongo_db_packages = ['mongoose']
    database_enabled = 'database' in api_service_options
    if (database_enabled):        
        database_provider = api_service_options['database']['provider']
        database_instance = FindDatabaseWithName(database_provider)
        if database_instance['type'] == 'mongodb':
            connection_string, connection_string_dev = BuildMongooseConnectionString(api_service_options, database_instance)
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
def HandleNodeJsAuthorization(api_service_options,api_copy_folder):
    app_js_file_path = os.path.join(api_copy_folder,'src','app.js')
    env_file_path = os.path.join(api_copy_folder,'src','.env')
    authorize_middleware_file_path = os.path.join(api_copy_folder,'src','middlewares','authorize.js')
    package_json_file_path =  os.path.join(api_copy_folder,'src','package.json')
    auth_test_route_file_path =  os.path.join(api_copy_folder,'src','controllers','authtest.js')
    authorization_enabled = 'authorization' in api_service_options
    if (authorization_enabled):
        identity_instance = FindIdentityServiceWithName(api_service_options['authorization']['issuer'])
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
def HandleNodeJsDocker(api_service_options,api_copy_folder):
    dockerfile_path = os.path.join(api_copy_folder,'Dockerfile')
    CamelCaseName = to_camelcase(api_service_options['name'])
    replace_dict = {}
    if 'port' in api_service_options:
        replace_dict['{{PORT}}'] =  str(api_service_options['port'])
    replace_template_file(dockerfile_path,replace_dict)
    docker_options = {
        api_service_options['name']:{
            'image': api_service_options['name'].lower(),
            'build': {
                'context': 'src/ApiServices/'+CamelCaseName+'/src',
                'dockerfile': 'Dockerfile'
            },
            'networks': ['localnet'],
            'ports': []
        }
    }
    if 'port' in api_service_options:
        docker_options[api_service_options['name']]['ports'].append(str(api_service_options['port'])+':'+str(api_service_options['port']))
    if 'docker_compose_override' in api_service_options:
        docker_options[api_service_options['name']].update(api_service_options['docker_compose_override'])  
    dockerOptions['services'][api_service_options['name']] = docker_options[api_service_options['name']]
def HandleNodeWebApi(api_service_options):
    CamelCaseName = to_camelcase(api_service_options['name'])
    api_template_folder = os.path.join(apiServicesPath,'express_web_api')
    api_copy_folder = os.path.join(srcDir,'ApiServices',CamelCaseName)
    if os.path.isdir(api_copy_folder):
        shutil.rmtree(api_copy_folder,ignore_errors=True)
    # TODO: Swap shutil operations
    #shutil.copytree(api_template_folder,api_copy_folder,ignore=shutil.ignore_patterns('node_modules*'))
    shutil.copytree(api_template_folder,api_copy_folder)
    
    HandleNodeJsData(api_service_options,api_copy_folder)
    HandleNodeJsAuthorization(api_service_options,api_copy_folder)
    HandleNodeJsDocker(api_service_options,api_copy_folder)
def HandleApiServices(api_services):
    print ('Scaffolding Api Services')
    for api_service in api_services:
        api_service_options = list(api_service.values())[0]
        if(api_service_options['type']=='dotnet_web_api'):
            HandleDotnetApiService(api_service_options)
        if(api_service_options['type']=='node_web_api'):
            HandleNodeWebApi(api_service_options)

def HandleNodeEnvironmentForAuthConfig(client_options, copy_folder):
    
    environment_dev_path = os.path.join(copy_folder,'src','environments','environment.ts')
    environment_prod_path = os.path.join(copy_folder,'src','environments','environment.prod.ts')
    # filter if auth not added
    if 'authorization' not in client_options:    
        filter_region_with_tag(environment_dev_path,'authorization')
        filter_region_with_tag(environment_prod_path,'authorization')
    else:
        identity_instance = FindIdentityServiceWithName(client_options['authorization']['issuer'])
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
def HandleDockerfileForAngularSsr(client_options, copy_folder):
    dockerfile_path = os.path.join(copy_folder,'Dockerfile')
    replace_dict = {
        '{{PORT}}': str(client_options['port'])
    }
    replace_template_file(dockerfile_path,replace_dict)
def HandleDockerComposeForAngularSsr(client_options):
    CamelCaseName = to_camelcase(client_options['name'])
    docker_options = {
        client_options['name']:{
            'image': client_options['name'].lower(),
            'build': {
                'context': 'src/Clients/'+CamelCaseName,
                'dockerfile': 'Dockerfile'
            },
            'networks': ['localnet'],
            'ports': []
        }
    }
    if 'port' in client_options:        
        docker_options[client_options['name']]['ports'].append(str(client_options['port'])+':'+str(client_options['port']))
    dockerOptions['services'][client_options['name']] = docker_options[client_options['name']]
def HandleAngular6SsrAuth(client_options, copy_folder):
    HandleNodeEnvironmentForAuthConfig(client_options, copy_folder)
    HandleDockerfileForAngularSsr(client_options,copy_folder)
    HandleDockerComposeForAngularSsr(client_options)
def HandleAngular6SsrClient(client_options):
    CamelCaseName = to_camelcase(client_options['name'])
    template_folder = os.path.join(clientsPath,'angular','cli_6_ssr')
    copy_folder = os.path.join(srcDir,'Clients',CamelCaseName)
    if os.path.isdir(copy_folder):
        shutil.rmtree(copy_folder,ignore_errors=True)
    # TODO: Ignore Node Modules in prod 
    shutil.copytree(template_folder,copy_folder)
    # shutil.copytree(template_folder,copy_folder,ignore=shutil.ignore_patterns('node_modules*'))
    HandleAngular6SsrAuth(client_options,copy_folder)

def HandleClients(clients):
    print ('Scaffolding Clients')
    for client in clients:
        client_options = list(client.values())[0]
        if(client_options['type']=='angular_cli_6_ssr'):
            HandleAngular6SsrClient(client_options)  
def DockerComposeFinalization(file):
    replace_dict = {
        'rabbitmq:healtcheck': '["CMD", "curl", "-f", "http://localhost:15672"]'
    }
    replace_template_file(file,replace_dict)
print('Enter a command')
print('To get help, enter `help`.')
while True:
    cmd, *args = shlex.split(input('> '))
    outputDir = None
    if cmd=='boile':
        optionsFilePath = args[0]
        if len(args) is 3:
            if args[1] == '-o' or args[1] == '--output':
                if args[2] is not None:
                    outputDir = args[2]
                else:
                    print ('Output Path did not specified.')
        if optionsFilePath is None:
            print('Plaese Provide a config file path')
            print ('Ex: boile example-config.yml')
            exit
        with open(optionsFilePath, 'r') as stream:
            try:
                # Load Yaml
                projectOptions = yaml.load(stream)
                if not ('name' in projectOptions):
                    print('Please Provide a valid project name')
                    exit
                projectName = projectOptions['name']
                # Create Project Files
                project_output_dir, srcDir = CreateProjectDirectory(projectName, outputDir)

                # Create Servers (Nginx Apache)
                if('servers' in projectOptions):
                    HandleServers(projectOptions['servers'])

                # Create Databases (Postgre, Mysql, Redis)
                if('databases' in projectOptions):
                    HandleDatabases(projectOptions['databases'])
                    
                # Configure Eventbus Instances (Rabbitmq)
                if('eventbus' in projectOptions):
                    HandleEventBus(projectOptions['eventbus'])

                # Create and configure identity_services
                if('identity_services' in projectOptions):
                    HandleIdentityServices(projectOptions['identity_services'])

                # Create and configure api_serviecs
                if('api_services' in projectOptions):
                    HandleApiServices(projectOptions['api_services'])
                # Create and configure clients
                if('clients' in projectOptions):
                    HandleClients(projectOptions['clients'])

                docker_compose_path = os.path.join(project_output_dir,'docker-compose.yml')
                with open(docker_compose_path, 'w') as yaml_file:
                    yaml.dump(dockerOptions, yaml_file, default_flow_style=False)
                DockerComposeFinalization(docker_compose_path)
                print('!! In case you generated .NET Core Services')
                print ('Do not forget to set evironment variable ASPNETCORE_DEVELOPMENT To Development')
                              
                
            except yaml.YAMLError as exc:
                print('Error parsing yml document')
                print(exc)
            break

    if cmd=='exit':
        break

    elif cmd=='help':
        print('See Github Documentation :))')

    else:
        print('Unknown command: {}'.format(cmd))


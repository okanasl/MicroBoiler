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
def HandleDotnetApiCsproj(dotnet_service, api_copy_folder):
    print ('Handle DotnetApi Csproj File')
    api_csproj_path = os.path.join(api_copy_folder,
        'src',
        to_camelcase(dotnet_service['name'])+'.csproj')
    # Handle Host Application
    HandleCsprojLogging(dotnet_service,api_csproj_path)
    HandleCsprojDatabase(dotnet_service,api_csproj_path)
    HandleCsprojEventbus(dotnet_service,api_csproj_path)
def BuildConnStringForDotnetApi(dotnet_options):
    database_instance_name = dotnet_options['database']['provider']
    database_instance = FindDatabaseWithName(database_instance_name)
    database_type = database_instance['type']
    connection_string ='' 
    user = 'doom'
    password = 'machine'
    if database_type=='mysql' or database_type=='postgresql':
        if 'username' in database_instance:
            user = database_instance['username']
        if 'password' in database_instance:
            password = database_instance['password']    
    connection_string, connection_string_dev = BuildDatabaseConnectionString(database_type,database_instance['name'],dotnet_options['name'],user,password)        
    
    return connection_string , connection_string_dev

def HandleDotnetApiStartup(dotnet_service, api_copy_folder):
    print ('Handle DotnetApi Startup.cs File')
    api_startup_path = os.path.join(api_copy_folder,
        'src',
        'Startup.cs')
    
    HandleCSharpDatabase(dotnet_service,api_startup_path)
    HandleCSharpCache(dotnet_service,api_startup_path)
    HandleCSharpEventbus(dotnet_service,api_startup_path)
    HandleCSharpLogging(dotnet_service,api_startup_path)
    HandleCSharpServer(dotnet_service,api_startup_path)
    HandleCSharpSwagger(dotnet_service,api_startup_path)
    # Set DBContext Name
    CamelCaseName = to_camelcase(dotnet_service['name'])
    replaceDict = {
        'NameContext': CamelCaseName.replace('.','') + 'Context'    
    }
    if 'database' in dotnet_service:
        database_instance = FindDatabaseWithName(dotnet_service['database']['provider'])
        conn_string, conn_string_dev = BuildConnStringForDotnetApi(dotnet_service)
        replaceDict['{{database:connectionString}}'] = conn_string
        replaceDict['{{database:connectionString-dev}}'] = conn_string_dev
    if 'cache' in dotnet_service:
        if dotnet_service['cache']['type'] == 'redis':
            redis_instance = FindDatabaseWithName(dotnet_service['cache']['redis_options']['redis_server'])
            if redis_instance is None:
                print ('Warning: Redis instance could not found. Configuration left default')
            else:
                redis_conn_string, redis_conn_string_dev = BuildRedisConnectionString(redis_instance)
                replaceDict['{{redis_options:connection}}'] = redis_conn_string
                replaceDict['{{redis_options:connection-dev}}'] = 'localhost:6379'
                if 'redis_instance_name' in dotnet_service['cache']['redis_options']:
                    replaceDict['{{redis_options:instance_name}}'] = dotnet_service['cache']['redis_options']['redis_instance_name']
    if 'authorization' in dotnet_service:
        issuer = dotnet_service['authorization']['issuer']
        if issuer is None:
            print ('Error: Identity Issuer for '+dotnet_service['name']+' is required')
        identity_instance = FindIdentityServiceWithName(issuer)
        if identity_instance is None:
            print ('Error: Identity Service Instance for '+dotnet_service['name']+' could not found')
        else:
            replaceDict['{{authorization:api_name}}'] = dotnet_service['name']        
            replaceDict['{{authorization:authority}}'] = str.lower(identity_instance['name'])+'.localhost'
            replaceDict['{{authorization:authority-dev}}'] = 'http://localhost:'+str(identity_instance['port'])
            if 'api_secret' in dotnet_service['authorization']:
                replaceDict['{{authorization:api_secret}}'] = dotnet_service['authorization']['secrets'][0]
            else:
                # Set Default Secret
                replaceDict['{{authorization:api_secret}}'] = 'secret'

    replace_template_file(api_startup_path,replaceDict)

def HandleDotnetApiProgramFile(dotnet_service, api_copy_folder):
    api_program_path = os.path.join(api_copy_folder,
        'src',
        'Program.cs')

    HandleCSharpLogging(dotnet_service,api_program_path)
def HandleDotnetApiDbContext(dotnet_service, api_copy_folder):
    dbcontext_path = os.path.join(api_copy_folder,
        'src',
        'Data',
        'NameContext.cs')
    CamelCaseDbName = to_camelcase(dotnet_service['name']).replace('.','') + 'Context'
    if 'database' in dotnet_service:
        if os.path.exists(dbcontext_path):
            dbcontext_rename_path = os.path.join(api_copy_folder,
                'src',
                'Data',
                CamelCaseDbName+'.cs')
            shutil.copy(dbcontext_path, dbcontext_rename_path)
            os.remove(dbcontext_path)
            replaceDict = {
                'NameContext': CamelCaseDbName
            }
            replace_template_file(dbcontext_rename_path,replaceDict)
    else:
        remove_data_folder_path = os.path.join(api_copy_folder,
            'src',
            'Data')
        shutil.rmtree(remove_data_folder_path)
        rm_files = ['migrations.sh','updatedb.sh','dropdb.sh','migrations.dev.sh','updatedb.dev.sh','dropdb.dev.sh']
        for rm_file in rm_files:
            rm_path = os.path.join(api_copy_folder,rm_file)
            os.remove(rm_path)
        docker_file = os.path.join(api_copy_folder,
            'Dockerfile')
        filter_region_with_tag(docker_file,'database')
# Change Namespace To Service Name 
# extensions: Tuple

def ReplaceDotnetNameSpaces(file_paths, namespace_name, replace_name):
    replace_dict = {}
    replace_dict[namespace_name] = replace_name
    for file in file_paths:
        if os.path.exists(file):
            replace_template_file(file,replace_dict)

# Remove Region Tags
def HandleDotnetApiNameSpaceAndCleaning(dotnet_service, api_copy_folder):
    src_path = os.path.join(api_copy_folder,'src')
    file_clean_paths = FindAllFilesWithExtensionInDirectory(src_path,('.cs','.csproj'))
    CamelCaseServiceName = to_camelcase(dotnet_service['name'])
    ReplaceDotnetNameSpaces(file_clean_paths,'DotnetWebApi',CamelCaseServiceName)
    ClearRegionLines(file_clean_paths)
def HandleDotnetApiDockerFile(dotnet_service, api_copy_folder):
    docker_file_path = os.path.join(api_copy_folder,'Dockerfile')
    docker_replace_dict = {}
    docker_replace_dict['{{port}}'] = str(dotnet_service['port'])
    docker_replace_dict['{{project_name}}'] = to_camelcase(dotnet_service['name'])
    replace_template_file(docker_file_path,docker_replace_dict)
    if 'database' in dotnet_service:
        ef_shell_replace_dict = {
            '{{ProjectName}}' : to_camelcase(dotnet_service['name']),
            '{{DatabaseContextName}}' : to_camelcase(dotnet_service['name']).replace('.','') + 'Context'
        }
        shell_file_paths = ['migrations.sh','updatedb.sh','dropdb.sh','migrations.dev.sh','updatedb.dev.sh','dropdb.dev.sh']
        for path in shell_file_paths:
            f_path = os.path.join(api_copy_folder,path)
            replace_template_file(f_path,ef_shell_replace_dict)

def HandleDotnetApiDockerCompose(dotnet_service,api_copy_folder):
    docker_props = {
        'image': dotnet_service['name'].lower(),
        'build': {
            'context': 'src/ApiServices/'+to_camelcase(dotnet_service['name'])+'/',
            'dockerfile': 'Dockerfile'
        },
        'restart': 'on-failure',
        'ports': [],
        'links': [],
        'depends_on':[],
        'networks':['localnet'],        
    }
    if 'database' in dotnet_service:
        docker_props['links'].append(dotnet_service['database']['provider'])
        docker_props['depends_on'].append(dotnet_service['database']['provider'])
    if 'port' in dotnet_service:
        docker_props['ports'].append(str(dotnet_service['port'])+':'+str(dotnet_service['port']))
    eventbus_enabled = 'eventbus' in dotnet_service
    if eventbus_enabled:
        eb_provider = dotnet_service['eventbus']['provider']        
        docker_props['links'].append(eb_provider)
        docker_props['depends_on'].append(eb_provider)

    dockerOptions['services'][dotnet_service['name']] = docker_props
def HandleDotnetApiService(api_service_options):
    CamelCaseName = to_camelcase(api_service_options['name'])
    api_template_folder = os.path.join(apiServicesPath,'dotnet_web_api','src')
    api_copy_folder = os.path.join(srcDir,'ApiServices',CamelCaseName )
    if os.path.isdir(api_copy_folder):
        shutil.rmtree(api_copy_folder,ignore_errors=True)
    # TODO: Swap shutil operations
    #shutil.copytree(api_template_folder,api_copy_folder,ignore=shutil.ignore_patterns('bin*','obj*'))
    shutil.copytree(api_template_folder,api_copy_folder)
    api_src_folder = os.path.join(srcDir,'ApiServices',CamelCaseName,'DotnetWebApi')
    api_src_rename_folder = os.path.join(srcDir,'ApiServices',CamelCaseName,'src')
    api_csproj_folder = os.path.join(srcDir,'ApiServices',CamelCaseName,'src','DotnetWebApi.csproj')
    api_csproj_rename_folder = os.path.join(srcDir,'ApiServices',CamelCaseName,'src',CamelCaseName+'.csproj')
    
    if not os.path.isdir(api_src_rename_folder):
        shutil.copytree(api_src_folder,api_src_rename_folder)
        shutil.rmtree( api_src_folder,ignore_errors=True)
    else: 
        shutil.rmtree( api_src_rename_folder,ignore_errors=True)
        shutil.copytree(api_src_folder,api_src_rename_folder)

    if not os.path.exists(api_csproj_rename_folder):
        shutil.copy(api_csproj_folder,api_csproj_rename_folder)
        os.remove( api_csproj_folder)
    else: 
        os.remove(api_csproj_rename_folder)
        shutil.copy(api_csproj_folder,api_csproj_rename_folder)


    HandleDotnetApiCsproj(api_service_options,api_copy_folder)
    HandleDotnetApiStartup(api_service_options,api_copy_folder)
    HandleDotnetApiProgramFile(api_service_options,api_copy_folder)
    HandleDotnetApiDbContext(api_service_options,api_copy_folder)
    HandleDotnetApiNameSpaceAndCleaning(api_service_options,api_copy_folder)
    HandleDotnetApiDockerFile(api_service_options,api_copy_folder)
    HandleDotnetApiDockerCompose(api_service_options,api_copy_folder)
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


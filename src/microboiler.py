#pylint: disable-msg=W0612

import readline
import fileinput
import re
import shlex
import json
import shutil
import yaml
import os
import sys
import nginx
# declare script scope
dotnet_logging_types = ['microsoft','serilog']
database_types = ['postgresql','mysql','mssql']
# end
# global
projectOptions = {}
rememberize = {}
scriptPath = os.path.dirname(os.path.realpath(sys.argv[0]))
templatesPath = os.path.normpath(os.path.join(scriptPath,'templatefiles'))
serversPath = os.path.join(templatesPath,'servers')
apiServicesPath = os.path.join(templatesPath,'api_services')
clientsPath = os.path.join(templatesPath,'clients')
databasesPath = os.path.join(templatesPath,'databases')
eventbusPath = os.path.join(templatesPath,'eventbus')
identityServicesPath = os.path.join(templatesPath,'identity_services')

dockerOptions = {'version' : "3", 'services': {},'volumes':{} ,'networks':{'localnet':{'driver':'bridge'}}}
optionsFilePath = ""
projectDir = ""
srcDir = ""
# end global

# helpers
def InDbQ(value):
    return '\"'+value+'\"'
def to_camelcase(s):
    s_val = re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)
    return s_val[0].upper()+s_val[1:]
def replace_template_file(filepath,replace_dict):
    with open(filepath,'r') as cs_file:
        cs_content = cs_file.read()
    os.remove(filepath)
    for key, value in replace_dict.items():
        cs_content = cs_content.replace(key,value)
    with open(filepath,'w') as cs_file_new:
        cs_file_new.write(cs_content)
def filter_region_with_tag(file,tag):
    with open(file, 'r+') as f:
        filtered = list(filter_region(f, 'region ('+tag+')', 'end ('+tag+')'))
        f.seek(0)
        f.writelines(filtered)
        f.truncate()
def filter_region(file, start_delete_key, stop_delete_key):
    """
    Given a file handle, generate all lines except those between the specified
    regions.
    """
    lines = iter(file)
    try:
        while True:
            line = next(lines)
            if start_delete_key in line and ':all' not in line:
                # Discard all lines up to and including the stop marker
                while stop_delete_key not in line:
                    line = next(lines)
                line = next(lines)            
            yield line
    except StopIteration:
        return
def filter_sub_region(
    file,
    parent_marker,
    child_marker):
    lines = iter(file)
    parent_marker_start = 'region ('+parent_marker+':'
    child_marker_start = 'region ('+parent_marker+':'+child_marker
    child_marker_end = 'end ('+parent_marker+':'+child_marker      
    parent_marker_end = 'end ('+parent_marker+':'
    try:
        while True:
            line = next(lines)
            if parent_marker_start in line and child_marker not in line:
                while parent_marker_end not in line:
                    line = next(lines)
            yield line
    except StopIteration:
        return
def Clear_File_Region_Marks(file):
    lines = iter(file)
    region_marks = ['//& region','<!-- region','//& end','<!-- end']
    re_lines = []
    try:
        for line in lines:
            found = False
            for mark in region_marks:
                if mark in line:
                    found = True
            if not found:
                yield line
        while True:
            line = next(lines)
            
    except StopIteration:
        return
def BuildMongooseConnectionString(api_options,mongodb_options):
    db_name = api_options['database']['database_name']
    db_host_dev = 'localhost'
    db_host = mongodb_options['name']
    db_username = mongodb_options['username']
    db_password = mongodb_options['password']
    conn_string = 'mongodb://{0}:{1}@{2}/{3}'.format(db_username,db_password,db_host,db_name)
    conn_string_dev=  'mongodb://{0}:{1}@{2}/{3}'.format(db_username,db_password,db_host_dev,db_name)
    return conn_string, conn_string_dev
def BuildDatabaseConnectionString(database_type,server_host,database_name,user,password):
    conn_string = ""
    conn_string_dev=""
    if(database_type == "mysql"):
        conn_string =  "Server={0};Database={1};Uid={2};Pwd={3};CharSet=utf8mb4;".format(server_host,database_name,user,password)
        conn_string_dev = "Server={0};Database={1};Uid={2};Pwd={3};CharSet=utf8mb4;".format('localhost',database_name,user,password)
    elif (database_type == 'postgresql'):
        conn_string ="Server={0};Database={1};Username={2};Password={3}".format(server_host,database_name,user,password)
        conn_string_dev = "Server={0};Database={1};Username={2};Password={3}".format('localhost',database_name,user,password)
    elif (database_type == 'mssql'):
        conn_string = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format(server_host,database_name,user,password)
        conn_string_dev = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format('localhost',database_name,user,password)
    elif (database_type == 'mssql'):
        conn_string = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format(server_host,database_name,user,password)
        conn_string_dev = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format('localhost',database_name,user,password)
    return conn_string, conn_string_dev
def BuildRedisConnectionString(redis_options):
    return redis_options['name'], '127.0.0.1'
def RemovePackagesFromJson(file,packages):
    with open(file) as f:
        package_info = json.load(f)
        for package in packages:
            package_info['dependencies'].pop(package, None)
        f.seek(0)
        json.dump(package_info,f)
# end helpers
# service helpers

def FindClientWithName(name):
    clients = projectOptions['clients']
    for client in clients:
        if list(client.values())[0]['name'] == name:
            return list(client.values())[0]
def FindIdentityServiceWithName(name):
    identity_services = projectOptions['identity_services']
    for i_s in identity_services:
        if list(i_s.values())[0]['name'] == name:
            return list(i_s.values())[0]
def FindDatabaseWithName(name):
    database_instances = projectOptions['databases']
    for db in database_instances:
        if list(db.values())[0]['name'] == name:
            return list(db.values())[0]
def FindEventBusWithName(name):
    eventbus_instances = projectOptions['eventbus']
    for bus in eventbus_instances:
        if list(bus.values())[0]['name'] == name:
            return list(bus.values())[0]
def FindServerWithName(name):
    server_instances = projectOptions['servers']
    for server in server_instances:
        if list(server.values())[0]['name'] == name:
            return list(server.values())[0] 
# end service helpers
# start .csproj helpers
def HandleCsprojLogging(logging_service, host_csproj_path):
    logging_enabled = 'logging' in logging_service
    if logging_enabled:
        if 'type' not in logging_service['logging']:
            logging_type = 'serilog'
        else:
            logging_type = 'microsoft'
    if(logging_enabled):
        with open(os.path.join(host_csproj_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'logging',logging_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        logging_type_start_line = 'region (logging)'
        logging_type_end_line = 'end (logging)'
        with open(os.path.join(host_csproj_path), 'r+') as f:
                filtered = list(filter_region(f, logging_type_start_line, logging_type_end_line))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCsprojDatabase(service_options, host_csproj_path):
    database_enabled = 'database' in service_options
    
    if(database_enabled):
        database_instance = FindDatabaseWithName(service_options['database']['provider'])
        if database_instance is None:
            print ('Could not found database with name'+service_options['database']['provider'])
        database_type = database_instance['type']
        with open(os.path.join(host_csproj_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'database',database_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(host_csproj_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (database)', 'end (database)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCsprojEventbus(service_options, host_csproj_path):
    eventbus_enabled = 'eventbus' in service_options
    
    if(eventbus_enabled):
        eventbus_instance = FindEventBusWithName(service_options['eventbus']['provider'])

        eventbus_type = eventbus_instance['type']
        with open(os.path.join(host_csproj_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'eventbus',eventbus_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(host_csproj_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (eventbus)', 'end (eventbus)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
# end csproj helpers
# start C# helpers
def HandleCSharpLogging(logging_service, sharp_file_path):
    logging_enabled = 'logging' in logging_service
    if logging_enabled:
        if 'type' not in logging_service['logging']:
            logging_type = 'serilog'
        else:
            logging_type = 'microsoft'
    if(logging_enabled):
        with open(os.path.join(sharp_file_path), 'r+') as f:
            filtered = list(filter_sub_region(f,'logging',logging_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        logging_type_start_line = 'region (logging)'
        logging_type_end_line = 'end (logging)'
        with open(os.path.join(sharp_file_path), 'r+') as f:
                filtered = list(filter_region(f, logging_type_start_line, logging_type_end_line))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCSharpDatabase(service_options, sharp_file_path):
    database_enabled = 'database' in service_options
    
    if(database_enabled):
        database_instance = FindDatabaseWithName(service_options['database']['provider'])
        database_type = database_instance['type']
        with open(os.path.join(sharp_file_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'database',database_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(sharp_file_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (database)', 'end (database)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCSharpCache(service_options, sharp_file_path):
    cache_enabled = 'cache' in service_options
    
    if(cache_enabled):
        cache_type = service_options['cache']['type']
        with open(os.path.join(sharp_file_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'cache',cache_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(sharp_file_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (cache)', 'end (cache)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCSharpServer(service_options,sharp_file_path):
    server_enabled = 'server' in service_options
    if(server_enabled):
        server_instance = FindServerWithName(service_options['server']['provider'])
        server_type = server_instance['type']
        with open(os.path.join(sharp_file_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'server',server_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(sharp_file_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (server)', 'end (server)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
def HandleCSharpSwagger(dotnet_service, sharp_file_path):
    is_swagger_in_config = 'swagger' in dotnet_service
    if(is_swagger_in_config):
        swagger_enabled = dotnet_service['swagger']
        if not swagger_enabled:
            with open(os.path.join(sharp_file_path), 'r+') as f:
                    filtered = list(filter_region(f, 'region (swagger)', 'end (swagger)'))
                    f.seek(0)
                    f.writelines(filtered)
                    f.truncate()
def HandleCSharpEventbus(service_options, sharp_file_path):
    eventbus_enabled = 'eventbus' in service_options
    
    if(eventbus_enabled):
        eb_replace_dict = {}
        
        eventbus_instance = FindEventBusWithName(service_options['eventbus']['provider'])

        if eventbus_instance['type'] == 'rabbitmq':
            eb_replace_dict['{{rabbitmq:host}}'] = 'rabbitmq://'+eventbus_instance['name']
            eb_replace_dict['{{rabbitmq:host-dev}}'] = 'localhost'
            eb_replace_dict['{{rabbitmq:user:username}}'] = 'doom'
            eb_replace_dict['{{rabbitmq:user:password}}'] = 'machine'
            if 'docker_compose_override' in eventbus_instance:
                if 'envoronment' in eventbus_instance['docker_compose_override']:
                    eb_replace_dict['{{rabbitmq:user:username}}'] = eventbus_instance['docker_compose_override']['environment']['RABBITMQ_DEFAULT_USER']
                    eb_replace_dict['{{rabbitmq:user:password}}'] = eventbus_instance['docker_compose_override']['environment']['RABBITMQ_DEFAULT_PASSWORD']
        replace_template_file(sharp_file_path,eb_replace_dict)
        eventbus_type = eventbus_instance['type']
        with open(os.path.join(sharp_file_path), 'r+') as f:
            filtered = list(filter_sub_region(f, 'eventbus',eventbus_type))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    else:
        with open(os.path.join(sharp_file_path), 'r+') as f:
                filtered = list(filter_region(f, 'region (eventbus)', 'end (eventbus)'))
                f.seek(0)
                f.writelines(filtered)
                f.truncate()
# end C# helpers


def CreateProjectDirectory(projectName, outputDir):
    print ("Scaffolding Project", projectName)
    directory = None
    if outputDir is None:
        directory = os.path.normpath(os.path.join(scriptPath, optionsFilePath,'../'))
    else:
        directory = os.path.normpath(os.path.join(os.getcwd(),outputDir))
    projectDir = os.path.normpath(os.path.join(directory, projectName))
    srcDir = os.path.normpath(os.path.join(projectDir,"src"))
    docker_volume_dir = os.path.normpath(os.path.join(projectDir,"docker_volumes"))
    if not os.path.isdir(srcDir):
        os.makedirs(srcDir)
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    # Create README.md
    f = open(os.path.normpath(os.path.join(projectDir,'README.md')), 'w+')
    f.write('#'+projectName)
    f.close()
    return projectDir, srcDir

# Configure Nginx in docker-compose
def AddNginxToDockerOptions(server,api_services, clients,identity_services):
    nginxOptions = {        
            'image': 'nginxhttp',
            'container_name': server['name'].lower(),
            'ports': [],
            'links': [],
            'restart': 'on-failure',
            'depends_on':[],
            'networks': ['localnet'],
            'build': {'context': server['name']+'/', 'dockerfile':'Dockerfile'}        
    }
    if 'ports' in server:        
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
    
    dockerOptions['services'][server['name']]= nginxOptions

def BuildNginxConfiguration(server, api_services,clients, identity_services):
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
    

def FindApiServicesUsesNginx(serverName):
    services = []
    for service in projectOptions['api_services']:
        for key, value in service.items():
            if 'server' in value:
                if value['server']['provider'] == serverName:
                    services.append(value)
    return services
def FindClientsUsesNginx(serverName):
    clients = []
    for client in projectOptions['clients']:
        for key, value in client.items():            
            if 'server' in value:
                if value['server']['provider'] == serverName:
                    clients.append(value)
    return clients
def FindIdentityServicesUsesNginx(serverName):
    i_services = []
    for i_service in projectOptions['identity_services']:
        for key, value in i_service.items():            
            if 'server' in value:
                if value['server']['provider'] == serverName:
                    i_services.append(value)
    return i_services
def HandleServers(servers):
    print ('Configuring servers')
    for server in servers:
        server_options = list(server.values())[0]
        print('Scaffolding'+ server_options['name'])
        if server_options['type'] == 'nginx':
            nginxTemplateFolder = os.path.join(serversPath,'nginx')
            folderPath = os.path.normpath(os.path.join(projectDir, server_options['name']))
            nginxPath = os.path.join(folderPath,'nginx.conf')
            if os.path.isdir(folderPath):
                shutil.rmtree(folderPath, ignore_errors=True)
            shutil.copytree(nginxTemplateFolder,folderPath)
            api_services_uses_nginx = FindApiServicesUsesNginx(server_options['name'])
            clients_uses_nginx = FindClientsUsesNginx(server_options['name'])
            identity_uses_nginx = FindIdentityServicesUsesNginx(server_options['name'])
            nginxConfig = BuildNginxConfiguration(server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
            AddNginxToDockerOptions(server_options,api_services_uses_nginx, clients_uses_nginx,identity_uses_nginx)
            nginx.dumpf(nginxConfig, nginxPath)



def HandlePostgreSql(db_options):    
    docker_volume_dir = os.path.normpath(os.path.join(projectDir,'docker_volumes','postgresql',db_options['name']))
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    dockerOptions['volumes']['postgres-volume'] = {}
    default_postgre_options = {
        db_options['name']:{
            'image': 'postgres',
            'container_name': db_options['name'],
            'volumes': ['postgres-volume:'+docker_volume_dir],
            'networks':['localnet'],
            'ports': ['5432:5432'],
            'environment': {
                'POSTGRES_DB': 'dev',
            }
        }
    }
    
    if 'docker_compose_override' in db_options:
        default_postgre_options[db_options['name']].update(db_options['docker_compose_override'])  
    if 'username' in db_options:
        default_postgre_options[db_options['name']]['environment']['POSTGRES_USER'] = db_options['username']
    if 'password' in db_options:
        default_postgre_options[db_options['name']]['environment']['POSTGRES_PASSWORD'] = db_options['password']
    
    dockerOptions['services'][db_options['name']] = default_postgre_options[db_options['name']]

def HandleMySql(db_options):
    docker_volume_dir = os.path.normpath(os.path.join(projectDir,'docker_volumes','mysql',db_options['name']))
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    dockerOptions['volumes']['mysql-volume'] = {}
    default_mysql_options = {
        db_options['name']:{
            'image': 'mysql/mysql-server:5.7',
            'container_name': db_options['name'],
            'command': 'mysqld --user=root --verbose',
            'volumes': ['mysql-volume:'+docker_volume_dir],
            'networks':['localnet'],            
            'ports': ['3306:3306'],
            'environment': {
                'MYSQL_ROOT_HOST': '"%"',
                'MYSQL_ALLOW_EMPTY_PASSWORD': '"false"'
            }
        }
    }
    if 'docker_compose_override' in db_options:
        default_mysql_options[db_options['name']].update(db_options['docker_compose_override'])    
    if 'username' in db_options:
        default_mysql_options[db_options['name']]['environment']['MYSQL_USER'] = db_options['username']
    if 'password' in db_options:
        default_mysql_options[db_options['name']]['environment']['MYSQL_PASSWORD'] = db_options['password']
        default_mysql_options[db_options['name']]['environment']['MYSQL_ROOT_PASSWORD'] = db_options['password']
    dockerOptions['services'][db_options['name']] = default_mysql_options[db_options['name']]
def FindMongoUsingServiceNames(mongo_name):
    api_services = []
    if 'api_services' not in projectOptions:
        return api_services
    if len(projectOptions['api_services'])== 0:
        return api_services
    for service in projectOptions['api_services']:
        for key, value in service.items():            
            if 'database' in value:
                if value['database']['provider'] == mongo_name:
                    api_services.append(value['name'])
    return api_services
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
    docker_volume_dir = os.path.normpath(os.path.join(projectDir,'docker_volumes','redis',db_options['name']))
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    redis_template_folder = os.path.join(databasesPath,'redis')
    redis_project_folder = os.path.join(projectDir, db_options['name'])
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
def HandleMongoDb(db_options):
    mongo_docker_volume_dir = os.path.normpath(os.path.join(projectDir,'docker_volumes','mongodb',db_options['name']))
    if not os.path.isdir(mongo_docker_volume_dir):
        os.makedirs(mongo_docker_volume_dir)
    mongo_docker_options = {
        'image': db_options['name'].lower(),
        'container_name': db_options['name'],
        'volumes': ['mongodb-volume:'+mongo_docker_volume_dir],
        'ports':[],
        'restart': 'on-failure',
        'links':[],
        'depends_on':[],
        'networks': ['localnet']
    }
    dockerOptions['volumes']['mongodb-volume'] = {}
    # Add Ports
    if 'ports' in db_options:
        for port in db_options['ports']:
            mongo_docker_options['ports'].append(str(port)+':'+str(port))
    # Default Port if Not provided
    else:
         mongo_docker_options['ports'].append('"27017:27017"')
    mongo_using_services = FindMongoUsingServiceNames(db_options['name'])
    # Add Links So We can use mongo instance name to connect it in services
    for service_name in mongo_using_services:
        mongo_docker_options['links'].append(service_name)

    if 'docker_compose_override' in db_options:
        mongo_docker_options.update(db_options['docker_compose_override'])
    dockerOptions['services'][db_options['name']] = mongo_docker_options
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

def FindApiServicesUsesRabbitmq(rabbit_name):
    api_services = []
    for service in projectOptions['api_services']:
        for key, value in service.items():            
            if 'eventbus' in value:
                if value['eventbus']['provider'] == rabbit_name:
                    api_services.append(value['name'])
    return api_services

def FindIdentityServicesUsesRabbitmq(rabbit_name):
    i_services = []
    for service in projectOptions['identity_services']:
        for key, value in service.items():            
            if 'eventbus' in value:
                if value['eventbus']['provider'] == rabbit_name:
                    i_services.append(value['name'])
    return i_services

def HandleRabbitMq(rabbit_options):
    rabbit_api_services = FindApiServicesUsesRabbitmq(rabbit_options['name'])
    rabbit_identity_services = FindIdentityServicesUsesRabbitmq(rabbit_options['name'])
    docker_volume_dir = os.path.normpath(os.path.join(projectDir,'docker_volumes','rabbitmq',rabbit_options['name']))
    if not os.path.isdir(docker_volume_dir):
        os.makedirs(docker_volume_dir)
    dockerOptions['volumes']['rabbit-volume'] = {}
    rabbitmq_docker_options = {
        'image': 'rabbitmq:3-management-alpine',
        'container_name': rabbit_options['name'],
        'volumes': ['rabbit-volume:'+docker_volume_dir],
        'ports': ['15672:15672','5672:5672','5671:5671'], # Management, Publish And Subsucribe Ports
        'environment': {
            'RABBITMQ_DEFAULT_PASS':'machine',
            'RABBITMQ_DEFAULT_USER' : 'doom',
        },
        'healthcheck':{
            'test': 'rabbitmq:healtcheck',
            'interval': '30s',
            'timeout': '10s',
            'retries': 5,
        },
        'networks': ['localnet']
        # 'links':rabbit_identity_services + rabbit_api_services # may be unnecessary
    }
    if 'docker_compose_override' in rabbit_options:
        rabbitmq_docker_options.update(rabbit_options['docker_compose_override'])
        
    dockerOptions['services'][rabbit_options['name']] = rabbitmq_docker_options

def HandleEventBus(eventbuses):
    print ('Configuring Bus Instances..')
    for evenbus in eventbuses:
        evenbus_options = list(evenbus.values())[0]
        print('Scaffolding '+evenbus_options['name'])
        if(evenbus_options['type'] == 'rabbitmq'):
            HandleRabbitMq(evenbus_options)



def FindApiServicesUsesIs4(i_service_name):
    api_services = []
    if 'api_services' not in projectOptions:
        return api_services
    if len(projectOptions['api_services']) < 1:
        return api_services
    for service in projectOptions['api_services']:
        for key, value in service.items():            
            if 'authorization' in value:
                if value['authorization']['issuer'] == i_service_name:
                    api_services.append(value)
    return api_services
def FindClientsUsesIs4(i_service_name):
    clients = []
    if 'clients' not in projectOptions:
        return clients
    if len(projectOptions['clients']) < 1:
        return clients
    for client in projectOptions['clients']:
        for key, value in client.items():            
            if 'authorization' in value:
                if value['authorization']['issuer'] == i_service_name:
                    clients.append(value)
    return clients

def HandleIs4ClientConfiguration(clients, identity_service, is4_copy_folder):
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
        
def HandleIs4ResourcesConfiguration(resources, identity_service, is4_copy_folder):
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
            print ('Configuring Secrets')
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
            print ('Configuring Avaliable Scopes...')
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
            print ('Configuring User Claims...')
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

def HanldeIs4Csproj(is4_options,is4_folder):
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
    HandleCsprojLogging(is4_options,host_csproj_path)
    HandleCsprojDatabase(is4_options,host_csproj_path)
    HandleCsprojEventbus(is4_options,host_csproj_path)

    HandleCsprojLogging(is4_options,host_eflib_csproj_path)
    HandleCsprojDatabase(is4_options,host_eflib_csproj_path)
    HandleCsprojEventbus(is4_options,host_eflib_csproj_path)

def BuildConnStringForIs4(identity_options):
    database_instance_name = identity_options['database']['provider']
    database_instance = FindDatabaseWithName(database_instance_name)
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
    user_connection_string, user_connection_string_dev = BuildDatabaseConnectionString(database_type,database_instance['name'],identity_options['name'].lower()+'_users',user,password)        
    config_connection_string, config_connection_string_dev = BuildDatabaseConnectionString(database_type,database_instance['name'],identity_options['name'].lower()+'_config',user,password)
    conn_strings = {}
    conn_strings['user_connection_string'] =user_connection_string
    conn_strings['user_connection_string_dev'] =user_connection_string_dev
    conn_strings['config_connection_string'] =config_connection_string
    conn_strings['config_connection_string_dev'] =config_connection_string_dev
    return conn_strings
def HandleConnectionStringForIs4(identity_options ,is4_copy_folder):
    conn_strings =  BuildConnStringForIs4(identity_options)
    startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
    replace_dict = {
        '{{database:usersconnectionstring-dev}}':conn_strings['user_connection_string_dev'],
        '{{database:usersconnectionstring}}': conn_strings['user_connection_string'],
        '{{database:configsConnectionString-dev}}': conn_strings['config_connection_string_dev'],
        '{{database:configsConnectionString}}': conn_strings['config_connection_string']
    }
    replace_template_file(startup_file_path,replace_dict)
def HandleEventBusForIs4(i_srv, is4_copy_folder):
    eventbus_srv = FindEventBusWithName(i_srv['eventbus']['provider'])
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

def HandleIs4DockerFile(identity_service, is4_copy_folder):
    docker_file_path = os.path.join(is4_copy_folder,'Dockerfile')
    docker_replace_dict = {}
    docker_replace_dict['{{port}}'] = str(identity_service['port'])
    replace_template_file(docker_file_path,docker_replace_dict)
def HandleStartupForIs4(identity_service, is4_copy_folder):
    startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
    program_file_path = os.path.join(is4_copy_folder,'src','Host','Program.cs')
    HandleCSharpEventbus(identity_service,startup_file_path)
    HandleCSharpDatabase(identity_service,startup_file_path)
    HandleCSharpLogging(identity_service,startup_file_path)
    HandleCSharpServer(identity_service,startup_file_path)
    HandleCSharpLogging(identity_service,program_file_path)
def HandleIs4DockerCompose(identity_service, is4_copy_folder):
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

    dockerOptions['services'][identity_service['name']]  = is4_docker_props
def HandleIs4Cleaning(copy_folder):
    src_path = os.path.join(copy_folder)
    file_clean_paths = FindAllFilesWithExtensionInDirectory(src_path,('.cs','.csproj'))
    ClearRegionLines(file_clean_paths)
def HandleIdentityServer4(identity_service):
    is4_template_folder = os.path.join(identityServicesPath,'identityserver4ef')
    is4_copy_folder = os.path.join(srcDir,'IdentityServices',identity_service['name'])
    if os.path.isdir(is4_copy_folder):
      shutil.rmtree(is4_copy_folder,ignore_errors=True)  
    # TODO: Swap shutil operations
    #shutil.copytree(is4_template_folder,is4_copy_folder,ignore=shutil.ignore_patterns('bin*','obj*'))
    shutil.copytree(is4_template_folder,is4_copy_folder)
    
    api_services_using_is4 = FindApiServicesUsesIs4(identity_service['name'])
    clients_using_is4 = FindClientsUsesIs4(identity_service['name'])

    HandleIs4ClientConfiguration(clients_using_is4,identity_service,is4_copy_folder)
    HandleIs4ResourcesConfiguration(api_services_using_is4,identity_service,is4_copy_folder)
    HanldeIs4Csproj(identity_service,is4_copy_folder)
    HandleConnectionStringForIs4(identity_service ,is4_copy_folder)
    if 'eventbus' in identity_service:
        HandleEventBusForIs4(identity_service, is4_copy_folder)
    HandleIs4DockerFile(identity_service, is4_copy_folder)
    HandleIs4DockerCompose(identity_service, is4_copy_folder)
    HandleStartupForIs4(identity_service, is4_copy_folder)
    HandleIs4Cleaning(is4_copy_folder)
    
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
        with open(os.path.join(docker_file), 'r+') as f:
            filtered = list(filter_region(f, 'region (database)', 'end (database)'))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
# Change Namespace To Service Name 
# extensions: Tuple
def FindAllFilesWithExtensionInDirectory(folder_path, extensions):
    ext_files = []
    for folder_root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extensions):
                ext_files.append(os.path.join(os.path.abspath(folder_root),file))
    return ext_files
def ReplaceDotnetNameSpaces(file_paths, namespace_name, replace_name):
    replace_dict = {}
    replace_dict[namespace_name] = replace_name
    for file in file_paths:
        if os.path.exists(file):
            replace_template_file(file,replace_dict)
def ClearRegionLines(file_paths):
    for file in file_paths:        
        with open(os.path.join(file), 'r+') as f:
            filtered = list(Clear_File_Region_Marks(f))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
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
    db_entity_route_file_path =  os.path.join(api_copy_folder,'src','routes','entity.js')
    mongo_db_packages = ['mongoose']
    database_enabled = 'database' in api_service_options
    if (database_enabled):        
        database_provider = api_service_options['database']['provider']
        database_instance = FindDatabaseWithName(database_provider)
        if database_instance['type'] == 'mongodb':
            connection_string, connection_string_dev = BuildMongooseConnectionString(api_service_options, database_instance)
            replace_dict = {
                '{{mongoose_connection_dev}}': connection_string_dev,
                '{{mongoose_connection_dev}}': connection_string
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
    auth_test_route_file_path =  os.path.join(api_copy_folder,'src','routes','authtest.js')
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
                'context': 'src/ApiServices/'+CamelCaseName,
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
def HandleEnvironmentForAuthConfig(client_options, copy_folder):
    
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
    HandleEnvironmentForAuthConfig(client_options, copy_folder)
    HandleDockerfileForAngularSsr(client_options,copy_folder)
    HandleDockerComposeForAngularSsr(client_options)
def HandleAngular6SsrClient(client_options):
    CamelCaseName = to_camelcase(client_options['name'])
    template_folder = os.path.join(clientsPath,'angular','cli_6_ssr')
    copy_folder = os.path.join(srcDir,'Clients',CamelCaseName)
    if os.path.isdir(copy_folder):
        shutil.rmtree(copy_folder,ignore_errors=True)
    # TODO: Ignore Node MOdules in prod 
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
                projectDir, srcDir = CreateProjectDirectory(projectName, outputDir)

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

                docker_compose_path = os.path.join(projectDir,'docker-compose.yml')
                with open(docker_compose_path, 'w') as yaml_file:
                    yaml.dump(dockerOptions, yaml_file, default_flow_style=False)
                DockerComposeFinalization(docker_compose_path)
                print('!! IN case you generated .NET Core Services')
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


#pylint: disable-msg=W0612

import readline
import fileinput
import re
import shlex
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

dockerOptions = {'version' : 3, 'services': [], 'networks':[{'localnet':{'driver':'bridge'}}]}
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
    with open(os.path.join(environment_dev_path), 'r+') as f:
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
def BuildDatabaseConnectionString(database_type,server_host,database_name,user,password):
    conn_string = ""
    conn_string_dev=""
    if(database_type == "mysql"):
        conn_string =  "Server={0};Database={1};Uid={2};Pwd={3};CharSet=utf8mb4;".format(server_host,database_name,user,password)
        conn_string_dev = "Server={0};Database={1};Uid={2};Pwd={3};CharSet=utf8mb4;".format('localhost:3306',database_name,user,password)
    elif (database_type == 'postgresql'):
        conn_string ="Server={0};Database={1};Username={2};Password={3}".format(server_host,database_name,user,password)
        conn_string_dev = "Server={0};Database={1};Username={2};Password={3}".format('localhost:5432',database_name,user,password)
    elif (database_type == 'mssql'):
        conn_string = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format(server_host,database_name,user,password)
        conn_string_dev = "Data Source={0};Initial Catalog={1};User Id={2};Password={3}".format('localhost:1433',database_name,user,password)
    return conn_string, conn_string_dev
def BuildRedisConnectionString(redis_options):
    return redis_options['name'], '127.0.0.1'
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
            eb_replace_dict['{{rabbitmq:host}}'] = eventbus_instance['name']
            eb_replace_dict['{{rabbitmq:host-dev}}'] = 'rabbitmq://localhost/'
            eb_replace_dict['{{rabbitmq:user:username}}'] = 'doom'
            eb_replace_dict['{{rabbitmq:user:password}}'] = 'machine'
            if 'docker_compose_set' in eventbus_instance:
                if 'envoronment' in eventbus_instance['docker_compose_set']:
                    eb_replace_dict['{{rabbitmq:user:username}}'] = eventbus_instance['docker_compose_set']['environment']['RABBITMQ_DEFAULT_USER']
                    eb_replace_dict['{{rabbitmq:user:password}}'] = eventbus_instance['docker_compose_set']['environment']['RABBITMQ_DEFAULT_PASSWORD']
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


def CreateProjectDirectory(projectName):
    print ("Scaffolding Project", projectName)
    directory = os.path.normpath(os.path.join(scriptPath, optionsFilePath,'../'))
    projectDir = os.path.normpath(os.path.join(directory, projectName))
    srcDir = os.path.normpath(os.path.join(projectDir,"src"))
    if not os.path.isdir(srcDir):
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
    
    nginx_docker_obj = {
        server['name']: nginxOptions
    }
    dockerOptions['services'].append(nginx_docker_obj)

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
    default_postgre_options = {
        db_options['name']:{
            'image': 'postgres',
            'container_name': db_options['name'],
            'volumes': ['./postgres-data:/var/lib/postgresql/data'],
            'networks':['localnet'],
            'ports': ['5432:5432'],
            'environment': {
                'POSTGRES_DB': 'dev',
                'POSTGRES_USER': 'doom',
                'POSTGRES_PASSWORD': 'machine',
            }
        }
    }
    if 'docker_compose_set' in db_options:
        default_postgre_options[db_options['name']].update(db_options['docker_compose_set'])  
    postgre_docker_options = {    
        db_options['name']:db_options['docker_compose_set']
    }
    dockerOptions['services'].append(postgre_docker_options)

def HandleMySql(db_options):
    default_mysql_options = {
        db_options['name']:{
            'image': 'mysql/mysql-server:5.7',
            'container_name': db_options['name'],
            'command': 'mysqld --user=root --verbose',
            'volumes': ['mysqlvol:/var/lib/mysql/data'],
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
        default_mysql_options[db_options['name']].update(db_options['docker_compose_set'])    
    dockerOptions['services'].append(default_mysql_options)

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
    if os.path.isdir(redis_project_folder):
        shutil.rmtree(redis_project_folder,ignore_errors=True)
    #Copy template (config and Dockerfile)
    shutil.copytree(redis_template_folder,redis_project_folder)
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
        print('Scaffolding '+db_options['name'])
        if(db_options['type'] == 'postgresql'):
            HandlePostgreSql(db_options)
        if(db_options['type'] == 'mysql'):
            HandleMySql(db_options)
        elif db_options['type'] == 'redis':
            HandleRedisDatabase(db_options)

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
    rabbitmq_docker_options = {
        'image': 'rabbitmq:3-management-alpine',
        'container_name': rabbit_options['name'],
        'volumes': ['rabbit-volume:/var/lib/rabbitmq'],
        'ports': ['15672:15672','5672:5672','5671:5671'], # Management, Publish And Subsucribe Ports
        'environment': {
            'RABBITMQ_DEFAULT_PASS':'machine',
            'RABBITMQ_DEFAULT_USER' : 'doom',
        },
        'networks': ['localnet'],
        'links':rabbit_identity_services + rabbit_api_services # may be unnecessary
    }
    if 'docker_compose_set' in rabbit_options:
        rabbitmq_docker_options.update(rabbit_options['docker_compose_set'])
    docker_opts_to_set = {
        rabbit_options['name']: rabbitmq_docker_options
    }
    dockerOptions['services'].append(docker_opts_to_set)

def HandleEventBus(eventbuses):
    print ('Configuring Bus Instances..')
    for evenbus in eventbuses:
        evenbus_options = list(evenbus.values())[0]
        print('Scaffolding '+evenbus_options['name'])
        if(evenbus_options['type'] == 'rabbitmq'):
            HandleRabbitMq(evenbus_options)



def FindApiServicesUsesIs4(i_service_name):
    api_services = []
    for service in projectOptions['api_services']:
        for key, value in service.items():            
            if 'authorization' in value:
                if value['authorization']['issuer'] == i_service_name:
                    api_services.append(value)
    return api_services
def FindClientsUsesIs4(i_service_name):
    clients = []
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
        client_host = client['name'].lower()+'.localhost'

        redirect_url_templ_val = ( InDbQ(client_host) +',\n' 
        + '\t\t\t\t\t\t'+ InDbQ(client_host+'/silent-renew.html') +',\n' 
        + '\t\t\t\t\t\t'+ InDbQ(client_host+'/login-callback.html')) 
        
        post_logout_redirect_url_val = ( InDbQ(client_host) +',\n'
        + '\t\t\t\t\t\t'+ InDbQ(client_host+'/loggedout'))

        cors_origins_val = InDbQ(client_host) +',\n'

        grant_type_val = 'GrantTypes.Implicit'
        if client['type'].startswith('web'):
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
    if database_type=='mysql':
        if 'docker_compose_set' in database_instance:
            if 'environment' in database_instance['docker_compose_set']:
                if 'MYSQL_USER' in database_instance['docker_compose_set']['environment']:
                    user = database_instance['docker_compose_set']['environment']['MYSQL_USER']
                if 'MYSQL_PASSWORD' in database_instance['docker_compose_set']['environment']:
                    password = database_instance['docker_compose_set']['environment']['MYSQL_PASSWORD']
    if database_type=='postgresql':
        if 'docker_compose_set' in database_instance:
            if 'environment' in database_instance['docker_compose_set']:
                if 'POSTGRES_USER' in database_instance['docker_compose_set']['environment']:
                    user = database_instance['docker_compose_set']['environment']['POSTGRES_USER']
                if 'POSTGRES_PASSWORD' in database_instance['docker_compose_set']['environment']:
                    password = database_instance['docker_compose_set']['environment']['POSTGRES_PASSWORD']
    user_connection_string, user_connection_string_dev = BuildDatabaseConnectionString(database_type,database_instance['name'],identity_options['name']+'_users',user,password)        
    config_connection_string, config_connection_string_dev = BuildDatabaseConnectionString(database_type,database_instance['name'],identity_options['name']+'_config',user,password)
    return user_connection_string,user_connection_string_dev, config_connection_string,config_connection_string_dev
def HandleConnectionStringForIs4(identity_options ,is4_copy_folder):
    userConnString ,userConnString_dev, configConnString,configConnString_dev =  BuildConnStringForIs4(identity_options)
    startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
    with open(startup_file_path,'r') as cs_file:
        cs_content = cs_file.read()
    os.remove(startup_file_path)
    cs_content = (cs_content
    .replace('{{database:usersconnectionstring-dev}}', userConnString_dev)
    .replace('{{database:usersconnectionstring}}', userConnString)
    .replace('{{database:configconnectionstring-dev}}', configConnString_dev)
    .replace('{{database:configconnectionstring}}',configConnString)
    )
    with open(startup_file_path,'w') as cs_file_new:
        cs_file_new.write(cs_content)

def HandleEventBusForIs4(i_srv, is4_copy_folder):
    eventbus_srv = FindEventBusWithName(i_srv['eventbus']['provider'])
    startup_file_path = os.path.join(is4_copy_folder,'src','Host','Startup.cs')
    repleceDict = {
        '{{rabbitmq:host}}': eventbus_srv['name'],
        '{{rabbitmq:host-dev}}' : 'rabbitmq://localhost/'
    }
    if 'docker_compose_set' in eventbus_srv:
        if 'environment' in eventbus_srv['docker_compose_set']:
            if 'RABBITMQ_DEFAULT_USER' in eventbus_srv['docker_compose_set']['environment']:
                repleceDict['{{rabbitmq:user:username}}'] = eventbus_srv['docker_compose_set']['environment']['RABBITMQ_DEFAULT_USER']
            else:
                repleceDict['{{rabbitmq:user:username}}'] = 'doom'
            if 'RABBITMQ_DEFAULT_PASSWORD' in eventbus_srv['docker_compose_set']['environment']:
                repleceDict['{{rabbitmq:user:password}}'] = eventbus_srv['docker_compose_set']['environment']['RABBITMQ_DEFAULT_PASSWORD']
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
    docker_replace_dict['{{port}}'] = str(identity_service['ports'][0])
    
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
        'image': identity_service['name'],
        'build': {
            'context': 'src/IdentityServices/'+identity_service['name']+'/',
            'dockerfile': 'Dockerfile'
        },
        'ports': [],
        'links': [],
        'depends_on':[],
        'networks':['localnet'],        
    }
    is4_docker_props['links'].append(identity_service['database']['provider'])
    is4_docker_props['depends_on'].append(identity_service['database']['provider'])
    for port in identity_service['ports']:
        is4_docker_props['ports'].append(str(port)+':'+str(port))
    eventbus_enabled = 'eventbus' in identity_service
    if eventbus_enabled:
        eb_provider = identity_service['eventbus']['provider']        
        is4_docker_props['links'].append(eb_provider)
        is4_docker_props['depends_on'].append(eb_provider)
    docker_opts_to_set = {
        identity_service['name']: is4_docker_props
    }
    dockerOptions['services'].append(docker_opts_to_set)
def HandleIdentityServer4(identity_service):
    is4_template_folder = os.path.join(identityServicesPath,'identityserver4ef')
    is4_copy_folder = os.path.join(srcDir,'IdentityServices',identity_service['name'])
    if os.path.isdir(is4_copy_folder):
      shutil.rmtree(is4_copy_folder,ignore_errors=True)  
    shutil.copytree(is4_template_folder,is4_copy_folder,ignore=shutil.ignore_patterns('bin*','obj*'))

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
    if database_type=='mysql':
        if 'docker_compose_set' in database_instance:
            if 'environment' in database_instance['docker_compose_set']:
                if 'MYSQL_USER' in database_instance['docker_compose_set']['environment']:
                    user = database_instance['docker_compose_set']['environment']['MYSQL_USER']
                if 'MYSQL_PASSWORD' in database_instance['docker_compose_set']['environment']:
                    password = database_instance['docker_compose_set']['environment']['MYSQL_PASSWORD']
    if database_type=='postgresql':
        if 'docker_compose_set' in database_instance:
            if 'environment' in database_instance['docker_compose_set']:
                if 'POSTGRES_USER' in database_instance['docker_compose_set']['environment']:
                    user = database_instance['docker_compose_set']['environment']['POSTGRES_USER']
                if 'POSTGRES_PASSWORD' in database_instance['docker_compose_set']['environment']:
                    password = database_instance['docker_compose_set']['environment']['POSTGRES_PASSWORD']
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
        'NameContext': CamelCaseName + 'Context'        
    }
    if 'database' in dotnet_service:
        database_instance = FindDatabaseWithName(dotnet_service['database']['provider'])
        conn_string, conn_string_dev = BuildConnStringForDotnetApi(dotnet_service)
        replaceDict['{{database:connectionString}}'] = conn_string
        replaceDict['{{database:connectionString-dev}}'] = conn_string_dev
    if 'cache' in dotnet_service:
        if dotnet_service['cache']['type'] == 'redis':
            redis_instance = FindDatabaseWithName(dotnet_service['cache']['redis_options']['redis_server'])
            redis_conn_string, redis_conn_string_dev = BuildRedisConnectionString(redis_instance)
            replaceDict['{{redis_options:connection}}'] = redis_conn_string
            replaceDict['{{redis_options:connection-dev}}'] = 'localhost:6379'
            if 'redis_instance_name' in dotnet_service['cache']['redis_options']:
                replaceDict['{{redis_options:instance_name}}'] = dotnet_service['cache']['redis_options']['redis_instance_name']
    if 'authorization' in dotnet_service:
        issuer = dotnet_service['authorization']['issuer']
        identity_instance = FindIdentityServiceWithName(issuer)
        replaceDict['{{authorization:api_name}}'] = dotnet_service['name']        
        replaceDict['{{authorization:authority}}'] = str.lower(identity_instance['name'])+'.localhost'
        replaceDict['{{authorization:authority-dev}}'] = 'localhost:'+str(identity_instance['ports'][0])
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
    CamelCaseDbName = to_camelcase(dotnet_service['name']) + 'Context'
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
        rm_files = ['migrations.sh','updatedb.sh','dropdb.sh']
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
    docker_replace_dict['{{port}}'] = str(dotnet_service['ports'][0])
    docker_replace_dict['{{project_name}}'] = to_camelcase(dotnet_service['name'])
    replace_template_file(docker_file_path,docker_replace_dict)
def HandleDotnetApiDockerCompose(dotnet_service,api_copy_folder):
    docker_props = {
        'image': dotnet_service['name'],
        'build': {
            'context': 'src/ApiServices/'+to_camelcase(dotnet_service['name'])+'/',
            'dockerfile': 'Dockerfile'
        },
        'ports': [],
        'links': [],
        'depends_on':[],
        'networks':['localnet'],        
    }
    if 'database' in dotnet_service:
        docker_props['links'].append(dotnet_service['database']['provider'])
        docker_props['depends_on'].append(dotnet_service['database']['provider'])
    if 'ports' in dotnet_service:
        for port in dotnet_service['ports']:
            docker_props['ports'].append(str(port)+':'+str(port))
    eventbus_enabled = 'eventbus' in dotnet_service
    if eventbus_enabled:
        eb_provider = dotnet_service['eventbus']['provider']        
        docker_props['links'].append(eb_provider)
        docker_props['depends_on'].append(eb_provider)
    docker_opts_to_set = {
        dotnet_service['name']: docker_props
    }
    dockerOptions['services'].append(docker_opts_to_set)
def HandleDotnetApiService(api_service_options):
    CamelCaseName = to_camelcase(api_service_options['name'])
    api_template_folder = os.path.join(apiServicesPath,'dotnet_web_api','src')
    api_copy_folder = os.path.join(srcDir,'ApiServices',CamelCaseName )
    if os.path.isdir(api_copy_folder):
        shutil.rmtree(api_copy_folder,ignore_errors=True)
    shutil.copytree(api_template_folder,api_copy_folder,ignore=shutil.ignore_patterns('bin*','obj*'))
    
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
def HandleApiServices(api_services):
    print ('Scaffolding Api Services')
    for api_service in api_services:
        api_service_options = list(api_service.values())[0]
        if(api_service_options['type']=='dotnet_web_api'):
            HandleDotnetApiService(api_service_options)
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
            '{{auth:stsServer}}': identity_instance['name'].lower()+'.localhost',
            '{{auth:clientUrl}}': client_options['name'].lower()+'.localhost',
            '{{auth:client_id}}': identity_instance['name']
        }
        dev_replace_dict = {
            '{{auth:stsServer}}': 'localhost:'+str(identity_instance['ports'][0]),
            '{{auth:clientUrl}}': 'localhost:'+str(client_options['ports'][0]),
            '{{auth:client_id}}': identity_instance['name']
        }
        if 'scopes' in client_options['authorization']:
            prod_replace_dict['{{auth:scope}}'] = " ".join(client_options['authorization']['scopes'])
            dev_replace_dict['{{auth:scope}}'] = " ".join(client_options['authorization']['scopes'])
        else:
            prod_replace_dict['{{auth:scope}}'] = 'openid profile email' # default scope values
            dev_replace_dict['{{auth:scope}}'] = 'openid profile email'
        replace_template_file(environment_dev_path,dev_replace_dict)
        replace_template_file(environment_prod_path,prod_replace_dict)
def HandleAngular6SsrAuth(client_options, copy_folder):
    HandleEnvironmentForAuthConfig(client_options, copy_folder)
def HandleAngular6SsrClient(client_options):
    CamelCaseName = to_camelcase(client_options['name'])
    template_folder = os.path.join(clientsPath,'angular','cli_6_ssr')
    copy_folder = os.path.join(srcDir,'Clients',CamelCaseName)
    if os.path.isdir(copy_folder):
        shutil.rmtree(copy_folder,ignore_errors=True)
    shutil.copytree(template_folder,copy_folder,ignore=shutil.ignore_patterns('node_modules*'))
    HandleAngular6SsrAuth(client_options,copy_folder)

def HandleClients(clients):
    print ('Scaffolding Clients')
    for client in clients:
        client_options = list(client.values())[0]
        if(client_options['type']=='angular_cli_6_ssr'):
            HandleAngular6SsrClient(client_options)  
print('Enter a command')
print('To get help, enter `help`.')
while True:
    cmd, *args = shlex.split(input('> '))
    if cmd=='boile':
        optionsFilePath = args[0]
        with open(optionsFilePath, 'r') as stream:
            try:
                # Load Yaml
                projectOptions = yaml.load(stream)
                if not ('name' in projectOptions):
                    print('Please Provide a valid project name')
                    break
                projectName = projectOptions['name']
                # Create Project Files
                projectDir, srcDir = CreateProjectDirectory(projectName)

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


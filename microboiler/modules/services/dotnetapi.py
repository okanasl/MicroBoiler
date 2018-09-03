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
    Clear_File_Region_Marks)

from microboiler.modules.databases.postgre import BuildPostgreConnectionString
from microboiler.modules.databases.mysql import BuildMysqlConnectionString

from microboiler.modules.templating.csharp import Csharp

import os
import shutil


class DotnetApi(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        self.csharp_templater = Csharp(projectOptions,project_templates_paths,outputPath)
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleDotnetApiService(self, api_service_options):
        CamelCaseName = to_camelcase(api_service_options['name'])
        apiServicesPath = os.path.join(self.project_templates_paths,'api_services')
        api_template_folder = os.path.join(apiServicesPath,'dotnet_web_api','src')
        srcDir = os.path.join(self.outputPath,'src')
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


        self.HandleDotnetApiCsproj(api_service_options,api_copy_folder)
        self.HandleDotnetApiStartup(api_service_options,api_copy_folder)
        self.HandleDotnetApiProgramFile(api_service_options,api_copy_folder)
        self.HandleDotnetApiDbContext(api_service_options,api_copy_folder)
        self.HandleDotnetApiNameSpaceAndCleaning(api_service_options,api_copy_folder)
        self.HandleDotnetApiDockerFile(api_service_options,api_copy_folder)

        docker_config = self.HandleDotnetApiDockerCompose(api_service_options,api_copy_folder)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(api_service_options['name'], docker_config)

    def HandleDotnetApiCsproj(self, dotnet_service, api_copy_folder):
        print ('Handle DotnetApi Csproj File')
        api_csproj_path = os.path.join(api_copy_folder,
            'src',
            to_camelcase(dotnet_service['name'])+'.csproj')
        # Handle Host Application
        self.csharp_templater.HandleCsprojLogging(dotnet_service,api_csproj_path)
        self.csharp_templater.HandleCsprojDatabase(dotnet_service,api_csproj_path)
        self.csharp_templater.HandleCsprojEventbus(dotnet_service,api_csproj_path)
    def BuildConnStringForDotnetApi(self, dotnet_options):
        database_instance_name = dotnet_options['database']['provider']
        database_instance = FindDatabaseWithName(self.projectOptions, database_instance_name)
        database_type = database_instance['type']
        connection_string ='' 
        user = 'doom'
        password = 'machine'
        if database_type=='mysql' or database_type=='postgresql':
            if 'username' in database_instance:
                user = database_instance['username']
            if 'password' in database_instance:
                password = database_instance['password']
        if database_type == 'mysql':            
            connection_string, connection_string_dev = BuildMysqlConnectionString(database_instance['name'],dotnet_options['name'],user,password)        
        elif database_type == 'postgresql':
            connection_string, connection_string_dev = BuildPostgreConnectionString(database_instance['name'],dotnet_options['name'],user,password)        
                
        return connection_string , connection_string_dev

    def HandleDotnetApiStartup(self, dotnet_service, api_copy_folder):
        print ('Handle DotnetApi Startup.cs File')
        api_startup_path = os.path.join(api_copy_folder,
            'src',
            'Startup.cs')
        
        self.csharp_templater.HandleCSharpDatabase(dotnet_service,api_startup_path)
        self.csharp_templater.HandleCSharpCache(dotnet_service,api_startup_path)
        self.csharp_templater.HandleCSharpEventbus(dotnet_service,api_startup_path)
        self.csharp_templater.HandleCSharpLogging(dotnet_service,api_startup_path)
        self.csharp_templater.HandleCSharpServer(dotnet_service,api_startup_path)
        self.csharp_templater.HandleCSharpSwagger(dotnet_service,api_startup_path)
        # Set DBContext Name
        CamelCaseName = to_camelcase(dotnet_service['name'])
        replaceDict = {
            'NameContext': CamelCaseName.replace('.','') + 'Context'    
        }
        if 'database' in dotnet_service:
            
            conn_string, conn_string_dev = self.BuildConnStringForDotnetApi(dotnet_service)
            replaceDict['{{database:connectionString}}'] = conn_string
            replaceDict['{{database:connectionString-dev}}'] = conn_string_dev

        if 'cache' in dotnet_service:
            if dotnet_service['cache']['type'] == 'redis':
                redis_instance = FindDatabaseWithName(self.projectOptions, dotnet_service['cache']['redis_options']['redis_server'])
                if redis_instance is None:
                    print ('Warning: Redis instance could not found. Configuration left default')
                else:
                    redis_conn_string, redis_conn_string_dev = BuildRedisConnectionString(redis_instance)
                    replaceDict['{{redis_options:connection}}'] = redis_conn_string
                    replaceDict['{{redis_options:connection-dev}}'] =  redis_conn_string_dev
                    if 'redis_instance_name' in dotnet_service['cache']['redis_options']:
                        replaceDict['{{redis_options:instance_name}}'] = dotnet_service['cache']['redis_options']['redis_instance_name']
        if 'authorization' in dotnet_service:
            issuer = dotnet_service['authorization']['issuer']
            if issuer is None:
                print ('Error: Identity Issuer for '+dotnet_service['name']+' is required')
            identity_instance = FindIdentityServiceWithName(self.projectOptions, issuer)
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

    def HandleDotnetApiProgramFile(self, dotnet_service, api_copy_folder):
        api_program_path = os.path.join(api_copy_folder,
            'src',
            'Program.cs')

        self.csharp_templater.HandleCSharpLogging(dotnet_service,api_program_path)
    def HandleDotnetApiDbContext(self, dotnet_service, api_copy_folder):
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
    
    def HandleDotnetApiNameSpaceAndCleaning(self, dotnet_service, api_copy_folder):
        src_path = os.path.join(api_copy_folder,'src')
        file_clean_paths = FindAllFilesWithExtensionInDirectory(src_path,('.cs','.csproj'))
        CamelCaseServiceName = to_camelcase(dotnet_service['name'])
        self.csharp_templater.ReplaceDotnetNameSpaces(file_clean_paths,'DotnetWebApi',CamelCaseServiceName)
        ClearRegionLines(file_clean_paths)
    def HandleDotnetApiDockerFile(self, dotnet_service, api_copy_folder):
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

    def HandleDotnetApiDockerCompose(self, dotnet_service,api_copy_folder):
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

        return docker_props
    
from microboiler.modules.basemodule import BaseModule
from microboiler.modules.templating.templating import filter_region,filter_region_with_tag,filter_sub_region, replace_template_file
from microboiler.modules.utils.utils import FindDatabaseWithName, FindEventBusWithName, FindServerWithName
import os
class Csharp(BaseModule):
    def __init(self,  projectOptions, project_templates_paths, outputPath, client_options):
        super().__init__()
    def HandleCsprojLogging(self, service, host_csproj_path):
        logging_enabled = 'logging' in service
        if logging_enabled:
            if 'type' not in service['logging']:
                logging_type = 'serilog'
            else:
                logging_type = 'microsoft'
        if(logging_enabled):
            filter_sub_region(host_csproj_path,'logging',logging_type)
        else:
            filter_region_with_tag(host_csproj_path,'logging')
    def HandleCsprojDatabase(self, service_options, host_csproj_path):
        database_enabled = 'database' in service_options        
        if(database_enabled):
            database_instance = FindDatabaseWithName(self.projectOptions, service_options['database']['provider'])
            if database_instance is None:
                print ('Could not found database with name'+service_options['database']['provider'])
            database_type = database_instance['type']
            filter_sub_region(host_csproj_path,'database',database_type)
        else:
            filter_region_with_tag(host_csproj_path,'database')
    def HandleCsprojEventbus(self, service_options, host_csproj_path):
        eventbus_enabled = 'eventbus' in service_options
        
        if(eventbus_enabled):
            eventbus_instance = FindEventBusWithName(self.projectOptions, service_options['eventbus']['provider'])

            eventbus_type = eventbus_instance['type']
            filter_sub_region(host_csproj_path,'eventbus',eventbus_type)
        else:
            filter_region_with_tag(host_csproj_path,'eventbus')

    def HandleCSharpLogging(self, service, sharp_file_path):
        logging_enabled = 'logging' in service
        if logging_enabled:
            if 'type' not in service['logging']:
                logging_type = 'serilog'
            else:
                logging_type = 'microsoft'
        if(logging_enabled):
            filter_sub_region(sharp_file_path,'logging',logging_type)
        else:        
            filter_region_with_tag(sharp_file_path,'logging')
    def HandleCSharpDatabase(self, service_options, sharp_file_path):
        database_enabled = 'database' in service_options
        
        if(database_enabled):
            database_instance = FindDatabaseWithName(self.projectOptions, service_options['database']['provider'])
            database_type = database_instance['type']
            filter_sub_region(sharp_file_path,'database',database_type)
        else:
            filter_region_with_tag(sharp_file_path,'database')
    def HandleCSharpCache(self, service_options, sharp_file_path):
        cache_enabled = 'cache' in service_options
        
        if(cache_enabled):
            cache_type = service_options['cache']['type']
            filter_sub_region(sharp_file_path,'cache',cache_type)
        else:        
            filter_region_with_tag(sharp_file_path,'cache')
    def HandleCSharpServer(self, service_options,sharp_file_path):
        server_enabled = 'server' in service_options
        if(server_enabled):
            server_instance = FindServerWithName(self.projectOptions, service_options['server']['provider'])
            server_type = server_instance['type']
            filter_sub_region(sharp_file_path,'server',server_type)
        else:
            filter_region_with_tag(sharp_file_path,'server')
    def HandleCSharpSwagger(self, dotnet_service, sharp_file_path):
        is_swagger_in_config = 'swagger' in dotnet_service
        if(is_swagger_in_config):
            swagger_enabled = dotnet_service['swagger']
            if not swagger_enabled:
                filter_region_with_tag(sharp_file_path,'swagger')
    def HandleCSharpEventbus(self, service_options, sharp_file_path):
        eventbus_enabled = 'eventbus' in service_options
        
        if(eventbus_enabled):
            eb_replace_dict = {}
            
            eventbus_instance = FindEventBusWithName(self.projectOptions, service_options['eventbus']['provider'])

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
            filter_sub_region(sharp_file_path,'eventbus',eventbus_type)
        else:
            filter_region_with_tag(sharp_file_path,'eventbus')


    def ReplaceDotnetNameSpaces(self, file_paths, namespace_name, replace_name):
        replace_dict = {}
        replace_dict[namespace_name] = replace_name
        for file in file_paths:
            if os.path.exists(file):
                replace_template_file(file,replace_dict)
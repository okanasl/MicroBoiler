from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
import os
import shutil
class Redis(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleRedisDatabase(self, db_options):
        print (self.project_templates_paths)
        databasesPath = os.path.join(self.project_templates_paths,'databases')
        redis_template_folder = os.path.join(databasesPath,'redis')
        redis_project_folder = os.path.join(self.outputPath, db_options['name'])
        if os.path.isdir(redis_project_folder):
            shutil.rmtree(redis_project_folder,ignore_errors=True)
        #Copy template (config and Dockerfile)
        shutil.copytree(redis_template_folder,redis_project_folder)

        docker_options = self.GetRedisDockerOptions(db_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(db_options['name'],docker_options)
        docker_instance.AddVolume('redis-volume')

    def GetRedisDockerOptions(self, db_options):

        docker_volume_dir = os.path.normpath(os.path.join(self.outputPath,'docker_volumes','redis'))
        if not os.path.isdir(docker_volume_dir):
            os.makedirs(docker_volume_dir)

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
        # Add Ports
        if 'ports' in db_options:
            for port in db_options['ports']:
                redis_docker_options['ports'].append(str(port)+':'+str(port))
        # Default Port if Not provided
        else:
            redis_docker_options['ports'].append('"6379:6379"')
        redis_using_services = self.FindRedisUsingServiceNames(db_options['name'])
        # Add Links So We can use redis instance name to connect it in services
        for service_name in redis_using_services:
            redis_docker_options['links'].append(service_name)
        return redis_docker_options
    
    def FindRedisUsingServiceNames(self, redis_name):
        services = []
        for service in self.projectOptions['api_services']:
            for _, value in service.items():
                if 'cache' in value:
                    if value['cache']['type'] == 'redis':
                        services.append(value['name'])
        for identity_service in self.projectOptions['identity_services']:
            for _, value in identity_service.items():
                if  'cache' in value:
                    if value['cache']['type'] == 'redis':
                        services.append(value['name'])
        
        return services

def BuildRedisConnectionString(redis_options):
    return redis_options['name'], 'localhost:6379'
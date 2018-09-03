from microboiler.modules.basemodule import BaseModule
import os
from microboiler.modules.devops.docker import Docker

class RabbitMq(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleRabbitMq(self,rabbit_options):
        
        docker_options = self.GetRabbitmqDockerOptions(rabbit_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(rabbit_options['name'],docker_options)
        docker_instance.AddVolume('rabbit-volume')

    def GetRabbitmqDockerOptions(self, rabbit_options):
        # No need rabbitmq to know about subs.
        # rabbit_api_services = self.FindApiServicesUsesRabbitmq(rabbit_options['name'])
        # rabbit_identity_services = self.FindIdentityServicesUsesRabbitmq(rabbit_options['name'])

        docker_volume_dir = os.path.normpath(os.path.join(self.outputPath,'docker_volumes','rabbitmq'))
        if not os.path.isdir(docker_volume_dir):
            os.makedirs(docker_volume_dir)
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
            
        return rabbitmq_docker_options
    def FindApiServicesUsesRabbitmq(self, rabbit_name):
        api_services = []
        for service in self.projectOptions['api_services']:
            for key, value in service.items():            
                if 'eventbus' in value:
                    if value['eventbus']['provider'] == rabbit_name:
                        api_services.append(value['name'])
        return api_services

    def FindIdentityServicesUsesRabbitmq(self,rabbit_name):
        i_services = []
        for service in self.projectOptions['identity_services']:
            for key, value in service.items():            
                if 'eventbus' in value:
                    if value['eventbus']['provider'] == rabbit_name:
                        i_services.append(value['name'])
        return i_services

    

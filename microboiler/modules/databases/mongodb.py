
from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
import os
class MongoDb(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleMongoDb(self, db_options):
        mongo_docker_options = self.GetDockerOptions(db_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(db_options['name'], mongo_docker_options)
        docker_instance.AddVolume('mongodb-volume')
    
    def GetDockerOptions(self, db_options):
        mongo_docker_volume_dir = os.path.normpath(os.path.join(self.outputPath,'docker_volumes','mongodb'))
        if not os.path.isdir(mongo_docker_volume_dir):
            os.makedirs(mongo_docker_volume_dir)
        
        mongo_docker_options = {
            'image': db_options['name'].lower(),
            'container_name': db_options['name'],
            'volumes': ['mongodb-volume:'+mongo_docker_volume_dir],
            'ports':[],
            'restart': 'on-failure',
            'links':[],
            'environment':{},
            'depends_on':[],
            'networks': ['localnet']
        }
        # Add Ports
        if 'ports' in db_options:
            for port in db_options['ports']:
                mongo_docker_options['ports'].append(str(port)+':'+str(port))
        # Default Port if Not provided
        else:
            mongo_docker_options['ports'].append('"27017:27017"')
        mongo_using_services = self.FindMongoUsingServiceNames(db_options['name'])
        # Add Links So We can use mongo instance name to connect it in services
        for service_name in mongo_using_services:
            mongo_docker_options['links'].append(service_name)

        if 'docker_compose_override' in db_options:
            mongo_docker_options.update(db_options['docker_compose_override'])

        # Set username and password
        if 'username' in db_options:
            mongo_docker_options['environment']['MONGO_INITDB_ROOT_USERNAME'] = db_options['username']
        if 'password' in db_options:
            mongo_docker_options['environment']['MONGO_INITDB_ROOT_PASSWORD'] = db_options['password']
        mongo_docker_options['environment']['MYSQL_ROOT_PASSWORD'] = 'test'

        
        return mongo_docker_options

    def FindMongoUsingServiceNames(self,mongo_name):
        api_services = []
        if 'api_services' not in self.projectOptions:
            return api_services
        if len(self.projectOptions['api_services'])== 0:
            return api_services
        for service in self.projectOptions['api_services']:
            for _, value in service.items():            
                if 'database' in value:
                    if value['database']['provider'] == mongo_name:
                        api_services.append(value['name'])
        return api_services

def GetConnectionString(api_options,mongodb_options):
    """
    Returns ConnectionString for Mongodb with mongoose etc.
    """
    db_name = api_options['database']['database_name']
    db_host_dev = 'localhost'
    db_host = mongodb_options['name']
    db_username = mongodb_options['username']
    db_password = mongodb_options['password']
    conn_string = 'mongodb://{0}:{1}@{2}/{3}'.format(db_username,db_password,db_host,db_name)
    conn_string_dev=  'mongodb://{0}:{1}@{2}/{3}'.format(db_username,db_password,db_host_dev,db_name)
    return conn_string, conn_string_dev
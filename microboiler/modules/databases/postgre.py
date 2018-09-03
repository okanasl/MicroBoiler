from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
import os

class Postgre(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandlePostgre(self, db_options):
        docker_options = self.BuildDockerOptions(db_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(db_options['name'],docker_options)
        docker_instance.AddVolume('postgres-volume')

    def BuildDockerOptions(self, db_options):    
        docker_volume_dir = os.path.normpath(os.path.join(self.outputPath,'docker_volumes','postgresql'))
        if not os.path.isdir(docker_volume_dir):
            os.makedirs(docker_volume_dir)
        default_postgre_options = {
            'image': 'postgres',
            'container_name': db_options['name'],
            'volumes': ['postgres-volume:'+docker_volume_dir],
            'networks':['localnet'],
            'ports': ['5432:5432'],
            'environment': {
                'POSTGRES_DB': 'dev',
            }            
        }
        
        if 'docker_compose_override' in db_options:
            default_postgre_options.update(db_options['docker_compose_override'])  
        # Set Username And Password for image
        if 'username' in db_options:
            default_postgre_options['environment']['POSTGRES_USER'] = db_options['username']
        if 'password' in db_options:
            default_postgre_options['environment']['POSTGRES_PASSWORD'] = db_options['password']
        
        return default_postgre_options

    
def BuildPostgreConnectionString(server_host,database_name,user,password):       
    conn_string ="Server={0};Database={1};Username={2};Password={3}".format(server_host,database_name,user,password)
    conn_string_dev = "Server={0};Database={1};Username={2};Password={3}".format('localhost',database_name,user,password)
    return conn_string, conn_string_dev

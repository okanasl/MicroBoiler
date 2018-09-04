from microboiler.modules.basemodule import BaseModule
from microboiler.modules.devops.docker import Docker
import os
class Mysql(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions, project_templates_paths, outputPath)

    def HandleMysql(self, db_options):
        docker_options = self.BuildDockerOptions(db_options)
        docker_instance = Docker.getInstance()
        docker_instance.AddService(db_options['name'],docker_options)
        docker_instance.AddVolume('mysql-volume')

    def BuildDockerOptions(self, db_options):
        docker_volume_dir = os.path.normpath(os.path.join(self.outputPath,'docker_volumes','mysql'))
        if not os.path.isdir(docker_volume_dir):
            os.makedirs(docker_volume_dir)
        default_mysql_options = {

            'image': 'mysql/mysql-server:5.7',
            'container_name': db_options['name'],
            'command': 'mysqld --user=root --verbose',
            'volumes': ['mysql-volume:'+docker_volume_dir],
            'networks':['localnet'],            
            'ports': ['3306:3306'],
            'environment': {
                'MYSQL_ROOT_HOST': "%",
                'MYSQL_ALLOW_EMPTY_PASSWORD': "false"
            }          
        }

        # Set username and password
        if 'username' in db_options:
            default_mysql_options['environment']['MYSQL_USER'] = db_options['username']
        if 'password' in db_options:
            default_mysql_options['environment']['MYSQL_PASSWORD'] = db_options['password']
            default_mysql_options['environment']['MYSQL_ROOT_PASSWORD'] = db_options['password']

        if 'docker_compose_override' in db_options:
            default_mysql_options.update(db_options['docker_compose_override'])
        return default_mysql_options

    
def BuildMysqlConnectionString(server_host,database_name,user,password):       
    conn_string ="Server={0};Database={1};Username={2};Password={3}".format(server_host,database_name,user,password)
    conn_string_dev = "Server={0};Database={1};Username={2};Password={3}".format('localhost',database_name,user,password)
    return conn_string, conn_string_dev

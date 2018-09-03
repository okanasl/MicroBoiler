from microboiler.modules.basemodule import BaseModule
from microboiler.modules.templating.templating import replace_template_file
import os
import yaml
class Docker(BaseModule):
    # Docker singleton Instance.
    __instance = None
    dockerOptions = {'version' : "3", 'services': {},'volumes':{} ,'networks':{'localnet':{'driver':'bridge'}}}
    @staticmethod
    def getInstance():
        """ Static access method. """
        return Docker.__instance 
    @staticmethod
    def initSingleton(projectOptions, project_templates_paths, outputPath):
        if Docker.__instance == None:
            Docker(projectOptions, project_templates_paths, outputPath)

    def __init__(self,projectOptions, project_templates_paths, outputPath):
        """ Virtually private constructor. """
        if Docker.__instance != None:
            raise Exception("This class is a singleton!")
        else:
            Docker.__instance = self
            super().__init__(projectOptions, project_templates_paths, outputPath)
    def AddService(self,name,options):
        self.dockerOptions['services'][name] = options   
    def AddVolume(self,name):
        self.dockerOptions['volumes'][name] = {}        
    def DumpTo(self, file):
        with open(file, 'w') as yaml_file:
            yaml.dump(self.dockerOptions, yaml_file, default_flow_style=False)
    def DockerComposeFinalization(self, file):
        replace_dict = {
            'rabbitmq:healtcheck': '["CMD", "curl", "-f", "http://localhost:15672"]'
        }
        replace_template_file(file,replace_dict)
    

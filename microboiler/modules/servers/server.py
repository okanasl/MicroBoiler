from microboiler.modules.basemodule import BaseModule
class Server(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath, server_options):
        self.server_options = server_options
        super().__init__(projectOptions,project_templates_paths,outputPath)
    def FindServerWithName(self,name):
        server_instances = self.projectOptions['servers']
        for server in server_instances:
            if list(server.values())[0]['name'] == name:
                return list(server.values())[0] 
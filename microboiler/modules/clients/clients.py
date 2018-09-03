from microboiler.modules.basemodule import BaseModule

class Client(BaseModule):
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        super().__init__(projectOptions,project_templates_paths)

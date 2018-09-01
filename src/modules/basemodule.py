class BaseModule:
    def __init__(self, projectOptions, project_templates_paths, outputPath):
        self.projectOptions = projectOptions
        self.outputPath = outputPath
        self.project_templates_paths = project_templates_paths
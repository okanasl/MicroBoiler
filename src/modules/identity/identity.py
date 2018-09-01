from modules.basemodule import BaseModule
class Identity(BaseModule):
    def FindIdentityServiceWithName(self,name):
        identity_services = self.projectOptions['identity_services']
        for i_s in identity_services:
            if list(i_s.values())[0]['name'] == name:
                return list(i_s.values())[0]
import json
import re
import os

def InDbQ(value):
    return '\"'+value+'\"'

def to_camelcase(s):
    s_val = re.sub(r'(?!^)_([a-zA-Z])', lambda m: m.group(1).upper(), s)
    return s_val[0].upper()+s_val[1:]

def FindClientWithName(projectOptions,name):
    clients = projectOptions['clients']
    for client in clients:
        if list(client.values())[0]['name'] == name:
            return list(client.values())[0]

def FindIdentityServiceWithName(projectOptions,name):
    identity_services = projectOptions['identity_services']
    for i_s in identity_services:
        if list(i_s.values())[0]['name'] == name:
            return list(i_s.values())[0]

def FindDatabaseWithName(projectOptions,name):
    database_instances = projectOptions['databases']
    for db in database_instances:
        if list(db.values())[0]['name'] == name:
            return list(db.values())[0]

def FindEventBusWithName(projectOptions,name):
    eventbus_instances = projectOptions['eventbus']
    for bus in eventbus_instances:
        if list(bus.values())[0]['name'] == name:
            return list(bus.values())[0]

def FindServerWithName(projectOptions,name):
    server_instances = projectOptions['servers']
    for server in server_instances:
        if list(server.values())[0]['name'] == name:
            return list(server.values())[0] 




def FindAllFilesWithExtensionInDirectory(folder_path, extensions):
    ext_files = []
    for folder_root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extensions):
                ext_files.append(os.path.join(os.path.abspath(folder_root),file))
    return ext_files

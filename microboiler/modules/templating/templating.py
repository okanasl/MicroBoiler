import os
import json
def replace_template_file(filepath,replace_dict):
    with open(filepath,'r') as cs_file:
        cs_content = cs_file.read()
    os.remove(filepath)
    for key, value in replace_dict.items():
        cs_content = cs_content.replace(key,value)
    with open(filepath,'w') as cs_file_new:
        cs_file_new.write(cs_content)
def clear_file_region_tags(file):
    try:
        with open(file,'r+') as f:
            filtered = list(Clear_File_Region_Marks(f))
            f.seek(0)
            f.writelines(filtered)
            f.truncate()
    except:
        print (file)
        pass
    
def filter_region_with_tag(file,tag):
    with open(file, 'r+') as f:
        filtered = list(filter_region(f, 'region ('+tag+')', 'end ('+tag+')'))
        f.seek(0)
        f.writelines(filtered)
        f.truncate()
def filter_region(file, start_delete_key, stop_delete_key):
    """
    Given a file handle, generate all lines except those between the specified
    regions.
    """
    lines = iter(file)
    try:
        while True:
            line = next(lines)
            if start_delete_key in line and ':all' not in line:
                # Discard all lines up to and including the stop marker
                while stop_delete_key not in line:
                    line = next(lines)
                line = next(lines)            
            yield line
    except StopIteration:
        return
def filter_sub_region(
    file,
    parent_marker,
    child_marker):
    lines = iter(file)
    parent_marker_start = 'region ('+parent_marker+':'
    parent_marker_end = 'end ('+parent_marker+':'
    try:
        while True:
            line = next(lines)
            if parent_marker_start in line and child_marker not in line:
                while parent_marker_end not in line:
                    line = next(lines)
            yield line
    except StopIteration:
        return
def Clear_File_Region_Marks(file):
    lines = iter(file)
    region_marks = ['//& region','<!-- region','//& end','<!-- end']
    try:
        for line in lines:
            found = False
            for mark in region_marks:
                if mark in line:
                    found = True
            if not found:
                yield line
        while True:
            line = next(lines)
            
    except StopIteration:
        return
def ClearRegionLines(file_paths):
    for file in file_paths:        
        clear_file_region_tags(file)
def RemovePackagesFromJson(file,packages):
    with open(file) as f:
        package_info = json.load(f)
        for package in packages:
            package_info['dependencies'].pop(package, None)
        f.seek(0)
        json.dump(package_info,f)
import os
import shutil
import yaml
import commentjson as json  # for JSON with comments
from pathlib import Path
from configparser import ConfigParser
import xml.etree.ElementTree as ET
from collections import OrderedDict

def load_file(filepath):
    suffix = filepath.suffix.lower()
    with open(filepath, 'r', encoding='utf-8') as f:
        if suffix == '.json':
            return json.load(f)
        elif suffix in ['.yaml', '.yml']:
            return yaml.safe_load(f)
        elif suffix == '.properties':
            parser = ConfigParser()
            parser.read_file(f)
            return {k: v for section in parser.sections() for k, v in parser.items(section)}
        elif suffix == '.xml':
            return ET.parse(filepath)
    return None

def save_file(filepath, data):
    suffix = filepath.suffix.lower()
    with open(filepath, 'w', encoding='utf-8') as f:
        if suffix == '.json':
            import json as std_json
            std_json.dump(data, f, indent=2, ensure_ascii=False)
        elif suffix in ['.yaml', '.yml']:
            yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
        elif suffix == '.properties':
            parser = ConfigParser()
            parser.add_section('DEFAULT')
            for k, v in data.items():
                parser.set('DEFAULT', k, v)
            parser.write(f)
        elif suffix == '.xml':
            data.write(filepath, encoding='utf-8', xml_declaration=True)

def merge_data(a, b):
    if isinstance(a, dict) and isinstance(b, dict):
        for key, value in b.items():
            if key in a:
                a[key] = merge_data(a[key], value)
            else:
                a[key] = value
        return a
    elif isinstance(a, list) and isinstance(b, list):
        combined = a + b
        seen = set()
        result = []
        for item in combined:
            hashable = json.dumps(item, sort_keys=True) if isinstance(item, (dict, list)) else item
            if hashable not in seen:
                seen.add(hashable)
                result.append(item)
        return result
    else:
        return b

def merge_xml_trees(tree1, tree2):
    root1 = tree1.getroot()
    root2 = tree2.getroot()

    def merge_elements(elem1, elem2):
        for child2 in elem2:
            matched = False
            for child1 in elem1:
                if child1.tag == child2.tag and child1.attrib == child2.attrib:
                    merge_elements(child1, child2)
                    matched = True
                    break
            if not matched:
                elem1.append(child2)

    merge_elements(root1, root2)
    return tree1

def merge_files(src_file: Path, dst_file: Path):
    suffix = src_file.suffix.lower()
    src_data = load_file(src_file)
    dst_data = load_file(dst_file)

    if src_data is None or dst_data is None:
        print(f"Warning: Cannot read {src_file} or {dst_file}")
        return

    if suffix in ['.json', '.yaml', '.yml', '.properties']:
        merged_data = merge_data(dst_data, src_data)
    elif suffix == '.xml':
        merged_data = merge_xml_trees(dst_data, src_data)
    else:
        print(f"Skipped unsupported merge: {src_file}")
        return

    save_file(dst_file, merged_data)
    print(f"Merged: {src_file.relative_to(src_file.parents[1])}")

def merge_folders(folder_a: str, folder_b: str):
    folder_a = Path(folder_a)
    folder_b = Path(folder_b)

    if not folder_a.exists() or not folder_b.exists():
        print("One or both folders do not exist.")
        return

    for root, _, files in os.walk(folder_a):
        relative_path = Path(root).relative_to(folder_a)
        target_dir = folder_b / relative_path
        target_dir.mkdir(parents=True, exist_ok=True)

        for file in files:
            src_file = Path(root) / file
            dst_file = target_dir / file
            suffix = src_file.suffix.lower()

            if not dst_file.exists():
                shutil.copy2(src_file, dst_file)
                print(f"Copied: {src_file.relative_to(folder_a)}")
            elif suffix in ['.json', '.yaml', '.yml', '.properties', '.xml']:
                merge_files(src_file, dst_file)
            else:
                print(f"Skipped (already exists): {src_file.relative_to(folder_a)}")

if __name__ == "__main__":
    folder_a_path = "path/to/folder_a"
    folder_b_path = "path/to/folder_b"
    merge_folders(folder_a_path, folder_b_path)

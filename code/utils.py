import json
import os
import csv


def is_valid_json(file_path):
    if not os.path.exists(file_path):
        return False
    try:
        with open(file_path, 'r') as f:
            json.load(f)
        return True
    except (json.JSONDecodeError, UnicodeDecodeError, json.decoder.JSONDecodeError):
        return False


def get_filename(path):
    string = os.path.basename(path)
    filename = string[:string.rfind(".")]
    return filename


def parse_fileinfo(path):  # parse from extracted file by extract.py
    string = os.path.basename(path)
    filename = string[:string.rfind(".")]
    _, tool, reponame = filename.split('#')
    with open(path, 'r') as file:
        data = json.load(file)
    return filename, tool, reponame, data


def write_row2csv(filename: str, data: list) -> None:
    with open(filename, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(data)

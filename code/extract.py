import glob
import hashlib
import json
import os
import time
from loguru import logger
from .extract_cdx_ort import extract_cdx_ort
from .utils import is_valid_json, get_filename


def extract_items(data: dict, filename: str, item_list: list, standard: str = 'spdx', mode: str = 'meta'):
    result = {}
    identifier = ''
    if standard == 'spdx' and mode == 'multiple':
        identifier = data.get('SPDXID', 'NE')
    elif standard == 'cdx' and mode == 'multiple':
        identifier = data.get('bom-ref', data.get('purl', hashlib.md5(data['name'].encode()).hexdigest()))

    if identifier == 'NE' and mode == 'multiple':
        logger.error(f'[NoIdentifier][{identifier}]: {filename}')
        return result
    result = {item: data.get(item, 'NE') for item in item_list}

    if mode == 'meta':
        return result
    elif mode == 'multiple':
        return {identifier: result}
    else:
        print(standard, mode)
        logger.error(f'[UnknownMode]: {mode}')
        return {}


def spdx_extract(filepath: str, spdx_items: dict, result_path: str):
    filename = get_filename(filepath)
    spdx_info = {}

    with open(filepath, 'r') as f:
        data = json.load(f)
        # SPDX Document Creation Information
        create_info = extract_items(data, filename, spdx_items['create_items'], 'spdx', 'meta')

        # creationInfo needs special handling
        if 'creationInfo' in spdx_items['create_items']:
            if 'creationInfo' in data:
                creationInfo = data['creationInfo']
                create_info['creators'] = creationInfo.get('creators', 'NE')
                create_info['created'] = creationInfo.get('created', 'NE')
            else:
                create_info['creators'] = 'NE'
                create_info['created'] = 'NE'
        spdx_info['documents'] = create_info

        # Extract Package Information
        packages_info = {}
        if 'packages' in data:
            for pkg in data['packages']:
                packages_info.update(extract_items(pkg, filename, spdx_items['package_items'], 'spdx', 'multiple'))
        else:
            packages_info = 'NE'
            logger.error(f'[NoPackages]: {filepath}')
        spdx_info['packages'] = packages_info

        # Extract File Information
        files_info = {}
        if 'files' in data:
            for file in data['files']:
                files_info.update(extract_items(file, filename, spdx_items['file_items'], 'spdx', 'multiple'))
        else:
            files_info = 'NE'
            logger.error(f'[NoFiles]: {filepath}')
        spdx_info['files'] = files_info

    # Write to JSON file
    spdx_info = json.dumps(spdx_info, indent=4)
    write_path = os.path.join(result_path, filename + '.json')
    with open(write_path, 'w') as f:
        f.write(spdx_info)
    logger.info(f'[SPDXExtractionSucceed]: {write_path}')


def cdx_extract(filepath: str, cdx_items: dict, result_path: str):
    filename = get_filename(filepath)
    cdx_info = {}

    with open(filepath, 'r') as f:
        data = json.load(f)

        # Metadata Information
        meta_info = {}
        meta_info = extract_items(data, filename, cdx_items['metadata']['create_items'], 'cdx', 'meta')

        metadata = data.get('metadata', {})
        meta_info.update(extract_items(metadata, filename, cdx_items['metadata']['meta_items'], 'cdx', 'meta'))

        comp_in_metadata = metadata.get('component', {})
        comp_in_meta_items = extract_items(comp_in_metadata, filename, cdx_items['metadata']['comp_in_meta_items'], 'cdx', 'meta')
        # deal with same name
        comp_in_meta_items.update({'name_com': comp_in_meta_items.pop('name')})
        comp_in_meta_items.update({'version_com': comp_in_meta_items.pop('version')})
        meta_info.update(comp_in_meta_items)

        cdx_info['metadata'] = meta_info

        # Component Information
        comp_info = {}
        if 'components' in data:
            for comp in data['components']:
                comp_info.update(extract_items(comp, filename, cdx_items['components_items'], 'cdx', 'multiple'))
        else:
            comp_info = 'NE'
            logger.error(f'[NoComponents]: {filepath}')
        cdx_info['components'] = comp_info

    # Write to JSON file
    cdx_info = json.dumps(cdx_info, indent=4)
    write_path = os.path.join(result_path, filename + '.json')
    with open(write_path, 'w') as f:
        f.write(cdx_info)
    logger.info(f'[CDXExtractionSucceed]: {write_path}')


def extract(filenames, file_path, result_path):
    spdx_items = {
        'create_items': ['SPDXID', 'name', 'spdxVersion', 'dataLicense', 'documentNamespace', 'creationInfo'],
        'package_items': ['name', 'SPDXID', 'downloadLocation', 'packageVerificationCode',
                          'versionInfo', 'originator', 'supplier', 'copyrightText'],  # and more......
        'file_items': ['fileName', 'SPDXID', 'checksums']
    }
    cdx_items = {
        'metadata': {
            'create_items': ['bomFormat', 'specVersion', 'version', 'serialNumber'],
            'meta_items': ['timestamp', 'tools'],
            'comp_in_meta_items': ['name', 'version', 'bom-ref']  # renamed into name_com, version_com
        },
        'components_items': ['name', 'author', 'type', 'bom-ref', 'purl', 'version', 'copyright', 'cpe']  # and more......
    }
    cdx_ort_items = {
        'metadata': {
            'create_items': ['bomFormat', '@xmlns', '@version', '@serialNumber'],  # Need special handle in ORT
            'meta_items': ['timestamp', 'tools'],
            'comp_in_meta_items': ['name', 'version', 'bom-ref']  # Need special handle in ORT  # renamed into name_com, version_com
        },
        'components_items': ['name', 'author', 'type', 'bom-ref', 'purl', 'version', 'copyright', 'cpe']  # and more......
    }

    with open(filenames, 'r') as f:
        line = f.readline().strip()
        while line:
            filepath = os.path.join(file_path, line)
            if not os.path.exists(filepath):
                logger.error(f'[FileNotFound]: {filepath}')
                line = f.readline().strip()
                continue
            if not is_valid_json(filepath):
                logger.error(f'[InvalidJSON]: {filepath}')
                line = f.readline().strip()
                continue
            if 'spdx' in line:
                spdx_extract(filepath, spdx_items, result_path)
            elif 'cdx#ort' in line:
                extract_cdx_ort(filepath, cdx_ort_items, result_path)  # empty code
            elif 'cdx' in line:
                cdx_extract(filepath, cdx_items, result_path)
            else:
                logger.error(f'[UnknownFormat]: {filepath}')
            line = f.readline().strip()

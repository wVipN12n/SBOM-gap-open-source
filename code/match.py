import csv
import os
import re
import math
from loguru import logger
from Levenshtein import jaro
from urllib.parse import unquote
from .utils import is_valid_json, parse_fileinfo, write_row2csv
from .evaluate import check_empty, equal_cmp, longest_common_substring_consistency_score, version_consistency, text_consistency


def deal_filename(name):
    # deal with filenames in Files Section
    if name.startswith('./'):
        name = name[2:]
    elif name.startswith('/'):
        name = name[1:]
    return name


def compareName(name1, name2):
    # fix encoding problem
    name1, name2 = unquote(name1), unquote(name2)
    # removing prefixes
    name1 = re.sub("npm:|pip:|go:|actions:|composer:|rust:|ruby:|nuget:|rubygems:|docker:|maven:| ", '', name1).lower()
    name2 = re.sub("npm:|pip:|go:|actions:|composer:|rust:|ruby:|nuget:|rubygems:|docker:|maven:| ", '', name2).lower()
    return name1 == name2


def deal_license(license):
    # return a list of licenses, only keeps the license id in SPDX Licerse List
    pass
    return []


def license_consistency(license1, license2):
    # deal with multiple format of licenses store in SBOMs
    pass
    return 0


def match_cdx(file1_path, file2_path, result_path):
    # match process is built on the basis of the extracted data by extract.py
    filename1, tool1, reponame1, filedata1 = parse_fileinfo(file1_path)
    filename2, tool2, reponame2, filedata2 = parse_fileinfo(file2_path)
    metadata1, metadata2 = filedata1['metadata'], filedata2['metadata']
    component1, component2 = filedata1['components'], filedata2['components']
    cmp_flag = True
    if component1 == 'NE' or component2 == 'NE':
        cmp_flag = False
    else:
        component_keys1, component_keys2 = component1.keys(), component2.keys()

    all_matched_scores = {}
    all_matched_scores['basic_info'] = f'cdx_{tool1}_{tool2}_{reponame1}'
    if metadata1 == 'NE' or metadata2 == 'NE':
        all_matched_scores['repo_info'] = [0, 0]
    else:
        repo_name1 = metadata1['name_com']
        repo_name2 = metadata2['name_com']
        if check_empty(repo_name1) and check_empty(repo_name2) or repo_name1 == '' and repo_name2 == '':
            repo_name_score = -1
        elif repo_name1 == 'NE' or repo_name2 == 'NE' or check_empty(repo_name1) or check_empty(repo_name2) or repo_name1 == '' or repo_name2 == '':
            repo_name_score = 0
        else:
            repo_name_score = jaro(repo_name1, repo_name2)
        all_matched_scores['repo_info'] = [repo_name_score,
                                           version_consistency(metadata1['version_com'], metadata2['version_com'])]
    all_matched_scores['pkg_info'] = []
    all_matched_scores['statistic_info'] = []
    matched_pkg = []
    if not cmp_flag:
        all_matched_scores['statistic_info'] += [0, 0, 0]
        all_matched_scores['pkg_info'] = [[0, 0, 0, 0, 0]]
        return all_matched_scores

    for k1 in component_keys1:
        pkg1 = component1[k1]
        for k2 in component_keys2:
            pkg2 = component2[k2]
            if compareName(pkg1['name'], pkg2['name']):
                if pkg1['name'] in matched_pkg or pkg2['name'] in matched_pkg:
                    continue
                matched_pkg.append(pkg1['name'])
                author_score = text_consistency(pkg1['author'], pkg2['author'])
                type_score = equal_cmp(pkg1['type'], pkg2['type'])
                purl_score = longest_common_substring_consistency_score(pkg1['purl'], pkg2['purl'])
                cpe_score = longest_common_substring_consistency_score(pkg1['cpe'], pkg2['cpe'])
                # license_score = license_consistency(pkg1['licenses'], pkg2['licenses'])
                version_score = version_consistency(pkg1['version'], pkg2['version'])
                result = [author_score, type_score, purl_score, cpe_score, version_score]

                if any(x < 0 for x in result):
                    with open(f'{result_path}/cdx-special-consistency.csv', 'a') as fd:
                        writer = csv.writer(fd)
                        writer.writerow(['cdx', tool1, tool2, reponame1, pkg1['name']] + result)
                        all_matched_scores['pkg_info'].append([math.fabs(x) for x in result])
                else:
                    all_matched_scores['pkg_info'].append(result)

    if len(all_matched_scores['pkg_info']) == 0:
        all_matched_scores['pkg_info'].append([0, 0, 0, 0, 0])

    all_matched_scores['statistic_info'] += [len(component_keys1), len(component_keys2), len(matched_pkg)]
    logger.success(f'[FinishedCDX]: {tool1}||{tool2}||{reponame1}')
    return all_matched_scores


def external_ref_proc(externalRefs: list):
    # deal with cpes and purls in SPDX externalReferences, and return them as lists
    pass
    return [], []


def deal_PVC(PVC):
    # return the packageVerificationCodeValue string
    if PVC == 'NE' or check_empty(PVC) or PVC == '':
        return None
    if type(PVC) == str:
        return PVC
    elif type(PVC) == list:
        if len(PVC) == 1:
            logger.info(f'[ListPVC]: {PVC}||{PVC[0]}')
            return PVC[0]
    elif type(PVC) == dict:
        if 'packageVerificationCodeValue' in PVC:
            return PVC['packageVerificationCodeValue']
    logger.error(f'Invalid packageVerificationCode: {PVC}')
    return None


def match_spdx(file1_path, file2_path, result_path):
    filename1, tool1, reponame1, filedata1 = parse_fileinfo(file1_path)
    filename2, tool2, reponame2, filedata2 = parse_fileinfo(file2_path)
    doc1, doc2 = filedata1['documents'], filedata2['documents']
    pkgs1, pkgs2 = filedata1['packages'], filedata2['packages']
    files1, files2 = filedata1['files'], filedata2['files']

    pkg_flag = True
    if pkgs1 == 'NE' or pkgs2 == 'NE':
        pkg_flag = False
    else:
        pkgs_keys1, pkgs_keys2 = pkgs1.keys(), pkgs2.keys()

    files_flag = True
    if files1 == 'NE' or files2 == 'NE':
        files_flag = False
    else:
        files_keys1, files_keys2 = files1.keys(), files2.keys()

    all_matched_scores = {}
    all_matched_scores['basic_info'] = f'spdx_{tool1}_{tool2}_{reponame1}'
    all_matched_scores['repo_info'] = []
    all_matched_scores['pkg_info'] = []
    all_matched_scores['files_info'] = []
    all_matched_scores['statistic_info'] = []

    repo1_flag = False
    repo2_flag = False
    if files_flag:
        matched_files = []
        for key1 in files_keys1:
            if len(files_keys1) > 2000 or len(files_keys2) > 2000:  # filter out too many files
                logger.warning(f'[TooManyFiles]: {tool1}||{tool2}||{reponame1}')
                break
            f1 = files1[key1]
            for f2 in files_keys2:
                f2 = files2[f2]
                if compareName(deal_filename(f1['fileName']), deal_filename(f2['fileName'])):  # deal with relative path
                    if f1['fileName'] in matched_files or f2['fileName'] in matched_files:
                        continue
                    matched_files.append(f1['fileName'])
                    if len(f1['checksums']) == 0 or len(f2['checksums']) == 0:
                        checksum_score = 0.

                    elif len(f1['checksums']) == 1 and len(f2['checksums']) == 1:
                        checksum_score = equal_cmp(f1['checksums'][0]['checksumValue'], f2['checksums'][0]['checksumValue'])

                        if checksum_score == 1:
                            logger.success(f"[SameChecksum]{f1['checksums'][0]['checksumValue']}, {f2['checksums'][0]['checksumValue']}")
                        elif checksum_score == -1:
                            logger.error(
                                f'[SpecialChecksum]: spdx||{tool1}||{tool2}||{reponame1}||{f1["fileName"]}||{f1["checksums"][0]["checksumValue"]}||{f2["checksums"][0]["checksumValue"]}')
                            checksum_score = 1
                        else:
                            logger.error(
                                f'[DiffChecksum]: spdx||{tool1}||{tool2}||{reponame1}||{f1["fileName"]}||{f2["fileName"]}||{f1["checksums"][0]["checksumValue"]}||{f2["checksums"][0]["checksumValue"]}')
                    else:
                        len1, len2 = len(f1['checksums']), len(f2['checksums'])
                        checksum_score = 0.
                        for c1 in f1['checksums']:
                            for c2 in f2['checksums']:
                                if c1['algorithm'] == c2['algorithm']:
                                    logger.debug(
                                        f'[MatchFileAndAlgorithm]: spdx||{tool1}||{tool2}||{reponame1}||{f1["fileName"]}||{f2["fileName"]}||{c1["checksumValue"]}||{c2["checksumValue"]}')
                                    c = equal_cmp(c1['checksumValue'], c2['checksumValue'])
                                    if c == -1:
                                        checksum_score += 1
                                        logger.error(
                                            f'[SpecialChecksum]: spdx||{tool1}||{tool2}||{reponame1}||{f1["fileName"]}||{c1["checksumValue"]}||{c2["checksumValue"]}')
                                    else:
                                        checksum_score += c
                        checksum_score /= max(len(f1['checksums']), len(f2['checksums']))
                    all_matched_scores['files_info'].append([checksum_score])

        if len(all_matched_scores['files_info']) == 0:
            all_matched_scores['files_info'].append([0])
        all_matched_scores['statistic_info'] += [len(files_keys1), len(files_keys2), len(matched_files)]

    if not files_flag:
        all_matched_scores['statistic_info'] += [0, 0, 0]
        all_matched_scores['files_info'] = [[0]]

    if not pkg_flag:
        all_matched_scores['statistic_info'] += [0, 0, 0]
        all_matched_scores['repo_info'] = [0, 0, 0, 0, 0, 0, 0]  # need to match with the nums of repo_info fields
        all_matched_scores['pkg_info'] = [0, 0, 0, 0, 0, 0]
        return all_matched_scores

    matched_pkg = []
    for k1 in pkgs_keys1:
        pkg1 = pkgs1[k1]
        if compareName(pkg1['name'], reponame1):
            repo1_flag = True
        for k2 in pkgs_keys2:
            pkg2 = pkgs2[k2]
            if compareName(pkg2['name'], reponame1):
                repo2_flag = True
            if compareName(pkg1['name'], pkg2['name']):
                if pkg1['name'] in matched_pkg or pkg2['name'] in matched_pkg:
                    continue
                matched_pkg.append(pkg1['name'])

                originator_score = text_consistency(pkg1['originator'], pkg2['originator'])
                supplier_score = text_consistency(pkg1['supplier'], pkg2['supplier'])
                copyright_score = text_consistency(pkg1['copyrightText'], pkg2['copyrightText'])

                version_score = version_consistency(pkg1['versionInfo'], pkg2['versionInfo'])

                PVC_score = equal_cmp(deal_PVC(pkg1['packageVerificationCode']), deal_PVC(pkg2['packageVerificationCode']))

                # cpe1, purl1 = external_ref_proc(pkg1['externalRefs'])
                # cpe2, purl2 = external_ref_proc(pkg2['externalRefs'])
                # cpe_score, purl_score = 0., 0.

                dL_score = longest_common_substring_consistency_score(pkg1['downloadLocation'], pkg2['downloadLocation'])

                # licenseC_score = license_consistency(pkg1['licenseConcluded'], pkg2['licenseConcluded'])
                # licenseD_score = license_consistency(pkg1['licenseDeclared'], pkg2['licenseDeclared'])

                if repo1_flag and repo2_flag:
                    all_matched_scores['repo_info'] = [jaro(doc1['name'], doc2['name']), originator_score, supplier_score, copyright_score,
                                                       version_score, PVC_score, dL_score]
                    repo1_flag = False
                    repo2_flag = False
                else:
                    result = [originator_score, supplier_score, copyright_score, version_score, PVC_score, dL_score]
                    if any(x < 0 for x in result):
                        with open(f'{result_path}/spdx-special-consistency.csv', 'a') as fd:
                            writer = csv.writer(fd)
                            writer.writerow(['spdx', tool1, tool2, reponame1, pkg1['name']] + result)
                        all_matched_scores['pkg_info'].append([math.fabs(x) for x in result])
                    else:
                        all_matched_scores['pkg_info'].append(result)

    if len(all_matched_scores['pkg_info']) == 0:
        all_matched_scores['pkg_info'].append([0, 0, 0, 0, 0, 0])
    if len(all_matched_scores['repo_info']) == 0:
        all_matched_scores['repo_info'] = [0, 0, 0, 0, 0, 0, 0]

    all_matched_scores['statistic_info'] += [len(pkgs_keys1), len(pkgs_keys2), len(matched_pkg)]
    logger.success(f'[FinishedSPDX]: {tool1}||{tool2}||{reponame1}')

    return all_matched_scores


def match_all(file1_path, file2_path, standard, result_path):
    # global fileinvalid, TotalMatchedName
    filevalidflag = True

    if file1_path == file2_path:
        logger.debug(f'[SameFile]: {file1_path}')
        filevalidflag = False
        # fileinvalid += 1

    if not is_valid_json(file1_path):
        logger.debug(f'[FileNotExistOrInvalid]: {file1_path}')
        filevalidflag = False
        # fileinvalid += 1

    if not is_valid_json(file2_path):
        logger.debug(f'[FileNotExistOrInvalid]: {file2_path}')
        filevalidflag = False
        # fileinvalid += 1

    if not filevalidflag:
        return None

    if standard == 'spdx':
        all_matched_scores = match_spdx(file1_path, file2_path, result_path)
    elif standard == 'cdx':
        all_matched_scores = match_cdx(file1_path, file2_path, result_path)
    else:
        logger.error(f'Invalid standard: {standard}')

    return all_matched_scores


def match(standard, extract_path, filenames, result_path):
    tools_spdx = ['syft', 'gh-sbom', 'sbom-tool', 'ort']
    tools_cdx = ['syft', 'gh-sbom', 'scancode', 'cdxgen']
    print(standard, extract_path, filenames, result_path)
    special = os.path.join(result_path, standard + '-special-consistency.csv')
    with open(special, 'w', newline='') as fd:
        writer = csv.writer(fd)
        if standard == 'cdx':
            writer.writerow([
                'standard', 'tool1', 'tool2', 'repo_name', 'pkg_name',
                'author_score', 'type_score', 'purl_score', 'cpe_score', 'version_score'
            ])
        elif standard == 'spdx':
            # ['spdx', tool1, tool2, reponame1, pkg1['name']] + result + [neg_cpe, neg_purl]
            writer.writerow([
                'standard', 'tool1', 'tool2', 'repo_name', 'pkg_name',
                # below are for pkgs
                'originator_score', 'supplier_score', 'copyright_score', 'version_score', 'PVC_score', 'dL_score'
            ])
    if standard == 'spdx':
        tools = tools_spdx
    elif standard == 'cdx':
        tools = tools_cdx
    else:
        logger.error(f'Invalid standard: {standard}')
        return
    for i in range(len(tools)):
        for j in range(i+1, len(tools)):
            tool1 = tools[i]
            tool2 = tools[j]
            wbfile = os.path.join(result_path, f'{standard}-{tool1}-{tool2}-package-consistency.csv')
            with open(wbfile, 'w', newline='') as fd:
                writer = csv.writer(fd)
                if standard == 'cdx':
                    writer.writerow([
                        'repo_name', 'repo_name_meta', 'repo_version', 'comp_num1', 'comp_num2', 'matched_comps',
                        'author_score', 'type_score', 'purl_score', 'cpe_score', 'version_score'
                    ])
                elif standard == 'spdx':
                    writer.writerow([
                        'repo_name', 'files_num1', 'files_num2', 'matched_files', 'pkgs_num1', 'pkgs_num2', 'matched_pkgs',
                        # repo info
                        'doc_name', 'originator_score_r', 'supplier_score_r', 'copyright_score_r', 'version_score_r', 'PVC_score_r', 'dL_score_r',
                        # pkg info
                        'originator_score', 'supplier_score', 'copyright_score', 'version_score', 'PVC_score', 'dL_score',
                        # file info
                        'checksum_score'
                    ])
    with open(filenames, 'r') as fd:
        line = fd.readline()
        while (line):
            line = line.strip()
            for i in range(len(tools)):
                tool1 = tools[i]
                filepath1 = os.path.join(extract_path, f'{standard}#{tool1}#{line}.json')
                for j in range(i+1, len(tools)):
                    tool2 = tools[j]
                    filepath2 = os.path.join(extract_path, f'{standard}#{tool2}#{line}.json')
                    results = match_all(filepath1, filepath2, standard, result_path)
                    if results is not None:
                        if standard == 'cdx':
                            row = [line] + results['repo_info'] + results['statistic_info'] + \
                                [sum(x) / len(x) for x in zip(*results['pkg_info'])]
                        elif standard == 'spdx':
                            row = [line] + results['statistic_info'] + results['repo_info'] + \
                                [sum(x) / len(x) for x in zip(*results['pkg_info'])] + \
                                [sum(x) / len(x) for x in zip(*results['files_info'])]
                        wbfile = os.path.join(result_path, f'{standard}-{tool1}-{tool2}-package-consistency.csv')
                        write_row2csv(wbfile, row)
            line = fd.readline()


if __name__ == '__main__':
    extract_path = 'results/extracted'
    filenames = 'results/extracted_filenames.txt'
    result_path = 'results/matched'

    logger.add(os.path.join(result_path, 'match.log'), rotation='10 MB')
    match('cdx', extract_path, filenames, result_path)
    match('spdx', extract_path, filenames, result_path)

    logger.success('Match Analysis Finished.')

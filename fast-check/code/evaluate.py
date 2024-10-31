import math
from Levenshtein import jaro
from urllib.parse import unquote
from loguru import logger


def check_empty(v):
    return v == 'NONE' or v == 'NOASSERTION' or v is None


def equal_cmp(v1, v2):  # Exact match strings
    if check_empty(v1) and check_empty(v2) or v1 == '' and v2 == '':
        return -1
    if v1 == 'NE' or v2 == 'NE' or check_empty(v1) or check_empty(v2) or v1 == '' or v2 == '':
        return 0
    if v1 == v2:
        return 1
    else:
        return 0


def check_digit(version):
    return all(char.isdigit() or char == '.' for char in version) and version != ''


def longest_common_substring_consistency_score(str1, str2):
    if check_empty(str1) and check_empty(str2) or str1 == '' and str2 == '':
        return -1
    if str1 == 'NE' or str2 == 'NE' or check_empty(str1) or check_empty(str2) or str1 == '' or str2 == '':
        return 0.
    if str1 == str2:
        return 1.
    if type(str1) != str or type(str2) != str:
        logger.error(f'Invalid string: {str1}||{str2}')

    # fix encoding problem
    str1, str2 = unquote(str1), unquote(str2)
    dp = [[0] * (len(str2) + 1) for _ in range(len(str1) + 1)]
    longest_len = 0
    end_pos = 0

    # Build the dp table and find the longest length
    for i in range(1, len(str1) + 1):
        for j in range(1, len(str2) + 1):
            if str1[i-1] == str2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
                if dp[i][j] > longest_len:
                    longest_len = dp[i][j]
                    end_pos = i
            else:
                dp[i][j] = 0

    # Extract the longest common substring
    # longest_common_substr = str1[end_pos-longest_len:end_pos]
    consistency_score = longest_len / max(len(str1), len(str2)) if max(len(str1), len(str2)) else 0.
    return consistency_score


def version_consistency(version1, version2):
    # global SpecialChar, fileinvalid, varchar, backspace, VersionNotMatch, NoneOrEmpty, ManualVersion
    if check_empty(version1) and check_empty(version2):
        return -1
    if check_empty(version1) or check_empty(version2) or version1 == 'NE' or version2 == 'NE':  # FIXME
        return 0.
    if version1 == version2:
        return 1.
    if version1 == '' or version2 == '':
        return 0.
    weights = [0.7, 0.2, 0.1]

    # deal with observed special characters
    version1 = version1.strip().replace(' ', '')
    version2 = version2.strip().replace(' ', '')  # remove spaces
    if version1.startswith('v') or version1.startswith('V'):
        version1 = version1[1:]
    if version2.startswith('v') or version2.startswith('V'):
        version2 = version2[1:]

    # equal after preprocessing
    if version1 == version2:
        return 1.

    # manually defined version as some tools need to be manually filled
    # if '15.4.6' in version1 or '15.4.6' in version2:
    #     logger.info(f'[ManualDefinedVersion]: {version1}||{version2}')
    special = ['<', '>', '=', '+', ',', '~', '!', '-']
    for sp in special:
        if sp in version1 or sp in version2:
            logger.info(f'[SpecialChar]: {version1}||{version2}')
            break

    # SemVer deal procedure
    v1_parts = version1.split('.')
    v2_parts = version2.split('.')

    length = min(len(v1_parts), len(v2_parts))
    if length == 2:
        weights = [0.8, 0.2]
    if length == 1:
        weights = [1.]
    length = length if length <= 3 else 3
    diffs = [0., 0., 0.]

    for i in range(length):
        run_flag = False
        if i == 0:
            run_flag = True
        elif diffs[i-1] == weights[i-1]:  # stop the comparison if the previous part is unequal
            run_flag = True
        if run_flag:
            if v1_parts[i] == v2_parts[i]:
                diffs[i] = weights[i]
            elif (check_digit(v1_parts[i]) and check_digit(v2_parts[i])):
                diffs[i] = math.fabs(int(v1_parts[i]) - int(v2_parts[i])) / max(int(v1_parts[i]), int(v2_parts[i])) * weights[i]
            else:
                diffs[i] = jaro(v1_parts[i], v2_parts[i]) * weights[i]
    return sum(diffs)


def text_consistency(text1, text2):
    # for unstructured text like author, originator, supplier, copyright, etc.
    if check_empty(text1) and check_empty(text2) or text1 == '' and text2 == '':
        return -1
    if text1 == 'NE' or text2 == 'NE' or check_empty(text1) or check_empty(text2):
        return 0.
    else:
        if text1 == text2:
            return 1.
        return jaro(unquote(text1), unquote(text2))

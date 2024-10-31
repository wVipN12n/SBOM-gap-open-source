from code.extract import extract
from code.match import match
from loguru import logger

logger.add('logs/test-run.log')
names = 'test-sboms-names.txt'  # reponames
filenames = 'test-sboms-filenames.txt'  # filenames

ext_result_path = 'results/extracted'
match_result_path = 'results/matched'
file_path = 'test-sboms'

extract(filenames, file_path, ext_result_path)
match('cdx', ext_result_path, names, match_result_path)
match('spdx', ext_result_path, names, match_result_path)

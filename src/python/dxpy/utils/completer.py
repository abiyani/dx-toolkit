'''
This file contains utility functions for interactive scripts such as
dx for tab-completion, resolving naming conflicts, etc.
'''

import sys, os
import dxpy
from dxpy.utils.resolver import *

def startswith(text):
    return (lambda string: string.startswith(text))

def get_folder_matches(text, delim_pos, dxproj, folderpath):
    '''
    :param text: String to be tab-completed; still in escaped form
    :type text: string
    :param delim_pos: index of last unescaped "/" in text
    :type delim_pos: int
    :param dxproj: DXProject handler to use
    :type dxproj: DXProject
    :param folderpath: Unescaped path in which to search for folder matches
    :type folderpath: string
    :returns: List of matches
    :rtype: list of strings

    Members of the returned list are guaranteed to start with *text*
    and be in escaped form for consumption by the command-line.
    '''
    try:
        folder_names = map(lambda folder_name:
                               folder_name[folder_name.rfind('/') + 1:],
                           dxproj.list_folder(folder=folderpath,
                                              only='folders')['folders'])
        return filter(startswith(text),
                      map(lambda folder_name:
                              text[:delim_pos + 1] + \
                              escape_folder_str(folder_name) + \
                              '/',
                          folder_names))
    except:
        return []

def get_data_matches(text, delim_pos, dxproj, folderpath, classname=None):
    '''
    :param text: String to be tab-completed; still in escaped form
    :type text: string
    :param delim_pos: index of last unescaped "/" or ":" in text
    :type delim_pos: int
    :param dxproj: DXProject handler to use
    :type dxproj: DXProject
    :param folderpath: Unescaped path in which to search for data object matches
    :type folderpath: string
    :param classname: Data object class by which to restrict the search (None for no restriction on class)
    :type classname: string
    :returns: List of matches
    :rtype: list of strings

    Members of the returned list are guaranteed to start with *text*
    and be in escaped form for consumption by the command-line.
    '''

    try:
        results = list(dxpy.find_data_objects(project=dxproj.get_id(),
                                              folder=folderpath,
                                              recurse=False,
                                              visibility='either',
                                              classname=classname,
                                              limit=100,
                                              describe=True))
        names = map(lambda result: result['describe']['name'], results)
        return filter(startswith(text),
                      map(lambda name:
                              ('' if text == '' else text[:delim_pos + 1]) + escape_name_str(name),
                          names))
    except:
        return []

def path_completer(text, expected=None, classes=None, perm_level=None, include_current_proj=False):
    '''
    :param text: String to tab-complete to a path matching the syntax project-name:folder/entity_or_folder_name
    :type text: string
    :param expected: "folder", "entity", "project", or None (no restriction) as to the types of answers to look for
    :type expected: string
    :param classes: if expected="entity", the possible data object classes that are acceptable
    :type classes: list of strings
    :param perm_level: the minimum permissions level required, e.g. "VIEW" or "CONTRIBUTE"
    :type perm_level: string
    :param include_current_proj: Indicate whether the current project's name should be a potential result
    :type include_current_proj: boolean

    Returns a list of matches to the text and restricted by the
    requested parameters.
    '''

    # First get projects if necessary
    colon_pos = get_last_pos_of_char(':', text)
    slash_pos = get_last_pos_of_char('/', text)
    delim_pos = max(colon_pos, slash_pos)

    matches = []
    if colon_pos < 0 and slash_pos < 0:
        # Might be tab-completing a project, but don't ever include
        # whatever's set as dxpy.WORKSPACE_ID unless expected == "project"
        results = filter(lambda result: result['id'] != dxpy.WORKSPACE_ID or include_current_proj,
                         list(dxpy.find_projects(describe=True, level=perm_level)))
        matches += filter(startswith(text),
                          map(lambda result: escape_name_str(result['describe']['name']) + ':', results))

    if expected == 'project':
        return matches

    # Attempt to tab-complete to a folder or data object name
    if colon_pos < 0 and slash_pos >= 0:
        # Not tab-completing a project, and the project is unambiguous
        # (use dxpy.WORKSPACE_ID)
        if dxpy.WORKSPACE_ID is not None:
            dxproj = dxpy.get_handler(dxpy.WORKSPACE_ID)
            folderpath, entity_name = clean_folder_path(text)
            matches += get_folder_matches(text, slash_pos, dxproj, folderpath)
            if expected != 'folder':
                if classes is not None:
                    for classname in classes:
                        matches += get_data_matches(text, slash_pos, dxproj,
                                                    folderpath, classname)
                else:
                    matches += get_data_matches(text, slash_pos, dxproj,
                                                folderpath)
    else:
        # project is ambiguous, but attempt to resolve to an object or folder
        proj_ids, folderpath, entity_name = resolve_path_with_project(text, multi_projects=True)
        for proj in proj_ids:
            dxproj = dxpy.get_handler(proj)
            matches += get_folder_matches(text, delim_pos, dxproj, folderpath)
            if expected != 'folder':
                if classes is not None:
                    for classname in classes:
                        matches += get_data_matches(text, delim_pos, dxproj,
                                                    folderpath, classname)
                else:
                    matches += get_data_matches(text, delim_pos, dxproj,
                                                folderpath)
    return matches

class DXPathCompleter():
    '''
    This class can be used as a tab-completer with the modules
    readline and rlcompleter.  Note that to tab-complete data object
    names with spaces, the delimiters set for the completer must not
    include spaces.
    '''
    def __init__(self, expected=None, classes=None):
        self.matches = []
        self.expected = expected
        self.classes = classes

    def __call__(self, text, state):
        if state == 0:
            self.matches = path_completer(text, self.expected, self.classes)

        if state < len(self.matches):
            return self.matches[state]
        else:
            return None
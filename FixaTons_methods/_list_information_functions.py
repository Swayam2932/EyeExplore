import os
from FixaTons import COLLECTION_PATH


def datasets():
    ''' Lists the names of the datasets included in the collection '''
    if not os.path.exists(COLLECTION_PATH):
        return []
    return sorted([
        d for d in os.listdir(COLLECTION_PATH)
        if os.path.isdir(os.path.join(COLLECTION_PATH, d)) and not d.startswith('.')
    ])


def stimuli(DATASET_NAME):
    ''' Lists the names of the stimuli of a specified dataset '''
    stim_dir = os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI')
    if not os.path.exists(stim_dir):
        return []
    return sorted([
        f for f in os.listdir(stim_dir)
        if not f.startswith('.') and os.path.isfile(os.path.join(stim_dir, f))
    ])


def subjects(DATASET_NAME, STIMULUS_NAME):
    ''' Lists the names of the subjects which have been watching a specified stimuli of a dataset '''
    file_name, _ = os.path.splitext(STIMULUS_NAME)
    scanpath_dir = os.path.join(
        COLLECTION_PATH,
        DATASET_NAME,
        'SCANPATHS',
        file_name
    )
    if not os.path.exists(scanpath_dir):
        return []
    return sorted([
        s for s in os.listdir(scanpath_dir)
        if not s.startswith('.')
    ])
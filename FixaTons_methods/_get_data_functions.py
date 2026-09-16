#########################################################################################
import FixaTons
from FixaTons import COLLECTION_PATH

#########################################################################################

# IMPORT EXTERNAL LIBRARIES

import os
import cv2
import numpy as np
import random
import base64
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import pandas as pd
from PIL import Image

#########################################################################################

def stimulus(DATASET_NAME, STIMULUS_NAME):
    ''' Returns the matrix of pixels of a specified stimulus (RGB). '''
    stim_path = os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME)
    img = cv2.imread(stim_path, 1)
    if img is None:
        raise FileNotFoundError(f"Could not load stimulus image at {stim_path}")
    return cv2.cvtColor(img, cv2.COLOR_BGR2RGB)


def stimulus_base64_encoding(DATASET_NAME, STIMULUS_NAME):
    stim_path = os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME)
    with open(stim_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string


def stimulus_size(DATASET_NAME, STIMULUS_NAME):
    ''' Returns (width, height) of the image stimulus. '''
    stim_path = os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME)
    image = cv2.imread(stim_path, 1)
    if image is None:
        return 1920, 1080
    return image.shape[1], image.shape[0]


def fixation_map(DATASET_NAME, STIMULUS_NAME):
    ''' Returns the binary fixation map matrix of a specified stimulus. '''
    file_name, _ = os.path.splitext(STIMULUS_NAME)
    fix_dir = os.path.join(COLLECTION_PATH, DATASET_NAME, 'FIXATION_MAPS')
    if not os.path.exists(fix_dir):
        raise FileNotFoundError(f"FIXATION_MAPS folder not found in dataset {DATASET_NAME}")
    files = [f for f in os.listdir(fix_dir) if not f.startswith('.')]
    if not files:
        raise FileNotFoundError(f"No fixation maps found in {fix_dir}")
    
    # Try exact match or match by basename
    target_file = None
    for f in files:
        if os.path.splitext(f)[0] == file_name:
            target_file = os.path.join(fix_dir, f)
            break
    if not target_file:
        _, file_extension = os.path.splitext(files[0])
        target_file = os.path.join(fix_dir, file_name + file_extension)

    fixation_map = cv2.imread(target_file, 1)
    if fixation_map is None:
        raise FileNotFoundError(f"Could not load fixation map at {target_file}")
    fixation_map = fixation_map[:, :, 0]
    fixation_map[fixation_map > 0] = 1
    return fixation_map


def saliency_map(DATASET_NAME, STIMULUS_NAME):
    ''' Returns the saliency map matrix of a specified stimulus. '''
    file_name, _ = os.path.splitext(STIMULUS_NAME)
    sal_dir = os.path.join(COLLECTION_PATH, DATASET_NAME, 'SALIENCY_MAPS')
    if not os.path.exists(sal_dir):
        raise FileNotFoundError(f"SALIENCY_MAPS folder not found in dataset {DATASET_NAME}")
    files = [f for f in os.listdir(sal_dir) if not f.startswith('.')]
    if not files:
        raise FileNotFoundError(f"No saliency maps found in {sal_dir}")
        
    target_file = None
    for f in files:
        if os.path.splitext(f)[0] == file_name:
            target_file = os.path.join(sal_dir, f)
            break
    if not target_file:
        _, file_extension = os.path.splitext(files[0])
        target_file = os.path.join(sal_dir, file_name + file_extension)

    img = cv2.imread(target_file, 0)
    if img is None:
        raise FileNotFoundError(f"Could not load saliency map at {target_file}")
    return img

#########################################################################################

def scanpath(DATASET_NAME, STIMULUS_NAME, subject = 0):

    ''' This functions returns the matrix of fixations of a specified stimulus. The
        scanpath matrix contains a row for each fixation. Each row is of the type
        [x, y, initial_t, final_time]

        By default, one random scanpath is chosen between available subjects. For
        a specific subject, it is possible to specify its id on the additional
        argument subject=id. '''

    file_name, _ = os.path.splitext(STIMULUS_NAME)

    # print(file_name)

    if not subject:
        list_of_subjects = os.listdir(
            os.path.join(
                COLLECTION_PATH,
                DATASET_NAME,
                'SCANPATHS',
                file_name)
        )
        subject = random.choice(list_of_subjects)

    scanpath_file = open(
        os.path.join(
            COLLECTION_PATH,
            DATASET_NAME,
            'SCANPATHS',
            file_name,
            subject), 'r')

    # print(scanpath_file)
    scanpath_file_lines = scanpath_file.readlines()
    # print(scanpath_file_lines)

    scanpath = np.zeros((len(scanpath_file_lines), 4))

    for i in range(len(scanpath)):
        scanpath[i] = np.array(scanpath_file_lines[i].split()).astype(np.complex128)

    return scanpath


#########################################################################################

def scanpath_aoi(DATASET_NAME, STIMULUS_NAME, SUBJECTS, AOI=[], AOI_TYPE="rect"):

    ''' This functions returns a dictionary of scanpaths of a specified stimulus,
        for each given participant. The scanpath matrix contains a row
        for each fixation. Each row is of the type [x, y, initial_t, final_time]
        Each dictionary entry can be identified by Subject ID as the key.
    '''
    polygons = []
    df = pd.DataFrame()
    file_name, _ = os.path.splitext(STIMULUS_NAME)

    # for [x0, y0, x1, y1] in AOI:
    #     polygons.append(Polygon([(x0, y0), (x0+x1, y0), (x1, y0+y1), (x1, y1)]))
    if AOI_TYPE == "rect":
        for [x0, y0, x1, y1] in AOI:
            polygons.append(Polygon([(x0, y0), (x0 + x1, y0), (x1, y0 + y1), (x1, y1)]))

    else:
        for point_array in AOI:
            points = []
            for i in range(len(point_array)):
                points.append(Point(point_array[i][0],point_array[i][1]))
            points.append(Point(point_array[0][0],point_array[0][1])) # Making last point = first point to close the shape
            polygons.append(Polygon([[p.x, p.y] for p in points]))

    for SUBJECT_NAME in FixaTons.info.subjects(DATASET_NAME, STIMULUS_NAME):
        if SUBJECT_NAME in SUBJECTS:
            scanpath_file = open(
                os.path.join(
                    COLLECTION_PATH,
                    DATASET_NAME,
                    'SCANPATHS',
                    file_name,
                    SUBJECT_NAME), 'r')

            scanpath_file_lines = scanpath_file.readlines()
            scanpath_file.close()

            scanpath = np.zeros((len(scanpath_file_lines), 5))

            for i in range(len(scanpath)):
                scanpath[i, 0:4] = np.array(scanpath_file_lines[i].split()).astype(np.complex128)
                point = Point(scanpath[i, 0], scanpath[i, 1])
                for j in range(len(polygons)):
                    if polygons[j].contains(point):
                        scanpath[i, 4] = j+1

            df_subject = pd.DataFrame(scanpath, columns=['X', 'Y', 'TIME_FROM', 'TIME_TO', 'AOI'])
            df_subject['SUBJECT'] = SUBJECT_NAME
            df = pd.concat([df, df_subject])

    return df
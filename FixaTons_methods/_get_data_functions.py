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

    ''' This functions returns the matrix of pixels of a specified stimulus.

        Notice that, of course, both DATASET_NAME and STIMULUS_NAME need
        to be specified. The latter, must include file extension.

        The returned matrix could be 2- or 3-dimesional. '''

    return cv2.cvtColor(cv2.imread(os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME), 1),
                        cv2.COLOR_BGR2RGB)


#########################################################################################
def stimulus_base64_encoding(DATASET_NAME, STIMULUS_NAME):

    with open(os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME), "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return encoded_string

#########################################################################################

def stimulus_size(DATASET_NAME, STIMULUS_NAME):

    ''' This function returns the x and y dimension of the image stimulus.
    This can be used while setting range of the X and Y axes in plots. '''
    image = cv2.imread(os.path.join(COLLECTION_PATH, DATASET_NAME, 'STIMULI', STIMULUS_NAME), 1)
    # print(image.shape[0], image.shape[1], image.shape[2])
    return image.shape[1], image.shape[0]


#########################################################################################

def fixation_map(DATASET_NAME, STIMULUS_NAME):

    ''' This functions returns the matrix of pixels of the fixation map
        of a specified stimulus.

        Notice that, of course, both DATASET_NAME and STIMULUS_NAME need
        to be specified. The latter, must include file extension.

        The returned matrix is a 2-dimesional matrix with 1 on fixated
        locations and 0 elsewhere. '''

    file_name, _ = os.path.splitext(STIMULUS_NAME)

    # File extensions of the fixation maps may be different between
    # datasets, so we need a check at this point.
    # All the files in the same folder have the same extension.

    _, file_extension = os.path.splitext(
        os.listdir(
            os.path.join(
                COLLECTION_PATH,
                DATASET_NAME,
                'FIXATION_MAPS')
        )[0])

    # Get the matrix

    fixation_map = cv2.imread(
        os.path.join(COLLECTION_PATH,
                     DATASET_NAME,
                     'FIXATION_MAPS',
                     file_name+file_extension
                     ), 1)

    fixation_map = fixation_map[:, :, 0]

    fixation_map[fixation_map > 0] = 1

    return fixation_map


#########################################################################################

def saliency_map(DATASET_NAME, STIMULUS_NAME):

    ''' This functions returns the matrix of pixels of the saliency map
        of a specified stimulus. Saliency map has been obtained by convolving
        the fixation map with a proper gaussian filter (corresponding to
        one degree of visual angle).

        Notice that, of course, both DATASET_NAME and STIMULUS_NAME need
        to be specified. The latter, must include file extension.

        The returned matrix is a 2-dimesional matrix. Values are in the
        range [0,1]. '''

    file_name, _ = os.path.splitext(STIMULUS_NAME)

    # File extensions of the saliency maps may be different between
    # datasets, so we need a check at this point.
    # All the files in the same folder have the same extension.

    _, file_extension = os.path.splitext(
                            os.listdir(
                                os.path.join(
                                    COLLECTION_PATH,
                                    DATASET_NAME,
                                    'SALIENCY_MAPS')
                            )[0]
    )

    # Get the matrix
    return cv2.imread(
        os.path.join(
            COLLECTION_PATH,
            DATASET_NAME,
            'SALIENCY_MAPS',
            file_name + file_extension
        ), 0)

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
            print(scanpath_file_lines)

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
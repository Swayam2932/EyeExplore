#########################################################################################

# IMPORT EXTERNAL LIBRARIES

import FixaTons
from FixaTons import COLLECTION_PATH
#########################################################################################

# IMPORT EXTERNAL LIBRARIES

import os
import numpy as np
from shapely.geometry import Point
from shapely.geometry.polygon import Polygon
import pandas as pd
from sklearn.preprocessing import normalize

#########################################################################################

def statistics(DATASET_NAME=None):

    ''' This function compute statistics on Fixations collection.

        If a DATASET_NAME is specified, statistics computation is restricted to that
        dataset. '''

    number_of_scanpaths = 0
    fixations_per_second = 0
    saccade_length = 0

    if DATASET_NAME:
        datasets_list = (DATASET_NAME,)
    else:
        datasets_list = FixaTons.info.datasets()

    for DATASET_NAME in datasets_list:
        for STIMULUS_NAME in FixaTons.info.stimuli(DATASET_NAME):
            for SUBJECT_NAME in FixaTons.info.subjects(DATASET_NAME, STIMULUS_NAME):

                number_of_scanpaths += 1

                scanpath = FixaTons.get.scanpath(
                                DATASET_NAME, STIMULUS_NAME, SUBJECT_NAME)

                if not len(scanpath) == 0:
                    fixations_per_second += fps(scanpath)
                    saccade_length += sac_len(scanpath)
                else:
                    number_of_scanpaths -= 1

    # average it
    fixations_per_second /= number_of_scanpaths
    saccade_length /= number_of_scanpaths

    return fixations_per_second, saccade_length

def fps(scanpath):

    if len(scanpath) == 0:
        return 0
    else:
        return float(len(scanpath))/scanpath[-1, 3]

def sac_len(scanpath):

    if len(scanpath) == 0:
        return 0
    else:

        s = 0

        for i in np.arange(1, len(scanpath), 1):

            s += np.sqrt(
                        (scanpath[i, 0] - scanpath[i-1, 0]) ** 2 +
                        (scanpath[i, 1] - scanpath[i - 1, 1]) ** 2
            )

        return s / len(scanpath)


#########################################################################################

def AOI_transition_matrix(DATASET_NAME, STIMULUS_NAME, AOI, AOI_TYPE):

    polygons = []
    df = pd.DataFrame()
    file_name, _ = os.path.splitext(STIMULUS_NAME)
    print(AOI_TYPE)

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
        scanpath_file = open(
            os.path.join(
                COLLECTION_PATH,
                DATASET_NAME,
                'SCANPATHS',
                file_name,
                SUBJECT_NAME), 'r')

        scanpath_file_lines = scanpath_file.readlines()

        scanpath = np.zeros((len(scanpath_file_lines), 5))

        for i in range(len(scanpath)):
            scanpath[i, 0:4] = np.array(scanpath_file_lines[i].split()).astype(np.complex128)
            point = Point(scanpath[i, 0], scanpath[i, 1])
            for j in range(len(polygons)):
                if polygons[j].contains(point):
                    scanpath[i, 4] = j + 1

        df_subject = pd.DataFrame(scanpath, columns=['X', 'Y', 'TIME_FROM', 'TIME_TO', 'AOI'])
        df_subject['SUBJECT'] = SUBJECT_NAME
        df = pd.concat([df, df_subject])
        df.sort_values(by=['SUBJECT','TIME_FROM'], ascending=[True, True])

    #Source: https://stackoverflow.com/questions/55492109/how-to-create-a-transition-matrix-for-a-column-in-python
    #TODO: Correct logic here - (1) seperate subject-wise, (2) order the AOIs in the numpy array to same as df
    df['TRANSITION'] = df['AOI'].shift(1)  # shift forward so B transitions to C
    df['TRANS_COUNTS'] = 1  # add an arbirtary counts column for group by
    trans_matrix = df.groupby(['AOI', 'TRANSITION']).count().unstack()
    # max the columns a bit neater
    trans_matrix.columns = trans_matrix.columns.droplevel()
    trans_matrix = trans_matrix.loc[:, ~trans_matrix.T.duplicated(keep='first')]
    arr = np.nan_to_num(np.array(trans_matrix))
    normalized_trans_matrix = arr/np.sum(arr) #normalize(arr, axis=1, norm='l1') # Normalizing between 0 and 1
    return pd.DataFrame(normalized_trans_matrix)




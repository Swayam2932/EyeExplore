#########################################################################################

import os

COLLECTION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'FixaTons'
)

COLLECTION_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'data',
    'FixaTons'
)

'''
This file includes tools to an easy use of the collection of datasets. 
This tools help you in different tasks:
    - List information
    - Get data (matrices)
    - Visualize data
    - Compute metrics
'''

#########################################################################################

# IMPORT EXTERNAL LIBRARIES

import os
import cv2
import numpy as np

from FixaTons_methods import _list_information_functions as info
from FixaTons_methods import _get_data_functions as get
from FixaTons_methods import _visualize_data_functions as show
from FixaTons_methods import _visual_attention_metrics as metrics
from FixaTons_methods import _compute_statistics as stats
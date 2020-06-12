"""
Functional implementation of several basic data-augmentation transforms
for pytorch video inputs.

Sources:
- https://github.com/hassony2/torch_videovision
- https://github.com/YU-Zhiyang/opencv_transforms_torchvision
"""

import numbers
import random

import cv2
import numpy as np
import PIL
import scipy
import torch
import torchvision
from sacred import Ingredient


training_ingredient = Ingredient('augmentation')


@training_ingredient.config
def training_config():
    augmentation_fns = [
        {
            'fn': 'shuffle',
            'args': {}
        },
        {
            'fn': 'random_offset',
            'args': {
                'offset_range': [0, 3]
            }
        },
        {
            'fn': 'random_flip',
            'args': {
                'axis': 0
            }
        },
        {
            'fn': 'random_flip',
            'args': {
                'axis': 1
            }
        },
        {
            'fn': 'random_flip',
            'args': {
                'axis': 2
            }
        },
        {
            'fn': 'jitter',
            'args': {
                'brightness': [0.5]
            }
        }
    ]


INTER_MODE = {'NEAREST': cv2.INTER_NEAREST, 'BILINEAR': cv2.INTER_LINEAR, 'BICUBIC': cv2.INTER_CUBIC}


def random_offset(clip, offset_range=[0,1]):
    """
    """
    return clip[random.randint(*offset_range)::max(offset_range)]


def random_flip(clip, axis=0):
    """
    """
    if random.random() < 0.5:
        return np.flip(clip, axis)


def jitter(clip, brightness=[], contrast=[], saturation=[], hue=[]):
    """Randomly change the brightness, contrast and saturation and hue of the clip
    Args:
    clip (np.ndarray) (T, H, W, C) matrix
    dims (list) the indices of the channels to change
    brightness (float): How much to jitter brightness. brightness_factor
    is chosen uniformly from [max(0, 1 - brightness), 1 + brightness].
    contrast (float): How much to jitter contrast. contrast_factor
    is chosen uniformly from [max(0, 1 - contrast), 1 + contrast].
    saturation (float): How much to jitter saturation. saturation_factor
    is chosen uniformly from [max(0, 1 - saturation), 1 + saturation].
    hue(float): How much to jitter hue. hue_factor is chosen uniformly from
    [-hue, hue]. Should be >=0 and <= 0.5.
    """
    if isinstance(clip[0], np.ndarray):
        num_channels = clip.shape[3] # iterate through channels
        if len(brightness) == 0:
            brightness = [0] * num_channels
        if len(contrast) == 0:
            contrast = [0] * num_channels
        if len(saturation) == 0:
            saturation = [0] * num_channels
        if len(hue) == 0:
            hue = [0] * num_channels

        for i in range(num_channels):
            brightness_factor, contrast_factor, saturation_factor, hue_factor = \
                get_jitter_params(
                    brightness[i], contrast[i], saturation[i], hue[i])
            if brightness_factor != None:
                clip[:,:,:,i] = clip[:,:,:,i] * brightness_factor
            if contrast_factor != None:
                mean = round(clip[:,:,:,i].mean())
                clip[:,:,:,i] = (1 - contrast_factor) * mean + contrast_factor * clip[:,:,:,i]
            if saturation_factor != None:
                raise NotImplementedError('Saturation augmentation ' +
                                          'not yet implemented')
            if hue_factor != None:
                raise NotImplementedError('Hue augmentation not ' +
                                          'yet implemented.')

    else:
        raise TypeError('Expected numpy.ndarray ' +
                        'but got list of {0}'.format(type(clip[0])))
    return clip


def get_jitter_params(brightness, contrast, saturation, hue):
    if brightness > 0:
        brightness_factor = random.uniform(
            max(0, 1 - brightness), 1 + brightness)
    else:
        brightness_factor = None

    if contrast > 0:
        contrast_factor = random.uniform(
            max(0, 1 - contrast), 1 + contrast)
    else:
        contrast_factor = None

    if saturation > 0:
        saturation_factor = random.uniform(
            max(0, 1 - saturation), 1 + saturation)
    else:
        saturation_factor = None

    if hue > 0:
        hue_factor = random.uniform(-hue, hue)
    else:
        hue_factor = None
    return brightness_factor, contrast_factor, saturation_factor, hue_factor
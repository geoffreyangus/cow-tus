"""
"""
import os
import sys

from sacred import Experiment

# from cow_tus.models.zoo import *

ex = Experiment()

@ex.config
def my_config():
    experiment_dir = 'experiment/'
    num_epochs = 5
    resume = False

@ex.capture
def run_experiment(experiment_dir, resume):
    if os.path.isfile(os.path.join(experiment_dir, 'metrics.json')):
        if not resume:
            print('This exists!')
        else:
            print('running')

@ex.command
def build_dataset(raw_dir, out_dir):
    print('building dataset')
    print(raw_dir, out_dir)

@ex.command
def split_dataset():
    print('splitting dataset')

@ex.automain
def main():
    run_experiment()
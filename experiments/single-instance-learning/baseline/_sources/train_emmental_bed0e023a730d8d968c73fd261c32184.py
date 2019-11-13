import os
import os.path as path
import logging
from functools import partial

import emmental
from emmental import Meta
from emmental.data import EmmentalDataLoader
from emmental.learner import EmmentalLearner
from emmental.model import EmmentalModel
from emmental.scorer import Scorer
from emmental.task import EmmentalTask
import torch
import torch.nn as nn
from torchvision import transforms
from sacred import Experiment
from sacred.observers import FileStorageObserver
from sacred.utils import apply_backspaces_and_linefeeds

from cow_tus.data.transforms import training_ingredient as transforms_ingredient
from cow_tus.util.util import unpickle, ce_loss, output
from cow_tus.models.modules import zoo as modules

EXPERIMENT_NAME = 'trainer'
ex = Experiment(EXPERIMENT_NAME, ingredients=[transforms_ingredient])
ex.logger = logging.getLogger(__name__)
ex.captured_out_filter = apply_backspaces_and_linefeeds

@ex.config
def config(transforms):
    """
    Configuration for training harness.
    """
    hypothesis_conditions = ['single-instance-learning', 'baseline']
    exp_dir = path.join('experiments', *hypothesis_conditions)

    meta_config = {
        'device': 'cpu'
    }

    logging_config = {
        'evaluation_freq': 40,
        'checkpointing': False
    }

    dataset_class = 'TUSDataset'
    dataset_args = {
        'dataset_dir': 'data/split/by-animal-number/hold-out-validation',
        'labels_path': 'data/labels/globals.csv'
    }

    transforms = {
        'train': transforms['preprocess_fns'] + transforms['augmentation_fns'],
        'valid': transforms['preprocess_fns'],
        'test':  transforms['preprocess_fns'],
    }
    target_transforms = {split: None for split in transforms.keys()}

    dataloader_configs = {
        'train': {
            'batch_size': 4,
            'num_workers': 8,
            'shuffle': True
        },
        'test': {
            'batch_size': 4,
            'num_workers': 8,
            'shuffle': True
        }
    }

    task_to_label_dict = {
        '_primary': '_primary'
    }

    encoder_class = 'I3DEncoder'
    encoder_args = {
        'modality': 'flow',
        'weights_path': 'i3d/model_flow.pth'
    }

    decoder_class = "AttDecoder"
    decoder_args = {}

class TrainingHarness(object):

    def __init__(self):
        """
        """
        self._init_meta()

        self.datasets = self._init_datasets()
        self.dataloaders = self._init_dataloaders()
        self.model = self._init_model()

    @ex.capture
    def _init_meta(self, _seed, exp_dir, meta_config, learner_config, logging_config):
        emmental.init(path.join(exp_dir, '_emmental_logs'))
        Meta.update_config(
            config={
                'meta_config': {**meta_config, 'seed': _seed},
                'learner_config': learner_config,
                'logging_config': logging_config
            }
        )

    @ex.capture
    def _init_datasets(self, _log, dataset_class, dataset_args, transforms, target_transforms):
        datasets = {}
        for split in ['train', 'test']:
            datasets[split] = getattr(datasets, dataset_class)(
                name=data_config['name'],
                root=data_config['path'],
                train=True if split == 'train' else False,
                transform=transforms[split],
                target_transform=target_transforms[split],
                download=False,
            )
            _log.info(f'Loaded {split} split for {data_config["name"]}.')
        return datasets

    @ex.capture
    def _init_dataloaders(self, _log, dataloader_configs, task_to_label_dict):
        dataloaders = []
        for split in ['train', 'test']:
            dataloaders.append(
                EmmentalDataLoader(
                    task_to_label_dict=task_to_label_dict,
                    dataset=self.datasets[split],
                    split=split,
                    shuffle=dataloader_configs[split]['shuffle'],
                    batch_size=dataloader_configs[split]['batch_size'],
                    num_workers=dataloader_configs[split]['num_workers'],
                )
            )
            _log.info(f'Built dataloader for {self.datasets[split].name} {split} set.')
        return dataloaders

    @ex.capture
    def _init_model(self, encoder_class, encoder_args, decoder_class, decoder_args, input_shape, task_to_label_dict):
        encoder_module = getattr(modules)(encoder_class, pretrained=True)
        encoder_output_dim = encoder_module.get_output_dim()
        tasks = [
            EmmentalTask(
                name=task_name,
                module_pool=nn.ModuleDict(
                    {
                        f'encoder_module': encoder_module,
                        f'decoder_module_{task_name}': getattr(modules, decoder_class)(emb_dim, 2, **decoder_args),
                    }
                ),
                task_flow=[
                    {
                        'name': 'encoder_module', 'module': 'encoder_module', 'inputs': [('_input_', 'exam')]
                    },
                    {
                        'name':   f'decoder_module_{task_name}',
                        'module': f'decoder_module_{task_name}',
                        'inputs': [('encoder_module', 0)],
                    },
                ],
                loss_func=partial(ce_loss, task_name),
                output_func=partial(output, task_name),
                scorer=Scorer(metrics=['accuracy', 'roc_auc', 'precision', 'recall', 'f1']),
            )
            for task_name in task_to_label_dict.keys()
        ]
        model = EmmentalModel(name='cow-tus-model', tasks=tasks)
        return model

    def run(self):
        learner = EmmentalLearner()
        learner.learn(self.model, self.dataloaders)


@ex.config_hook
def hook(config, command_name, logger):
    if config['exp_dir'] == None:
        raise Exception(f'exp_dir is {config["exp_dir"]}')
    ex.observers.append(FileStorageObserver(config['exp_dir']))


@ex.main
def main():
    trainer = TrainingHarness()
    res = trainer.run()
    return res


if __name__ == '__main__':
    ex.run_commandline()
import unittest
import codex
from codex import config
import os.path as osp


class TestConfig(unittest.TestCase):

    def test_load_conf(self):
        # Load json configuration
        codex.set_config_default_filename('experiment.json')
        conf_dir = osp.join(codex.conf_dir, 'v0.1', 'examples', 'ex1')
        conf = codex.config.load(conf_dir)
        self.assertTrue(len(conf.channel_names) > 0)

        # Load yaml configuration
        codex.set_config_default_filename('experiment.yaml')
        conf_dir = osp.join(codex.conf_dir, 'v0.1', 'examples', 'ex1')
        conf = codex.config.load(conf_dir)
        self.assertTrue(len(conf.channel_names) > 0)

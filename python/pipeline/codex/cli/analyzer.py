#!/usr/bin/python
"""CODEX analysis CLI application"""
import fire
import codex
from codex import cli
import os.path as osp
import papermill as pm
import logging
logging.basicConfig(level=logging.INFO, format=cli.LOG_FORMAT)

class CodexAnalyzer(object):

    def _get_nb_path(self, nb_name):
        return osp.join(codex.nb_dir, 'data_analysis', nb_name)

    def processor_data(self, output_dir, filename=cli.DEFAULT_PROCESSOR_DATA_FILENAME):
        """Analyze data collected by the processing pipeline
        
        This operation will execute a parameterized notebook and print the notebook location
        (as well as how to view it) on completion.

        Args:
            output_dir: Directory containing processor output (should be same as output_dir specified
                to that application)
            filename: In the event that the processor data (json) file was given a non-default name,
                it can be specified here; otherwise, the default value should not be changed
        """
        logging.info('Running processor data analysis')
        processor_data_path = osp.join(output_dir, filename)
        nb_input_path = self._get_nb_path('processor_data_analysis.ipynb')
        nb_output_path = osp.join(output_dir, 'processor_data_analysis.ipynb')
        pm.execute_notebook(nb_input_path, nb_output_path, parameters={'processor_data_path': processor_data_path})
        logging.info('Processor data analysis complete; view with `jupyter notebook {}`'.format(nb_output_path))

    def best_focus_montage(self, config_dir, output_dir, region_indexes=None, filename=cli.DEFAULT_PROCESSOR_DATA_FILENAME):
        from codex.ops import op, best_focus
        from codex import config as codex_config
        from codex.ops import op, best_focus
        from codex.exec import montage
        from codex import io as codex_io

        config = codex_config.load(config_dir)
        if region_indexes is None:
            region_indexes = config.region_indexes

        best_focus_op = op.CodexOp.get_op_for_class(best_focus.CodexFocalPlaneSelector)
        focus_data = cli.read_processor_data(osp.join(output_dir, filename))[best_focus_op]
        focus_data = focus_data.set_index(['region', 'tile_x', 'tile_y'])['best_z']

        for ireg in region_indexes:
            logging.info('Generating montage for region %d of %d', ireg + 1, len(region_indexes))
            tiles = []
            for itile in range(config.n_tiles_per_region):
                tx, ty = config.get_tile_coordinates(itile)
                best_z = focus_data.loc[(ireg, tx, ty)]
                path = codex_io.get_best_focus_img_path(ireg, tx, ty, best_z)
                tile = codex_io.read_image(osp.join(output_dir, path))
                tiles.append(tile)
            reg_img_montage = montage.montage(tiles, config)
            path = osp.join(output_dir, 'bestFocus', 'reg{:03d}_montage.tif'.format(ireg+1))
            logging.info('Saving montage to file "%s"', path)
            codex_io.save_image(path, reg_img_montage)
        logging.info('Montage generation complete')



if __name__ == '__main__':
    fire.Fire(CodexAnalyzer)
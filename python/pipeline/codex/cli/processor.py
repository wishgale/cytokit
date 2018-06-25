#!/usr/bin/python
"""Processing pipeline CLI application"""
import fire
from codex.exec import pipeline
from codex.utils import tf_utils
from codex import config as codex_config
from codex import cli
import logging
import sys
import os
import os.path as osp


class Processor(object):

    def run(self,

            # Data and configuration locations
            data_dir, output_dir, config_path=None,

            # Data subsets to process
            region_indexes=None,
            tile_indexes=None,

            # Execution parameters
            n_workers=None,
            gpus=None,
            memory_limit=48e9,
            tile_prefetch_capacity=1,

            # Processing flags
            run_tile_generator=True,
            run_crop=True,
            run_deconvolution=True,
            run_best_focus=True,
            run_drift_comp=True,
            run_summary=True,
            run_cytometry=True,

            # Logging levels
            codex_py_log_level=logging.INFO, 
            tf_py_log_level=logging.ERROR,
            tf_cpp_log_level=logging.ERROR,

            # Bookkeeping
            record_execution=True,
            record_data=True):
        """Run processing and cytometry pipeline

        This application can execute the following operations on either raw or already processed data:
            - Drift compensation
            - Deconvolution
            - Selection of best focal planes within z-stacks
            - Cropping of tile overlap
            - Cell segmentation and quantification

        Nothing beyond an input data directory and an output directory are required (see arguments
        below), but GPU information should be provided via the `gpus` argument to ensure that
        all present devices are utilized.  Otherwise, all arguments have reasonable defaults that
        should only need to be changed in special scenarios.

        Args:
            data_dir: Path to directoring containing raw acquisition data files
            output_dir: Directory to save results in; will be created if it does not exist
            config_path: Either a directory containing a configuration file named "experiment.yaml" or a path
                to a single file; If not provided this will default to `data_dir`
            region_indexes: 1-based sequence of region indexes to process; can be specified as:
                - None: Region indexes will be inferred from experiment configuration
                - str or int: A single value will be interpreted as a single index 
                - tuple: A two-item tuple will be interpreted as a right-open range (e.g. '(1,4)' --> [1, 2, 3]) 
                - list: A list of integers will be used as is
            tile_indexes: 1-based sequence of tile indexes to process; has same semantics as `region_indexes`
            n_workers: Number of tiles to process in parallel; should generally match number of gpus and if
                the `gpus` argument is given, then the length of that list will be used as a default (otherwise
                default is 1)
            gpus: 0-based list of gpu indexes to use for processing; has same semantics as other integer
                list arguments like `region_indexes` and `tile_indexes` (i.e. can be a scalar, list, or 2-tuple)
            memory_limit: Maximum amount of memory to allow per-worker; defaults to 48G
            tile_prefetch_capacity: Number of input tiles to buffer into memory for processing; default is 1
                which is nearly always good as this means one tile will undergo processing while a second
                is buffered into memory asynchronously
            run_tile_generator: Flag indicating whether or not the source data to be processed is from un-assembled
                single images (typically raw microscope images) or from already assembled tiles (which would be the
                case if this pipeline has already been run once on raw source data)
            run_crop: Flag indicating whether or not overlapping pixels in raw images should be cropped off; this
                should generally only apply to raw images but will have no effect if images already appear to be
                cropped (though an annoying warning will be printed in that case so this should be set to False
                if not running on raw images with overlap)
            run_deconvolution: Flag indicating whether or not to run deconvolution
            run_best_focus: Flag indicating that best focal plan selection operations should be executed
            run_drift_comp: Flag indicating that drift compensation should be executed
            run_summary: Flag indicating that tile summary statistics should be computed (eg mean, max, min, etc)
            run_cytometry: Flag indicating whether or not image tiles should be segmented and quantified
            codex_py_log_level: Logging level for CODEX and dependent modules (except TensorFlow); can be
                specified as string or integer compatible with python logging levels (e.g. 'info', 'debug',
                'warn', 'error', 'fatal' or corresponding integers)
            tf_py_log_level: TensorFlow python logging level; same semantics as `codex_py_log_level`
            tf_cpp_log_level: TensorFlow C++ logging level; same semantics as `codex_py_log_level`
            record_execution: Flag indicating whether or not to store arguments and environment in
                a file within the output directory; defaults to True
            record_data: Flag indicating whether or not summary information from each operation
                performed should be included within a file in the output directory; defaults to True
        """
        # Load experiment configuration and "register" the environment meaning that any variables not
        # explicitly defined by env variables should set based on what is present in the configuration
        # (it is crucial that this happen first)
        if not config_path:
            config_path = data_dir
        exp_config = codex_config.load(config_path)
        exp_config.register_environment()

        # Initialize logging (use a callable function for passing to spawned processes in pipeline)
        def logging_init_fn():
            logging.basicConfig(level=tf_utils.log_level_code(codex_py_log_level), format=cli.LOG_FORMAT)
            tf_utils.init_tf_logging(tf_cpp_log_level, tf_py_log_level)
        logging_init_fn()

        # Save a record of execution environment and arguments
        if record_execution:
            path = cli.record_execution(output_dir)
            logging.info('Execution arguments and environment saved to "%s"', path)

        # Resolve arguments with multiple supported forms
        region_indexes = resolve_int_list_arg(region_indexes)
        tile_indexes = resolve_int_list_arg(tile_indexes)
        gpus = resolve_int_list_arg(gpus)

        # Set other dynamic defaults
        if n_workers is None:
            # Default to 1 worker given no knowledge of available gpus 
            n_workers = len(gpus) if gpus is not None else 1

        # Execute pipeline on localhost
        conf = pipeline.PipelineConfig(
            exp_config, region_indexes, tile_indexes, data_dir, output_dir,
            n_workers, gpus, memory_limit,
            tile_prefetch_capacity=tile_prefetch_capacity,
            run_crop=run_crop,
            run_deconvolution=run_deconvolution,
            run_best_focus=run_best_focus,
            run_drift_comp=run_drift_comp,
            run_summary=run_summary,
            run_tile_generator=run_tile_generator,
            run_cytometry=run_cytometry
        )
        data = pipeline.run(conf, logging_init_fn=logging_init_fn)

        if record_data:
            path = cli.record_processor_data(data, output_dir)
            logging.info('Operation summary data saved to "%s"', path)


def resolve_int_list_arg(arg):
    """Resolve a CLI argument as a list of integers"""
    if arg is None:
        return None
    if isinstance(arg, int):
        return [arg]
    if isinstance(arg, str):
        return [int(arg)]
    if isinstance(arg, tuple):
        # Interpret as range (ignore any other items in tuple beyond second)
        return list(range(arg[0], arg[1]))
    return arg


if __name__ == '__main__':
    fire.Fire(Processor)

"""
This module provides convenience functions to create experiments
"""
import numpy as np

import qcodes
from qcodes.dataset.experiment_container import load_experiment_by_name, \
    new_experiment
from qcodes.dataset.data_set import DataSet
from qcodes.sweep import SweepMeasurement

from .realtime_monitors import Plot1DSubscriber


def do_experiment(base_path, setup, sweep_object, cleanup, live_plot_axes=None,
                  return_format=None):
    """
    Perform a sweep experiment and put the result in a QCoDeS data set

    Args:
        base_path (str): Experiment database base path in the format
            <experiment_name>/<sample_name> The eventual path of the data
            set will be given by <experiment_name>/<sample_name>/<run number>
            Note: This is *not* a path on the file system. Use the
            "get_results_from_db_path" function to retrieve your data.

        setup (list): A list of tuples, e.g.
            [(function1, args1), (function2, args2), etc...]

        sweep_object: Defining the experiment

        cleanup (list): A list of tuples, e.g.
            [(function1, args1), (function2, args2), etc...]

        live_plot_axes (dict): The keys are the axis labels and the values are
            the columns to be plotted. No plots will be shown if None is given

        return_format (list): Defines in which way(s) we want to return the
            results of the experiment. Possible options are: data_set_path,
            dataid, dataset, experiment, measurement. Default value is
            "data_set_path".
    """
    # By default we only return the data set path.
    if return_format is None:
        return_format = ["data_set_path"]

    name_parts = base_path.split("/")
    experiment_name = name_parts[0]
    if len(name_parts) == 1:
        sample_name = "None"
    else:
        sample_name = "/".join(name_parts[1:])

    try:
        experiment = load_experiment_by_name(experiment_name, sample_name)
        experiment.id = experiment.exp_id  # This is needed because of a bug
        # in the "load_experiment_by_name" method
        # A PR for a fix has been submitted (PR 997)
    except ValueError:  # experiment does not exist yet
        db_location = qcodes.config["core"]["db_location"]
        DataSet(db_location)
        experiment = new_experiment(experiment_name, sample_name)

    counter = experiment.last_counter
    measurement = SweepMeasurement(exp=experiment)

    if live_plot_axes is not None:
        for live_plot_axis in live_plot_axes:
            measurement.add_subscriber(Plot1DSubscriber(live_plot_axis), {})

    # init
    for func, args in setup:
        measurement.add_before_run(func, args)

    # meas
    measurement.register_sweep(sweep_object)
    measurement.write_period = 1.0

    # end
    for func, args in cleanup:
        measurement.add_after_run(func, args)

    # perform exp
    with measurement.run() as datasaver:
        for data in sweep_object:
            datasaver.add_result(*data.items())

    dataid = datasaver.run_id
    data_set_path = f"{base_path}/{counter}"
    dataset = datasaver.dataset

    print(f"Completed measurement. Database path: {data_set_path}")

    results = {
        "data_set_path": data_set_path,
        "dataid": dataid,
        "dataset": dataset,
        "experiment": experiment,
        "measurement": measurement
    }

    return [results[k] for k in return_format]


def dataset_to_dict(results, flatten_values=False):
    data_dict = {}

    for name in [r.name for r in results.get_parameters()]:
        values = np.array(results.get_data(name))
        if flatten_values:
            values = values.flatten()

        data_dict[name] = values

    return data_dict


def get_results_from_db_path(db_path, return_as_dict=False,
                             flatten_values=False):
    """
    We define the data base path as
    "<experiment name>/<sample name>/<run number>".
    If we have used "do_experiment" to perform acquire the results, then the
    experiment name and sample name combination will be unique.
    """
    path_parts = db_path.split("/")
    experiment_name = path_parts[0]
    run_number = int(path_parts[-1])
    sample_name = "/".join(path_parts[1:-1])

    try:
        exp = load_experiment_by_name(experiment_name, sample_name)
    except ValueError:
        raise ValueError(
            "The experiment and sample name combination is not unique. "
            "Are you sure you have used the 'do_experiment' function to "
            "acquire data?"
        )

    results = exp.data_sets()[run_number]

    if return_as_dict:
        results = dataset_to_dict(results, flatten_values=flatten_values)

    return results

from experiments import do_experiment, get_results_from_db_path
from qcodes.instrument.parameter import ManualParameter
from qcodes.sweep import sweep


def main():
    x = ManualParameter("x", unit="V")
    y = ManualParameter("y", unit="V")

    m = ManualParameter("m", unit="A")
    m.get = lambda: x() ** 2

    n = ManualParameter("n", unit="A")
    n.get = lambda: x() - y() ** 2 + 16

    setup = [(lambda: None, tuple())]
    cleanup = [(lambda: None, tuple())]

    result = do_experiment(
        "cool_experiment/my_sample",
        setup,
        sweep(x, [0, 1, 2])(m),
        cleanup,
        return_format=["data_set_path"]
    )

    data_set_path = result[0]

    data = get_results_from_db_path(data_set_path, return_as_dict=True)

    print(data)

if __name__ == "__main__":
    main()

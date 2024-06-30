from pathlib import Path
from typing import Protocol
import matplotlib.pyplot as plt
from structlog import get_logger
import csv
import numpy as np

logger = get_logger()


class Problem(Protocol):
    def save(self, t: float, outdir: Path) -> None: ...


class DataCollector:
    def __init__(self, outdir: Path, problem: Problem) -> None:
        self.times = []
        self.activations = []
        self.volumes = []
        self.pressures = []
        self.problem = problem
        outdir.mkdir(exist_ok=True, parents=True)
        self.outdir = outdir
        if hasattr(problem, "comm"):
            self.comm = problem.comm
        else:
            from dolfin import MPI

            self.comm = MPI.comm_world

    def collect(
        self,
        time: float,
        activation: float,
        volume: float,
        pressure: float,
    ) -> None:
        if self.comm.rank == 0:
            logger.info(
                "Collecting data",
                time=time,
                activation=activation,
                volume=volume,
                pressure=pressure,
            )
        # print('start collecting from ', self.comm.rank)
        self.times.append(time)
        self.activations.append(activation)
        self.volumes.append(volume)
        self.pressures.append(pressure)
        self.save(time)

    @property
    def csv_file(self):
        return Path(self.outdir) / "results_data.csv"

    @property
    def figure(self):
        return Path(self.outdir) / "results.png"

    def _save_csv(self):
        with open(self.csv_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "Time [ms]",
                    "Activation [kPa]",
                    "Volume [ml]",
                    "LV Pressure [kPa]",
                ]
            )
            for time, activation, vol, pres_val in zip(
                self.times,
                self.activations,
                self.volumes,
                self.pressures,
            ):
                writer.writerow([time, activation, vol, pres_val])

    def _plot(self):
        fig, axs = plt.subplots(
            2, 2, figsize=(10, 10)
        )  # Create a figure and two subplots
        axs[0, 0].plot(self.times, self.activations)
        axs[0, 0].set_ylabel("Activation (kPa)")
        axs[0, 0].set_xlabel("Time (ms)")
        axs[0, 1].plot(self.volumes, self.pressures)
        axs[0, 1].set_ylabel("Pressure (kPa)")
        axs[0, 1].set_xlabel("Volume (ml)")
        ax2 = axs[0, 1].twinx()
        pressures_mmHg = np.array(self.pressures) * 7.50062  # Convert to mmHg
        # Plotting the same data but converted on the second y-axis
        ax2.plot(
            self.volumes, pressures_mmHg, "r-", alpha=0
        )  # invisible plot just for axis
        ax2.set_ylabel("Pressure (mmHg)")
        axs[1, 0].plot(self.times, self.outflows)
        axs[1, 0].set_ylabel("Outflow (ml/s)")
        axs[1, 0].set_xlabel("Time (ms)")
        axs[1, 1].plot(self.times, self.pressures, label="LV Pressure")
        axs[1, 1].plot(self.times, self.aortic_pressures, label="Aortic Pressure")
        axs[1, 1].legend()
        axs[1, 1].set_ylabel("Pressure (kPa)")
        axs[1, 1].set_xlabel("Time (ms)")
        ax4 = axs[1, 1].twinx()
        ax4.plot(
            self.times, pressures_mmHg, "r-", alpha=0
        )  # invisible plot just for axis
        ax4.set_ylabel("Pressure (mmHg)")
        fig.savefig(self.figure)
        plt.close(fig)

    def save(self, t: float) -> None:
        self.problem.save(t, self.outdir)
        if self.comm.rank == 0:
            # self._plot()
            self._save_csv()

    def read_csv(self):
        data = {
            "time": [],
            "activation": [],
            "volume": [],
            "lv_pressure": [],
            "aortic_pressure": [],
            "outflow": [],
        }
        with open(self.csv_file, mode="r") as file:
            csv_reader = csv.DictReader(file)
            for row in csv_reader:
                data["time"].append(float(row["Time [ms]"]))
                data["activation"].append(float(row["Activation [kPa]"]))
                data["volume"].append(float(row["Volume [ml]"]))
                data["lv_pressure"].append(float(row["LV Pressure [kPa]"]))
                data["aortic_pressure"].append(float(row["Aortic Pressure [kPa]"]))
                data["outflow"].append(float(row["Outflow [ml/ms]"]))
        return data

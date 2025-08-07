from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range

class Fluke5522A(Instrument):
    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Fluke 5522A Multifunction Calibrator",
            includeSCPI=False,
            **kwargs
        )

    @property
    def id(self):
        """ Zwraca identyfikator urządzenia """
        return self.ask("*IDN?")
    def reset(self):
        """ Zwraca identyfikator urządzenia """
        return self.ask("*RST")

    def standby(self):
        """ Przechodzi w tryb STANDBY """
        self.write("STBY")

    def operate(self):
        """ Przechodzi w tryb OPERATE (włącza wyjście) """
        self.write("OPER")

    def output_current(self, current_A, frequency_Hz=0):
        current = truncated_range(current_A, (-20.5, 20.5))
        frequency = truncated_range(frequency_Hz, (0, 300000))
        self.write("*RST")
        self.write(f"OUT {current:.6f} A, {frequency:.1f} HZ")
        self.write("*WAI")

    def output_voltage(self, value_V, frequency_Hz=0):
        """ Ustawia napięcie DC lub AC w woltach """
        voltage = truncated_range(value_V, (-1020, 1020))
        frequency = truncated_range(frequency_Hz, (0, 300000))
        self.write("*RST")
        self.write(f"OUT {voltage:.6f} V, {frequency:.6f} HZ")
        self.write("*WAI")





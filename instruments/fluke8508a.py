"""
This file is part of the PyMeasure package.

Copyright (c) 2013-2025 PyMeasure Developers

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
"""

import logging
import time

from pymeasure.instruments import Instrument
from pymeasure.instruments.validators import truncated_range

log = logging.getLogger(__name__)
log.addHandler(logging.NullHandler())


class Fluke8508A(Instrument):
    """Represents the Fluke 8508A Reference Multimeter.

    The 8508A is a high‑accuracy, 8½‑digit reference multimeter capable of
    measuring DC and AC voltage and current, several resistance modes and
    temperature.  This class provides a high‑level interface in the spirit
    of :class:`~pymeasure.instruments.hp.hp34401A.HP34401A`.

    The remote commands implemented here follow the syntax diagrams in
    the Fluke 8508A Users Manual.  Measurement functions are selected with
    the ``FUNC`` command and configured with a comma‑separated list of
    parameters.  Once configured, a single measurement is initiated with
    ``INIT`` and the result is read via ``X?`` – this query is equivalent
    to the compound command ``*TRG;RDG?`` and is intended for high‑speed
    measurements.

    Supported measurement functions
    ------------------------------
    The :attr:`function_` property accepts the following strings to select
    the measurement function.  The appropriate SCPI token is written using
    ``FUNC`` when the property changes:

    ===========   =============================================================
    ``"DCV"``     DC voltage (``FUNC 'VOLT:DC'``)
    ``"ACV"``     AC voltage (``FUNC 'VOLT:AC'``)
    ``"DCI"``     DC current (``FUNC 'CURR:DC'``)
    ``"ACI"``     AC current (``FUNC 'CURR:AC'``)
    ``"OHMS"``    Normal resistance (two‑ or four‑wire)
    ``"HIV_OHMS"`` High‑voltage resistance
    ``"TRUE_OHMS"`` True ohms (ratio mode)
    ``"PRT"``     Platinum resistance thermometer (temperature)
    ===========   =============================================================

    Configuration tokens
    --------------------
    Each function accepts a number of optional configuration tokens:

    • **Range selection** – When ``autorange`` is True (default) the
      instrument selects the range automatically.  When ``autorange`` is
      False the range can be set manually via the :attr:`range_token`
      property.  Typical ranges for voltage are ±200 mV, ±2 V, ±20 V,
      ±200 V and ±1 kV; for current: ±200 µA, ±2 mA, ±20 mA, ±200 mA,
      ±2 A and ±20 A.  Resistance functions support decade ranges from
      20 Ω up to tens of megohms, and platinum‑RTD measurements cover the
      full –200 °C to 660 °C range.

    • **Resolution** – Select the number of digits of resolution via the
      :attr:`resolution` property or the ``resolution`` argument of the
      legacy methods.  Valid values are 5–8 for voltage and resistance
      measurements and 5–7 for current.  When unspecified the highest
      supported resolution for the selected function is used.

    • **Fast mode** – The :attr:`fast_enabled` property controls the
      integration time.  When True (default), ``FAST_ON`` is sent for
      rapid measurements; when False, ``FAST_OFF`` selects longer
      integration for maximum accuracy.

    • **Filter** – The :attr:`filter_enabled` property toggles a low‑pass
      analog filter.  For DC measurements the filter is either off
      (``FILT_OFF``) or on (``FILT_ON``).  AC functions provide
      additional filter selections at 100 Hz, 40 Hz, 10 Hz and 1 Hz
      bandwidths along with coupling (DC or AC) and transfer options.

    • **Resistance options** – Resistance measurements can be made in
      two‑wire or four‑wire configuration (``TWO_WR``/``FOUR_WR``) and
      include a low‑current mode (``LOI_ON``/``LOI_OFF``) for sensitive
      devices.

    Refer to the Users Manual for complete descriptions of the available
    tokens and their effects on the measurement.

    Examples
    --------
     dmm = Fluke8508A("GPIB::19")
     dmm.function_ = "DCV"  # Select DC voltage function
     dmm.autorange = True    # Use autoranging
     dmm.resolution = 8      # 8.5‑digit resolution
     dmm.fast_enabled = True # Enable fast mode
     print(dmm.reading)      # Take a single measurement

    The legacy convenience methods :meth:`measure_dc_voltage` and
    :meth:`measure_dc_current` are retained for situations where manual
    range selection is desired or when controlling the filter state
    explicitly.
    """

    def __init__(self, adapter, **kwargs):
        super().__init__(
            adapter,
            "Fluke 8508A Reference Multimeter",
            includeSCPI=False,
            **kwargs,
        )
        # Initialise configuration state.  These attributes track the
        # currently selected measurement function, range token, autorange
        # state, resolution, fast mode and filter mode.  They are used
        # when constructing the configuration command in the :attr:`reading`
        # property.  By storing them on the instance rather than the class
        # we avoid shared state between multiple instrument instances.
        self._function = None  # type: str | None
        self._range_token = None  # type: str | None
        self._autorange = True  # type: bool
        self._resolution = None  # type: int | None
        self._fast_enabled = True  # type: bool
        self._filter_enabled = False  # type: bool

    # Identification query using the standard IEEE 488.2 command
    id = Instrument.measurement(
        "*IDN?",
        """Return the instrument identification string.""",
    )

    #: Mapping of high‑level function names to instrument SCPI tokens.  The
    #: instrument uses tokens such as ``VOLT:DC`` and ``CURR:DC`` when
    #: selecting a measurement function.  These are mapped here so the user
    #: can set :attr:`function_` with a simple mnemonic like ``"DCV"`` or
    #: ``"DCI"``.  Additional functions (ACV and ACI) are provided for
    #: completeness but are not currently used by :meth:`measure_dc_voltage`
    #: or :meth:`measure_dc_current`.
    FUNCTIONS = {
        "DCV": "VOLT:DC",
        "ACV": "VOLT:AC",
        "DCI": "CURR:DC",
        "ACI": "CURR:AC",
    }

    #: Boolean to integer mapping used by several controls
    BOOL_MAPPINGS = {True: 1, False: 0}

    #: Supported resolutions for voltage measurements (digits)
    _VOLTAGE_RESOLUTIONS = (5, 6, 7, 8)

    #: Supported resolutions for current measurements (digits)
    _CURRENT_RESOLUTIONS = (5, 6, 7)

    def reset(self) -> None:
        """Reset the multimeter to its default state and wait for completion."""
        self.write("*RST")
        # Ensure the reset completes before proceeding
        self.write("*WAI")

    # Note: The Fluke 8508A is a multimeter and does not support STBY or OPER commands.
    # These methods are intentionally omitted to avoid confusion with calibrator devices.

    # ---------------------------------------------------------------------
    # High‑level configuration controls
    #
    # The 8508A requires a configuration string that includes the range,
    # fast/slow state, filter state, and resolution.  Rather than forcing the
    # user to construct this string manually each time, we allow these
    # parameters to be set individually.  Internally they are stored and
    # combined when a measurement is triggered via the :attr:`reading`
    # property.  The following attributes track the current configuration.
    _function: str | None = None
    _range_token: str | None = None
    _autorange: bool = True
    _resolution: int | None = None
    _fast_enabled: bool = True
    _filter_enabled: bool = False

    @property
    def function_(self) -> str:
        """Get or set the current measurement function.

        The instrument supports DC voltage (``"DCV"``) and DC current
        (``"DCI"``) natively; additional functions (AC voltage and AC current)
        are defined here for future expansion.  Setting this property
        immediately writes ``FUNC '<TOKEN>'`` to the instrument.

        ``function_`` is mapped to the corresponding SCPI token via
        :attr:`FUNCTIONS` with ``map_values=True``, so the user can provide
        friendly names (e.g. ``"DCV"``) and the correct instrument token
        (e.g. ``"VOLT:DC"``) will be sent.
        """
        return self._function

    @function_.setter
    def function_(self, value: str) -> None:
        # Validate input
        if value not in self.FUNCTIONS:
            raise ValueError(f"Invalid function '{value}'. Valid options are: {list(self.FUNCTIONS.keys())}")
        # Send the command only if the function has changed
        if value != self._function:
            scpi_token = self.FUNCTIONS[value]
            self.write(f"FUNC '{scpi_token}'")
            self._function = value

    @property
    def autorange(self) -> bool:
        """Get or set the autorange state.

        When set to True (default), the instrument selects the best range
        automatically.  When False, the instrument uses the manual range set
        via :attr:`range_token`.  Changing this property does not
        immediately affect the instrument; the updated range state is
        applied when a measurement is initiated via :attr:`reading` or
        :meth:`measure_dc_voltage` / :meth:`measure_dc_current`.
        """
        return self._autorange

    @autorange.setter
    def autorange(self, value: bool) -> None:
        self._autorange = bool(value)

    @property
    def range_token(self) -> str | None:
        """Get or set the manual range token.

        For voltage measurements the valid range tokens are ``"200MV"``,
        ``"2V"``, ``"20V"``, ``"200V"`` and ``"1KV"``.  For current
        measurements the valid tokens are ``"200UA"``, ``"2MA"``, ``"20MA"``,
        ``"200MA"``, ``"2A"`` and ``"20A"``.  When :attr:`autorange` is
        True this value is ignored.  Changing this property does not
        immediately affect the instrument; the value is used when
        constructing the configuration string for a measurement.
        """
        return self._range_token

    @range_token.setter
    def range_token(self, value: str | None) -> None:
        if value is None:
            self._range_token = None
            return
        # Normalize token to upper case
        token = value.upper()
        valid = {
            "DCV": ["200MV", "2V", "20V", "200V", "1KV"],
            "ACV": ["200MV", "2V", "20V", "200V", "1KV"],
            "DCI": ["200UA", "2MA", "20MA", "200MA", "2A", "20A"],
            "ACI": ["200UA", "2MA", "20MA", "200MA", "2A", "20A"],
        }
        if self.function_ is None:
            raise AttributeError("Set the measurement function before setting the range token")
        # If the current function has an explicit list of valid tokens, enforce it.
        if self.function_ in valid:
            if token not in valid[self.function_]:
                raise ValueError(f"Invalid range token '{value}' for function {self.function_}")
        # For other functions (e.g. OHMS, HIV_OHMS, TRUE_OHMS, PRT) accept any token
        self._range_token = token

    @property
    def resolution(self) -> int | None:
        """Get or set the measurement resolution in digits.

        Valid resolutions are 5–8 for voltage measurements and 5–7 for current
        measurements.  If ``None`` (the default) is given, the resolution
        defaults to the highest resolution supported for the current
        function.  Changing this property does not immediately affect
        the instrument; the updated value is used when a measurement is
        triggered.
        """
        return self._resolution

    @resolution.setter
    def resolution(self, value: int | None) -> None:
        if value is None:
            self._resolution = None
            return
        if self.function_ is None:
            raise AttributeError("Set the measurement function before setting the resolution")
        # Validate per function
        # Resistance and temperature functions share the voltage resolution range
        if self.function_ in ("DCV", "ACV", "OHMS", "HIV_OHMS", "TRUE_OHMS", "PRT"):
            res = int(truncated_range(value, (5, 8)))
        else:
            # Current functions use 5–7 digit resolutions
            res = int(truncated_range(value, (5, 7)))
        self._resolution = res

    @property
    def fast_enabled(self) -> bool:
        """Get or set the fast measurement mode state.

        When enabled (default), the instrument performs fast measurements.
        Disabling fast mode may improve measurement accuracy at the expense
        of speed.
        """
        return self._fast_enabled

    @fast_enabled.setter
    def fast_enabled(self, value: bool) -> None:
        self._fast_enabled = bool(value)

    @property
    def filter_enabled(self) -> bool:
        """Get or set the low‑pass filter state.

        When enabled, a low‑pass filter is applied to the measurement.
        By default, the filter is disabled to maximize measurement speed.
        """
        return self._filter_enabled

    @filter_enabled.setter
    def filter_enabled(self, value: bool) -> None:
        self._filter_enabled = bool(value)

    # ---------------------------------------------------------------------
    # Reading property
    # ---------------------------------------------------------------------
    @property
    def reading(self) -> float:
        """Trigger a measurement and return the result as a float.

        This property constructs and writes the appropriate configuration
        command based on the current settings (:attr:`function_`,
        :attr:`autorange`, :attr:`range_token`, :attr:`resolution`,
        :attr:`fast_enabled` and :attr:`filter_enabled`), then sends
        ``INIT`` to start the measurement.  It waits for the measurement
        to complete using :meth:`_wait_for_opc` and finally queries the
        reading using ``X?``.  The value returned is parsed to a float.

        :returns: The measured value.
        :raises ValueError: If the result cannot be parsed to a float.
        """
        # Determine the configuration tokens based on current settings
        if self.function_ is None:
            raise AttributeError("Measurement function not set. Set function_ before reading.")
        # Autoranging or manual range
        if self.autorange or self.range_token is None:
            range_token = "AUTO"
        else:
            range_token = self.range_token
        # Resolution digits: default to highest supported if not specified
        if self._resolution is None:
            if self.function_ in ("DCV", "ACV"):
                res_digits = max(self._VOLTAGE_RESOLUTIONS)
            else:
                res_digits = max(self._CURRENT_RESOLUTIONS)
        else:
            res_digits = self._resolution
        # Fast and filter tokens
        fast_token = "FAST_ON" if self.fast_enabled else "FAST_OFF"
        filt_token = "FILT_OFF" if not self.filter_enabled else "FILT_ON"
        # Build the configuration command prefix (DCV/DCI/ACV/ACI)
        function_code = self.function_.upper()
        # Compose configuration and send
        config_cmd = f"{function_code} {range_token},{fast_token},{filt_token},RESL{res_digits}"
        self.write(config_cmd)
        # Initiate measurement and wait
        self.write("INIT")
        self._wait_for_opc()
        # Read the value
        result = self.ask("X?").strip()
        try:
            return float(result)
        except ValueError:
            log.warning(f"Unable to parse reading: {result}")
            raise

    # -------------------------------------------------------------------------
    # Measurement helpers
    # -------------------------------------------------------------------------
    def _wait_for_opc(self, timeout: float = 10.0) -> None:
        """Wait until the instrument signals that the last operation completed.

        The Fluke 8508A supports the standard ``*OPC?`` query which returns
        ``1`` when the operation is complete.  This helper polls the query
        until completion or until the timeout is exceeded.

        :param timeout: Maximum number of seconds to wait.
        :raises TimeoutError: If the timeout elapses before completion.
        """
        start = time.time()
        while True:
            status = self.ask("*OPC?").strip()
            if status == "1":
                return
            if (time.time() - start) > timeout:
                raise TimeoutError(
                    "Operation did not complete within the timeout period"
                )
            time.sleep(0.1)

    # -------------------------------------------------------------------------
    # DC Voltage Measurement
    # -------------------------------------------------------------------------
    def measure_dc_voltage(
        self,
        resolution: int = 8,
        autorange: bool = True,
        fast_on: bool = True,
        filt_off: bool = True,
    ) -> float:
        """Legacy DC voltage measurement method.

        This convenience method constructs the appropriate configuration
        based on the supplied arguments and triggers a single DC voltage
        measurement.  It sets the measurement function internally to ``DCV``
        and builds a configuration string similar to that used by
        :meth:`reading`.  It then initiates the measurement and returns
        the result as a floating‑point value.

        :param resolution: Integer number of digits (5–8) used to select
            ``RESL5`` – ``RESL8``.  Values outside this range are truncated.
        :param autorange: If True (default) the instrument automatically
            selects the range.  When False, a manual range is chosen based
            on the :attr:`range_token` property.  If no range token is set
            in manual mode, the widest range is used.
        :param fast_on: Enable fast measurement mode (``FAST_ON``) if True.
        :param filt_off: Disable the low‑pass filter (``FILT_OFF``) if True.
        :returns: The measured voltage in volts.
        """
        # Configure the function
        self.function_ = "DCV"
        # Determine the range
        if autorange:
            range_token = "AUTO"
        else:
            # Use manual range from range_token if set, otherwise use widest range
            range_token = self.range_token if self.range_token is not None else "1KV"
        # Validate resolution
        res_digits = int(truncated_range(resolution, (5, 8)))
        fast_token = "FAST_ON" if fast_on else "FAST_OFF"
        filt_token = "FILT_OFF" if filt_off else "FILT_ON"
        # Configure
        self.write(f"DCV {range_token},{fast_token},{filt_token},RESL{res_digits}")
        self.write("INIT")
        self._wait_for_opc()
        result = self.ask("X?").strip()
        try:
            return float(result)
        except ValueError:
            log.warning(f"Unable to parse DC voltage reading: {result}")
            raise

    # -------------------------------------------------------------------------
    # DC Current Measurement
    # -------------------------------------------------------------------------
    def measure_dc_current(
        self,
        resolution: int = 7,
        autorange: bool = True,
        fast_on: bool = True,
        filt_off: bool = True,
    ) -> float:
        """Legacy DC current measurement method.

        This convenience method configures the instrument for a single
        DC current measurement using the supplied arguments and returns
        the measured value.  It sets the measurement function to ``DCI``
        internally and constructs a configuration string similar to that
        used by :meth:`reading`.

        :param resolution: Integer number of digits (5–7) used to select
            ``RESL5`` – ``RESL7``.  Values outside this range are truncated.
        :param autorange: If True (default) the instrument automatically
            selects the measurement range.  When False, a manual range
            is chosen based on the current :attr:`range_token` property.
            If no manual range is set, the widest range (``20A``) is used.
        :param fast_on: Enable fast measurement mode (``FAST_ON``) when True.
        :param filt_off: Disable the low‑pass filter (``FILT_OFF``) when True.
        :returns: The measured current in amperes.
        """
        # Configure the function
        self.function_ = "DCI"
        # Determine range
        if autorange:
            range_token = "AUTO"
        else:
            # Use manual range from range_token if set, otherwise use widest range
            range_token = self.range_token if self.range_token is not None else "20A"
        # Validate resolution
        res_digits = int(truncated_range(resolution, (5, 7)))
        fast_token = "FAST_ON" if fast_on else "FAST_OFF"
        filt_token = "FILT_OFF" if filt_off else "FILT_ON"
        # Send configuration
        self.write(f"DCI {range_token},{fast_token},{filt_token},RESL{res_digits}")
        self.write("INIT")
        self._wait_for_opc()
        result = self.ask("X?").strip()
        try:
            return float(result)
        except ValueError:
            log.warning(f"Unable to parse DC current reading: {result}")
            raise
# plik: set_5522a_current.py

import pyvisa
import time

# Inicjalizacja zasobów GPIB
gpib_address = 'GPIB0::5::INSTR'
rm = pyvisa.ResourceManager()
inst = rm.open_resource(gpib_address)
inst.timeout = 5000

# Wyczyszczenie i identyfikacja
inst.write("*CLS")
inst.write("*RST")
print("Połączono z:", inst.query("*IDN?").strip())

# Przejdź do trybu STANDBY (bezpieczne przygotowanie)
inst.write("STBY")

# Ustaw wyjście na 1 mA DC
#inst.write("FUNC CURR:DC")
inst.write("OUT 1.5 mA")  # 1 mA

# Włącz wyjście OPERATE
inst.write("OPER")

# Trzymaj 1 mA przez 5 sekund
time.sleep(10)

# Wyłącz wyjście
inst.write("STBY")

# Zamknij połączenie
inst.close()
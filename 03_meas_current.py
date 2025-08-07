# plik: 02_meas_voltage.py

import pyvisa
import time

# Inicjalizacja GPIB
rm = pyvisa.ResourceManager()
inst = rm.open_resource('GPIB0::19::INSTR')  # Adres GPIB urządzenia 8508A
inst.timeout = 10000  # Timeout w ms

# Wyczyszczenie i identyfikacja
inst.write("*CLS")
print("Połączono z:", inst.query("*IDN?").strip())

# Konfiguracja pomiaru DC Voltage
inst.write("*RST")
inst.write("FUNC 'CURR:DC'")
inst.write("DCI AUTO,FAST_ON,FILT_OFF,RESL7")
#inst.write("VOLT:DC:NPLC 100")      # Rozdzielczość 8.5 cyfry
#inst.write("TRIG:SOUR IMM")        # Natychmiastowe wyzwolenie
#inst.write("SAMP:COUN 1")          # Jedna próbka
#inst.write("TRIG:DEL 0.1")         # Czas ustalania

# Lista na wyniki
odczyty = []

# Pętla 10 pomiarów
for i in range(10):
    inst.write("INIT")
    # Czekaj na zakończenie pomiaru (*OPC? zwróci '1')
    while True:
        if inst.query("*OPC?").strip() == '1':
            break
        time.sleep(0.1)
    #wynik = inst.query("FETC?").strip()
    wynik = inst.query("X?").strip()
    #wynik=0
    odczyty.append(float(wynik))
    print(f'Pomiar {i+1}: {wynik} A')

# Zakończenie
inst.close()

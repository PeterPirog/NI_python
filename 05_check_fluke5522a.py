from instruments.fluke5522a import Fluke5522A
import time
instr = Fluke5522A("GPIB::5")

print("ID:", instr.id)

instr.standby()
instr.output_current(-0.1)
instr.operate()
time.sleep(5)


instr.standby()
instr.output_current(0.1)
instr.operate()
time.sleep(5)


instr.standby()
instr.output_current(0.1,100)
instr.operate()
time.sleep(5)


instr.standby()
instr.output_voltage(-5)
instr.operate()
time.sleep(5)

instr.standby()
instr.output_voltage(5)
instr.operate()
time.sleep(5)

instr.standby()
instr.output_voltage(5,100)
instr.operate()
time.sleep(5)
instr.standby()
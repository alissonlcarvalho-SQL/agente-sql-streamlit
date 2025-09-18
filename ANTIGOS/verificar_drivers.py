
import pyodbc

print("Drivers ODBC disponíveis:")
for driver in pyodbc.drivers():
    print("-", driver)

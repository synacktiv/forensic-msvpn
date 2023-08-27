import pyodbc
import sys
from pathlib import Path
import csv
import ipaddress
import datetime


def convert_windows_epoch_to_date(timestamp: int):
    windows_epoch = datetime.datetime(1601, 1, 1)
    timestamp = timestamp / 10_000_000  # Adjust the timestamp by dividing by 10,000,000

    date = windows_epoch + datetime.timedelta(seconds=timestamp)

    return str(date)

def convert_bytes_to_ip(bip: bytes):
    if len(bip) <= 4 or len(bip.rstrip(b"\x00"))==4:
        try:
            ipv4_address = ipaddress.IPv4Address(bip[:4])
            return str(ipv4_address)
        except ipaddress.AddressValueError as e:
            print(f"Error ipv4: {e}")
    else:
        try:
            ipv6_address = ipaddress.IPv6Address(bip)
            return str(ipv6_address)
        except ipaddress.AddressValueError as e:
            print(f"Error ipv6: {e}")


if len(sys.argv) < 2:
    print("usage: python dump_wid.py <output_dir>")
    exit()

output_directory = Path(sys.argv[1])

# Connection settings
server = r'np:\\.\pipe\MICROSOFT##WID\tsql\query'
database = 'RaAcctDb'
trusted_connection = 'yes'  # Use Windows authentication

# Establish the connection
connection_string = (
    r'DRIVER={SQL Server};'
    f'SERVER={server};'
    f'DATABASE={database};'
    f'Trusted_Connection={trusted_connection};'
)
connection = pyodbc.connect(connection_string)

# Create a cursor
cursor = connection.cursor()

# List of tables to export
tables_to_export = ['ConnectionTable', 'SessionTable', 'ServerEndpointTable', 'EndpointsAccessedTable']

# IPv4 and/or IPv6 column names to convert from bytes-encoding (hexadecimal)
ip_columns = ['ClientIPv4Address', 'ClientIPv6Address', 'ClientISPAddress', 'ServerIpAddress']

# Time column names (windows epoch)
time_columns = ['SessionStartTime']

# Export data to CSV files
for table_name in tables_to_export:
    select_query = f"SELECT * FROM {table_name}"
    cursor.execute(select_query)
    rows = cursor.fetchall()
    
    csv_file_path = Path(output_directory, f"{table_name}.csv")
    
    # Write data to CSV file
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csv_file:
        csv_writer = csv.writer(csv_file)
        
        # Write header
        column_names = [column[0] for column in cursor.description]
        csv_writer.writerow(column_names)
        
        # Write data rows. We need this loop for the conversion. Might be optimized...
        for row in rows:
            converted_row = list(row)
            
            # Convert known IPv4 columns to human-readable format
            for i, column_name in enumerate(column_names):
                if column_name in ip_columns and isinstance(row[i], bytes):
                    converted_row[i] = convert_bytes_to_ip(row[i])
                elif column_name in time_columns and isinstance(row[i], int):
                    converted_row[i] = convert_windows_epoch_to_date(row[i])
            
            csv_writer.writerow(converted_row)

# Close the cursor and connection
cursor.close()
connection.close()
import sys, time, csv, pyfiglet, getpass, re, os

from colorama import Fore, Back, Style
from colorama import init
from netmiko import ConnLogOnly
from datetime import datetime
from tqdm import tqdm

# This script is used to do interface config comparisons for multiple devices with multiple configs against a template file.
# By rdt042web@gmail.com

# Version 1 - Initial release
# Version 2 - Added netmiko device_type for nexus

# Variables
usr = pwd = None
csvFileName = "devices.csv"
outputFile = "output.txt"

# For colorama!
# Colorama colors are - Black, Red, Green, Blue, Yellow, Magenta, Cyan, and White
init()
SB = Style.BRIGHT
SR = Style.RESET_ALL

# --------------- COMMON FUNCTIONS START ---------------

def input_tester(msg, test, finish):
    # "msg" to display on cli, "test" to run
    # "finish" bool only ~True~ in case of "n" is a choice AND for an exit condition
    myinput = input(msg).lower()
    while True:
        if not bool(myinput) or re.search(test, myinput):
            myinput = input('Input not accepted\nDo it again\n--> ')
            continue
        elif finish and (myinput == 'n' or myinput == 'N'): 
            sys.exit(SB + Fore.RED + 'Exiting: Please re-check and re-run when ready.' + SR)
        else:
            return myinput 

# Function to get username and password
def getusrpass():
    global usr, pwd
    usr = input('\nUsername : ')
    pwd = getpass.getpass('Device password : ')
    return usr, pwd

# Report on how many devices will be tested from the csv
def count_csv():
    global count
    with open(csvFileName) as csvFile:
        devicesDict = csv.DictReader(csvFile) 
        count = len(list(devicesDict))
        return count

# Function to read devices from a CSV file and generate a device list
def dev_list(csv_file_name, model):
    device_list = []
    with open(csv_file_name, newline='') as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            cisco_dict = {
                'host': row['hostname'],
                'device_type': model,
                'username': usr,
                'password': pwd,
            }
            device_list.append(cisco_dict)
    return device_list

# --------------- COMMON FUNCTIONS END ---------------

# Process the template file, return list of template lines
def read_template(template_file_name):
    with open(template_file_name, 'r') as template_file:
        return [line.strip() for line in template_file if line.strip()]

# Parse interface configurations from the device configuration
def parse_interface_config(config):
    interfaces = {}  # Dictionary for interface configurations
    lines = config.splitlines()  # Split config into lines
    current_interface = None  # Track current interface
    current_lines = []  # Store lines of current interface config

    # Select delimiter
    if check3 == 'i':
        delimeter = '!' # For IOS
    else:
        delimeter = '' # For Nexus

    for line in lines:
        line = line.strip()  # Strip leading/trailing whitespaces

        # Check if line indicates the start of new interface section
        if line.startswith('interface '):  
            if current_interface:  # If an interface section was being processed
                # Store the current interface's lines in interfaces dictionary
                # key - current_interfaces / value - current_lines
                interfaces[current_interface] = current_lines  
            current_interface = line  # Update current interface to new interface
            current_lines = []  # Reset lines list
       
        # If inside an interface section       
        elif current_interface:  
            # Delimiter is end of the interface section
            if line == delimeter:  
                interfaces[current_interface] = current_lines  
                current_interface = None  # Reset current interface
            
            # Add the line to the current interface's lines
            else:
                current_lines.append(line)  

    # For last interface if no delimiter or new interface following
    # Ensure last interface is stored - contingency/
    if current_interface:
        interfaces[current_interface] = current_lines

    return interfaces  

# Compare interface configuration to the template and return differences
def compare_interface_with_template(interface_lines, template_lines):
    # Convert template and interface lines to set for comparisons
    interface_set = set(interface_lines) 
    template_set = set(template_lines)  

    # Lines in template but not in inteface
    missing_lines = [line for line in template_lines if line not in interface_set]
    # Lines in in interface but not template
    extra_lines = [line for line in interface_lines if line not in template_set]

    return missing_lines, extra_lines

# Write diffs between interface configuration and the template for each interface.
def print_interface_differences(hostname, interfaces, template_lines, file):
    file.write(f'\n\n===== {hostname} Output =====\n')

    # Iterate over each interface and its lines in the interfaces dictionary
    # .items() method for dictionary
    for interface, lines in interfaces.items():
        file.write(f'\n{interface}\n')
        missing_lines, extra_lines = compare_interface_with_template(lines, template_lines)

        # Write missing lines if there are any
        if missing_lines:
            file.write('  Missing template lines:\n')
            for line in missing_lines:
                file.write(f'    {line}\n')

        # Write extra lines if there are any
        if extra_lines:
            file.write('\n  Extra lines:\n')
            for line in extra_lines:
                file.write(f'    {line}\n')

# --------------- MAIN ---------------

# Main execution
if __name__ == '__main__':
    csv_file_name = 'devices.csv'
    template_file_name = 'template.txt'
    
    banner = pyfiglet.figlet_format('ABC CISCO INTERFACE COMPARER', font='digital')
    print(SB + Fore.GREEN + banner + SR)
    print()

    print('This script will compare a reference interface template to a group of devices and their interfaces.')
    print()
    print('\n' + SB + Fore.CYAN + 'Confirm devices.csv is the correct list of devices to run this script on? (y/n) : ' + SR)
    print('devices.csv MUST be in the same directory this script is run from.')
    check1 = input_tester('>> : ','[^YyNn]',True)

    print('\n' + SB + Fore.CYAN + 'Confirm template.txt is the correct ref interface template to run against the devices in devices.csv (y/n) : ' + SR)
    print('template.txt MUST be in the same directory this script is run from.')
    print('template.txt should not include the line starting with "interface" itself')
    check2 = input_tester('>> : ','[^YyNn]',True)

    print('\n' + SB + Fore.CYAN + 'Run interface comparison against (i)os or (n)exus devices : ' + SR)
    check3 = input_tester('>> : ','[^IiNn]',False)
    if check3 == 'i': 
        model = 'cisco_ios'
    else:
        model = 'cisco_nxos'

    print('\n' + SB + Fore.CYAN + 'Enter credentials :'  + SR)
    getusrpass()

    count_csv()

    print(f'\n' + SB + Fore.GREEN + f'Loaded {count} devices from {csvFileName} to run the comparison against.' + SR)
    
    print('\nExecuting script. Standby....')
    print()
    
    template_lines = read_template(template_file_name)
    
    device_list = dev_list(csv_file_name, model)

    t1 = time.time()  

    # Initialize tqdm progress bar
    with tqdm(total=len(device_list), desc="Comparing devices", ncols=100, 
        colour='green', bar_format='{desc}: {percentage:.0f}%|{bar}| {n}/{total}') as pbar:

        # Open the output file for writing.
        with open(outputFile, 'w') as f:
            # Write header only once
            f.write(('-' * 60) + '\n')
            now = datetime.now()
            dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
            f.write(f'This output generated by the "{os.path.basename(__file__)}" script.\n')
            f.write(f'Run commenced :   {dt_string}\n')
            f.write('\n')
            f.write(f'Interfaces config comparison run against "{template_file_name}".\n')
            f.write('>>>>\n')
            for line in template_lines:
                f.write(' ' + line + '\n') # writes need \n help!
            f.write('\n')
            f.write(('-' * 60) + '\n')
            
            for device in device_list:
                hostname = device['host']
                conn = ConnLogOnly(**device)
                if conn is None:
                    sys.exit("Logging in failed")

                config = conn.send_command('show running-config')

                interfaces = parse_interface_config(config)

                print_interface_differences(hostname, interfaces, template_lines, f)
                
                # Update tqdm progress bar
                pbar.update(1)    

    t2 = time.time() 
    print()
    print('-' * 60)
    print()
    print(f'Script run time is {t2-t1:.1f} seconds')
    print('Output saved to ' + SB + Fore.YELLOW + f'{outputFile}' + SR + ' in the same directory the script was run from.' )

# ~ SCRIPT END ~

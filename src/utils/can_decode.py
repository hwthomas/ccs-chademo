#
# This program reads a CAN log from a file written in csv format
# and generates CAM messages to be passed to the decode program
# which understands each ID meaning and layout
#

# An example csv file:
# 01/01/2016, 4
# 02/01/2016, 2
# 03/01/2016, 10
# 04/01/2016, 8

#code:- 

import csv      # this is general code examples to read from a csv file

with open('file.csv') as csvDataFile:
    csvReader = csv.reader(csvDataFile)
    for row in csvReader:
        print(row)
        

# We import the csv module. We read every row in the file. 
# Every row is returned as an array and can be accessed as such.
# to print the first cells we could simply write: 
#
# print(row[0])
#
# If we want the data in arrays, we can achieve that using:

import csv
dates = []
scores = []
with open('file.csv') as csvDataFile:
    csvReader = csv.reader(csvDataFile)
    for row in csvReader:
        dates.append(row[0])
        scores.append(row[1])
        
print(dates)
print(scores)

# simple readline from file 'short.log'

Time Stamp,ID,Extended,Dir,Bus,LEN,D1,D2,D3,D4,D5,D6,D7,D8
-1688467643383897,00000201,false,Rx,0,8,02,00,00,00,00,00,00,00,
-1688467643373880,00000700,false,Rx,0,8,01,02,00,00,06,00,00,00,
-1688467643363869,00000202,false,Rx,0,8,01,01,01,00,00,00,00,00,
-1688467643355760,00000108,false,Rx,0,8,00,F4,01,87,B3,01,00,00,


file_path = 'input.txt'
with open(file_path, 'r') as file:
    lines = file.readlines()

#or read 1 line    
with open("short.log") as file:
    print(file.readline())    

# This loop prints 1 line at a time    
with open("short.log") as file:
    for line in file:
        print(line)    

>>> with open(file_path,'r') as file:
...     for line in file:
...         print(line)
...         ts = line[0:17]
...         len = line[38]
...         id = line[23:26]
...         print("ts = ", ts, "len = ", len, "id = ", id)

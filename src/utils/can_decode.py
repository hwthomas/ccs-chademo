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

#
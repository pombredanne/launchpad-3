#!/usr/bin/python

import os
import string


inFileName = 'fm-projects.rdf'
#inFileName = 'test.rdf'

def rdfsplit(inFileName, outputDir='/home/freshmeat/'):
    outFileSuffix = '.xml'

    # Read in the whole rdf file
    rdfLines = open(inFileName).readlines()

    line = 0
    maxLines = len(rdfLines)
    header = rdfLines[0:3]
    footer = rdfLines[maxLines-1:maxLines]

    # Process file, extracting all <project>...</project> sections
    # and storing them in individual .xml files
    #
    while line < maxLines:
        while line < maxLines and rdfLines[line] <> '  <project>\n':
            line = line + 1

        if line == maxLines:
            break

        projStartLine = line

        while rdfLines[line][:23] <> '    <projectname_short>':
            line = line + 1

        projName = string.split(string.split(rdfLines[line],'>')[1],'<')[0]

        while rdfLines[line] <> '  </project>\n':
            line = line + 1

        projEndLine = line + 1

        #print projName+outFileSuffix

        outFileName = outputDir + projName + outFileSuffix

        outFile = open(outFileName, 'w')

        for outLine in header:
            outFile.write(outLine)

        for outLine in rdfLines[projStartLine:projEndLine]:
            outFile.write(outLine)

        for outLine in footer:
            outFile.write(outLine)

        outFile.close()

if __name__=='__main__':
    rdfsplit(inFileName, '/home/freshmeat/')

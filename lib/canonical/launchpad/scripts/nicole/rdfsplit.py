#!/usr/bin/python

import os
import string
from optparse import OptionParser


def rdfsplit(inFileName, outputDir):
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
        destfile = projName + outFileSuffix
        
        if not os.access(outputDir, os.F_OK):
            os.mkdir(outputDir)
                
        outFileName = os.path.join (outputDir, destfile) 

        outFile = open(outFileName, 'w')

        for outLine in header:
            outFile.write(outLine)

        for outLine in rdfLines[projStartLine:projEndLine-1]:
            outFile.write(outLine)

        # Write the <local_status> line.
        outFile.write('    <local_status>NEW</local_status>\n')
        
        for outLine in rdfLines[projEndLine-1:projEndLine]:
            outFile.write(outLine)

        for outLine in footer:
            outFile.write(outLine)

        outFile.close()

if __name__=='__main__':
    parser = OptionParser()

    parser.add_option("-f", "--file", dest="filename",
                      help="Freashmeat RDF file",
                      metavar="FILE",
                      default="fm-projects.rdf")

    parser.add_option("-d", "--dir", dest="directory",
                      help="XML directory",
                      metavar="DIR",
                      default="freshmeat")

    (options,args) = parser.parse_args()
    
    FILE = options.filename
    DIR = options.directory

    rdfsplit(FILE, DIR)

#FLM: Input TrueType Hints

__copyright__ = __license__ =  """
Copyright (c) 2013 Adobe Systems Incorporated. All rights reserved.
 
Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"), 
to deal in the Software without restriction, including without limitation 
the rights to use, copy, modify, merge, publish, distribute, sublicense, 
and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:
 
The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.
 
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, 
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER 
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING 
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER 
DEALINGS IN THE SOFTWARE.
"""

__doc__ = """
Input TrueType Hints as coordinates v1.0 - Mar 2015

This FontLab macro will read an external simple text file containing
TrueType instructions for each glyph, and will apply that data to the
glyphs. The hints can be further edited and written out using the macro
named "Output TrueType Hints".

==================================================
Versions:

v1.2 - Mar 23 2015 - Enable instructions in x-direction
v1.1 - Sep 07 2013 - Enabled the reading of 'tthints' files with an optional column for glyph color mark
v1.0 - Jan 07 2013 - Initial release
"""

#----------------------------------------

kTTHintsFileName = "tthints_coords"
debugMode = False

#----------------------------------------

vAlignLinkTop = 1
vAlignLinkBottom = 2
vAlignLinkNear = 8
vSingleLink = 4
vDoubleLink = 6
vInterpolateLink = 14

hAlignLinkNear = 7
hSingleLink = 3
hDoubleLink = 5
hInterpolateLink = 13

vMidDelta = 21
vFinDelta = 23
hMidDelta = 20
hFinDelta = 22


deltas = map(int, [hMidDelta, hFinDelta, vMidDelta, vFinDelta])
interpolations = map(int, [hInterpolateLink, vInterpolateLink])
links = map(int, [hSingleLink, hDoubleLink, vSingleLink, vDoubleLink])
anchors = map(int, [vAlignLinkTop, vAlignLinkNear, vAlignLinkBottom, hAlignLinkNear])

k1NodeIndexList = [vAlignLinkTop, vAlignLinkBottom, vAlignLinkNear, hAlignLinkNear]
k2NodeIndexList = [vSingleLink, vDoubleLink, hSingleLink, hDoubleLink]
k3NodeIndexList = [vInterpolateLink, hInterpolateLink]

#----------------------------------------

import os
from FL import *


def readTTHintsFile(filePath):
	file = open(filePath, "r")
	data = file.read()
	file.close()
	lines = data.splitlines()

	ttHintsList = []
	
	for i in range(len(lines)):
		line = lines[i]
		# Skip over blank lines
		line2 = line.strip()
		if not line2:
			continue
		# Skip over comments
		if line.find('#') >= 0:
			continue
		else:
			ttHintsList.append(line)
	
	return ttHintsList


def transformItemList(glyph, itemList):
	'''
	Transforms an item list with point coordinates to an itemList with point indices, for instance:

		input:  [4, (155, 181), (180, 249), 0, -1]
		output: [4, 6, 9, 0, -1]	

		input:  [3, 'BL', (83, 0), 0, -1]
		output: [3, 34, 0, 0, -1]

	'''

	pointDict = {(point.x, point.y): pointIndex for pointIndex, point in enumerate(glyph.nodes)}

	output = []
	for item in itemList:
		if item == 'BL':
			'bottom left hinted'
			output.append(len(glyph))
		elif item == 'BR':
			'bottom right hinted'
			output.append(len(glyph) + 1)
		elif isinstance(item, tuple):
			'point coordinates'
			pointIndex = pointDict.get(item, None)
			if pointIndex == None:
				print '\tERROR: point %s does not exist in glyph %s.' % (item, glyph.name)
			output.append(pointIndex)
		else:
			'other hinting data, integers'
			output.append(item)

	if None in output:
		print '\tERROR: could not read recipe of glyph %s' % glyph.name
		return
	else:
		return output


def applyTTHints(ttHintsList):
	glyphsHinted = 0
	for item in ttHintsList:
		hintItems = item.split("\t")
		
		if len(hintItems) == 3:
			continue

		elif len(hintItems) == 2:
			hintItems.append(80) # green mark color
		
		else:
			print "ERROR: This hint definition does not have the correct format\n\t%s" % item
			continue

		gName, gHintsString, gMark = hintItems
		gIndex = fl.font.FindGlyph(gName)
		
		if gIndex != -1:
			glyph = fl.font[gName]
		else:
			print "ERROR: Glyph %s not found in the font." % gName
			continue
		
		if not len(gHintsString.strip()):
			print "WARNING: There are no hints defined for glyph %s." % gName
			continue

		gHintsList = gHintsString.split(";")
		
		# dictionary from point coordinate to point index

		tth = TTH(glyph)
		tth.LoadProgram(glyph)
		tth.ResetProgram()
		
		if debugMode:
			print gName
		
		for item in gHintsList:
			itemList = list(eval(item))

			if len(itemList) < 3:
				print "ERROR: A hint definition for glyph %s does not have enough parameters: %s" % (gName, item)
				continue
			
			try:
				commandType = itemList[0]
			except:
				print "ERROR: A hint definition for glyph %s has an invalid command type: %s" % (gName, item)
				continue
			
			# Create the TTHCommand
			try:
				ttc = TTHCommand(commandType)
			except RuntimeError:
				print "ERROR: A hint definition for glyph %s has an invalid command type: %s\n\t\tThe first value must be within the range 1-23." % (gName, item)
				continue
			
			# # Remove the first item of the list (i.e. the command type)
			# del(itemList[0])
			
			# Determine how many parameters to consider as node indexes
			# if commandType in k1NodeIndexList: # the instruction is an Align Link (top or bottom), so only one node is provided
			# 	nodeIndexCount = 1
			# elif commandType in k2NodeIndexList: # the instruction is a Single Link or a Double Link, so two nodes are provided
			# 	nodeIndexCount = 2
			# elif commandType in k3NodeIndexList: # the instruction is an Interpolation Link, so three nodes are provided
			# 	nodeIndexCount = 3
			# else:
			# 	print "WARNING: Hint type %d in glyph %s is not yet supported." % (commandType, gName)
			# 	nodeIndexCount = 0

			itemList = transformItemList(glyph, itemList)

			if not itemList:
				return

			if commandType in deltas:
				nodes = [itemList[1]]
			elif commandType in links:
				nodes = itemList[1:3]
			else:
				nodes = itemList[1:-1]

			paramError = False

			for nodeIndex in nodes:
				try:
					gNode = glyph.nodes[nodeIndex]
				except IndexError:
					if nodeIndex in range(len(glyph), len(glyph)+2):
						pass
					else:
						print "ERROR: A hint definition for glyph %s is referencing an invalid node index: %s" % (gName, nodeIndex)
						paramError = True
						break



			for i, item in enumerate(itemList[1:]):
				ttc.params[i] = item

			# for i, item in enumerate(itemList[1:]):
			# 	try:
			# 		paramValue = item
			# 		if nodeIndexCount:
			# 			gNode = glyph.nodes[paramValue]
			# 	except IndexError:
			# 		print "ERROR: A hint definition for glyph %s is referencing an invalid node index: %s" % (gName, item)
			# 		paramError = True
			# 		break
			# 	except:
			# 		print "ERROR: A hint definition for glyph %s has an invalid parameter value: %s" % (gName, item)
			# 		paramError = True
			# 		break
			# 	ttc.params[i] = paramValue
			# 	nodeIndexCount -= 1


			if not paramError:
				tth.commands.append(ttc)
		
		if len(tth.commands):
			tth.SaveProgram(glyph)
			glyph.mark = int(gMark)
			fl.UpdateGlyph(gIndex)
			glyphsHinted += 1
	
	if glyphsHinted > 0:
		fl.font.modified = 1


def run(parentDir):
	tthintsFilePath = os.path.join(parentDir, kTTHintsFileName)
	if os.path.exists(tthintsFilePath):
		ttHintsList = readTTHintsFile(tthintsFilePath)
	else:
		print "Could not find the %s file at %s" % (kTTHintsFileName, tthintsFilePath)
		return
	
	if len(ttHintsList):
		applyTTHints(ttHintsList)
		print "Done!"
	else:
		print "The %s file at %s has no hinting data." % (kTTHintsFileName, tthintsFilePath)
		return
		

def preRun():
	# Reset the Output window
	fl.output = '\n'
	
	if fl.count == 0:
		print "Open a font first."
		return

	font = fl.font
	
	if len(font) == 0:
		print "The font has no glyphs."
		return

	try:
		parentDir = os.path.dirname(os.path.realpath(font.file_name))
	except AttributeError:
		print "The font has not been saved. Please save the font and try again."
		return
	
	run(parentDir)


if __name__ == "__main__":
	preRun()
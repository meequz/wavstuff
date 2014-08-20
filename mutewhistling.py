#! /usr/bin/env python3
# coding: utf-8
from scipy.io import wavfile
import numpy as NP
from numpy.fft import fft as fft
import sys, math

#~ Mute whistling sounds in speak so they don't hurts over the ears anymore.
#~ Usage: ./mutewhistling.py in.wav out.wav [OPTIONAL: STARTPOINT] [OPTIONAL: FINISHPOINT]
#~ Version 0.1


FILENAME = sys.argv[1]
OUTFILENAME = sys.argv[2]
PERIOD = 601				# length of one frame
MUTE_FACTOR = 1500			# unforce of the mute. more -> lower effect
BORDER = 24					# border for get_mute()

# if user do not want to process the whole file
slicce = False
if len(sys.argv) == 5:
	slicce = True
	START = int(sys.argv[3])
	FINISH = int(sys.argv[4])


def get_frame_by_idx(inlist, idx):
	start = idx * PERIOD
	finish = start + PERIOD
	return inlist[start:finish]

def get_mute(inlist):
	sp = fft(inlist)
	sp = sp[:len(sp)//2]
	sp = NP.abs(sp)
	
	low = sum(sp[:BORDER])
	high = sum(sp[BORDER:])
	
	return (low - high)/1000

def get_line(mute0, mute1, mute2):
	prevmute = mute0
	currmute = mute1
	nextmute = mute2
	
	res = [0] * PERIOD
	center = PERIOD // 2
	res[center] = currmute
	
	#~ left
	step = (prevmute-currmute) / PERIOD
	prev_line_value = res[center]
	for i in reversed(range(center)):
		res[i] = prev_line_value + step
		prev_line_value = res[i]
	
	#~ right
	step = (nextmute-currmute) / PERIOD
	prev_line_value = res[center]
	for i in range(center+1, PERIOD):
		res[i] = prev_line_value + step
		prev_line_value = res[i]
	
	return res

def correct(frame, line):
	frame = NP.float64(frame)
	for itidx, it in enumerate(frame):
		k = abs(line[itidx] / MUTE_FACTOR) + 1		# calculate divider
		frame[itidx] = it / k
	frame = NP.around(frame)
	return NP.int16(frame)

def print_inplace(string):
	string = str(string) + '\r'
	sys.stdout.write(string)
	sys.stdout.flush()


# read file
freq, data = wavfile.read(FILENAME)
if slicce: data = data[START:FINISH]
len_in_frames = len(data) // PERIOD
outdata = []


# go through 2 channels
for channel_n, channel_name in enumerate(('left', 'right')):
	channel = data[:,channel_n].copy()
	
	fr0 = get_frame_by_idx(channel, 0).copy()
	fr1 = get_frame_by_idx(channel, 1).copy()
	
	res_channel = fr1.copy()

	mute0 = get_mute(fr0)
	mute1 = get_mute(fr1)
	
	# go through frames
	for idx in range(len_in_frames-2):
		fr1 = get_frame_by_idx(channel, idx+1).copy()
		fr2 = get_frame_by_idx(channel, idx+2).copy()
		
		mute2 = get_mute(fr2)
		line = get_line(mute0, mute1, mute2)
		corrected = correct(fr1.copy(), line)
		
		# append corrected frame to the result
		res_channel = NP.append(res_channel, corrected.copy(), 0)
		
		# for next iteration
		mute0 = mute1
		mute1 = mute2
		
		# report progress
		progrs = 100 * idx // len_in_frames
		print_inplace(channel_name + ' channel: ' + str(progrs) + '%')
	
	# complete channel to the original length
	stop_point = len(res_channel)
	res_channel = NP.append(res_channel, channel[stop_point:].copy(), 0)
	
	# channel done
	print(channel_name + ' channel done')
	outdata.append(res_channel)


# prepare outdata to writing in wav
outdata = NP.int16(outdata)
outdata = NP.rot90(outdata)
outdata = NP.flipud(outdata)

wavfile.write(OUTFILENAME, freq, outdata)						# write corrected values to wav file
print('result: ' + OUTFILENAME)

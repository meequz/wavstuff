#! /usr/bin/env python3
# coding: utf-8
from pydub import AudioSegment, effects
from math import log
import sys

#~ Adjust sound to make it level equal. May be useful for voice over.
#~ Usage: ./wavadjust.py in.wav out.wav
#~ Version 0.1

appr_quantity = 300		# how many milliseconds on left and right in use to approximate
adjust_degree = 1.0		# power of adjusting, 0..1
silence_tresh = 200		# Silence treshold
dur_tresh = 500			# duration treshold in ms
normalizing = True		# normalize at the end or not


def get_appr_rms(track_segm, idx, appr_quantity=appr_quantity):
	# find slice
	start = idx - appr_quantity
	finish = idx + appr_quantity + 1
	if start < 0: start = 0
	if finish > len(track_segm): finish = len(track_segm)
	# make an audiosegment instanse
	approxies = track_segm[start:finish]
	# return mean volume level of aprroxies
	return approxies.rms

def adjustment(track_segm):
	for idx, item in enumerate(track_segm):
		item_appr_rms = get_appr_rms(track_segm, idx)
		ratio = mean_rms / item_appr_rms	# how many times is changed
		ratio = adjust_degree * ratio		# consider degree
		adjust = 10 * log(ratio, 10)		# convert to db
		
		try:
			res_track_segm = res_track_segm + (item + adjust)
		except NameError:
			res_track_segm = track_segm[0] + adjust
	return res_track_segm

def is_silence(track_segm):
	if track_segm.rms <= silence_tresh:
		return True
	return False

def is_appr_silence(track_segm, idx):
	appr_rms = get_appr_rms(track_segm, idx)
	if appr_rms <= silence_tresh:
		return True
	else:
		return False

def silence_in(track_segm):
	for item in track_segm:
		if is_silence(item):
			return True
	return False

def choke(track_segm):
	len_ = track_segm.duration_seconds * 1000
	return track_segm.silent(len_)

def print_inplace(string):
	string = str(string) + '\r'
	sys.stdout.write(string)
	sys.stdout.flush()

# merge short silencies inside sentencies
def merge_short_sils(fragment_list):
	a = fragment_list[:]
	
	# 1. there is what to modify or not
	def continue_():
		for idx, item in enumerate(a):
			if idx == 0: continue
			if suitable(item)  and  suitable(a[idx-1]):
				return True
		return False

	# 2. modifying
	def modify():
		for idx, item in enumerate(a):
			if idx == 0: continue
			prev = a[idx-1]
			if suitable(item)  and  suitable(prev):
				a[idx-1] = prev + item
				del a[idx]

	def suitable(item):
		nonsils = [it.rms for it in item if not is_silence(it)]		# nonsilencies from 'item'
		if nonsils:													# suituble 1: if not silence
			return True
		elif item.duration_seconds*1000 <= dur_tresh:	# suitable 2: if silent and short. List have to be empty
			return True
		return False
	
	while continue_():
		modify()
	
	return a


# open a wav file
filename = sys.argv[1]
track = AudioSegment.from_wav(filename)
print('processing', filename)
print('silence treshold =', silence_tresh, ';\tapproximate quantity =', appr_quantity, ';\tduration treshold =', dur_tresh)


# fragment_list with segments slicing by silence sign
# determine borders
print('phase 1, finding borders')
borders = [0]
for idx, item in enumerate(track):
	if idx == 0: continue
	#~ if is_appr_silence(track, idx) != is_appr_silence(track, idx-1):		# borders by approximate silent from 08
	if is_silence(item) != is_silence(track[idx-1]):
		borders.append(idx)
borders.append(len(track))

# make fragment list
print('phase 2, making fragment list')
fragment_list = []
for idx, item in enumerate(borders):
	if idx == 0: continue
	start = borders[idx-1]
	finish = item
	range_ = track[start:finish]
	fragment_list.append(range_)
print(len(fragment_list), 'fragments')


# calculate mean rms without silence
# make a list
if not is_silence(fragment_list[0][0]):
	sentence_only_list = fragment_list[::2]
else:
	sentence_only_list = fragment_list[1::2]
print(len(sentence_only_list), 'sentencies')

# calculate mean
rmses = [item.rms for item in sentence_only_list]
try:
	mean_rms = sum(rmses) / len(rmses)
except ZeroDivisionError:
	print('silence_tresh is too much, set it to lesser value')
	exit(1)
mean_rms = 2 * mean_rms		# because quiet sections make mean rms lower
print('mean rms', '{:8.2f}'.format(mean_rms))


# merge short silencies inside sentencies
print('phase 3, merging short silencies inside sentencies')
fragment_list = merge_short_sils(fragment_list)
print(len(fragment_list), 'fragments after merging')


# choke silences, adjust sentencies
print('phase 4, choke and adjust')
for idx, track_segm in enumerate(fragment_list):
	if is_silence(track_segm):
		action = choke
	else:
		action = adjustment
	# brings together
	try:
		res_track += action(track_segm)
	except NameError:
		res_track = action(track_segm)


# normalize
if normalizing:
	res_track = effects.normalize(res_track)


# save result
res_track.export(sys.argv[2], format='wav')
print('done:', sys.argv[2])

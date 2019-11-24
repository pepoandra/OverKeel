import subprocess
import fnmatch
import os, os.path

import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool 

import json

number_of_cores = 4
number_of_features_per_frame = 3

clean_cmd = 'rm -r ffmpeg_stuff'
setup_cmd = 'mkdir ffmpeg_stuff'
ffmpeg_cmd = 'ffmpeg -i 420.mp4 ffmpeg_stuff/%04d.jpg -hide_banner'
_and_ = ' && '
rm_odds = 'rm -f ffmpeg_stuff/*[13579].jpg'

cmd = clean_cmd + _and_ + setup_cmd + _and_ + ffmpeg_cmd + _and_ + rm_odds
os.system(cmd)


files = fnmatch.filter(os.listdir(os.getcwd()+'/ffmpeg_stuff/'), '*.jpg')
number_files =  len(files)

info = {}

cmd = os.getcwd()+'/overfeat/bin/linux_64/overfeat -n ' + str(number_of_features_per_frame) 

#used to analyze one frame, deprecated in favor of analyze_frames_by_chunks
def analyze_frame(file_name):
    frame_cmd = cmd + ' ffmpeg_stuff/' + file_name
    p = os.popen(frame_cmd)
    process = p.read()
    result = {}
    lines = process.split('\n')
    for line in lines:
        if line=='':
            continue
        tokens = line.split('0.')
        result[tokens[0]] = float('0.' + tokens[1])
    number = int(file_name.strip('.jpg').strip('0'))
    info[number] = result

#splits lists in sublists of length n
def split_list(l, n):
    return [l[i:i + n] for i in xrange(0, len(l), n)]

#analyzes lists of files & populates global dictionary info
def analyze_frames_by_chunks(files):
    pre_file = ' ffmpeg_stuff/'
    frames_cmd = cmd + ' ffmpeg_stuff/' + pre_file.join(str(p) for p in files) 
    #process = subprocess.check_output(frames_cmd.split())
    p = os.popen(frames_cmd)
    process = p.read()

    result = {}
    lines = process.split('\n')
    lines = filter(filterBlanks, lines)
    l = lines
    n = 3
    results = split_list(lines, number_of_features_per_frame)
    

    for idx, result in enumerate(results, start=0):
        res = {}
        for line in result:
            tokens = line.split('0.')
            res[tokens[0]] = float('0.' + tokens[1])
            
        number = int(files[idx].strip('0').strip('.jpg'))
        info[number] = res
        


def filterBlanks(line):
    return line != ''

#divides lists in #num sublists of approx equal length 
def chunkIt(seq, num):
    avg = len(seq) / float(num)
    out = []
    last = 0.0

    while last < len(seq):
        out.append(seq[int(last):int(last + avg)])
        last += avg
    return out

#separate files in equal groups, one group per thread
files_in_chunks = chunkIt(files, number_of_cores)

#start one thread per core
pool = ThreadPool(number_of_cores) 

results = pool.map(analyze_frames_by_chunks, files_in_chunks) # real    6m2.109s
#results = pool.map(analyze_frame, files) # 7m41.077s

#min threshold to even consider a feature
threshold = 0.5

features_to_frames = {}
for idx, features in info.items():
    for feature, value in features.items():
        if(value > threshold):
            if(feature in features_to_frames):
                features_to_frames[feature].append(idx)
            else:
                features_to_frames[feature] = [idx]

final_output = {}

for key, frames in features_to_frames.items():
    in_seq = False
    seq = []
    last = 1
    for frame in frames:
        if(in_seq == False):
            seq.append(frame)
            in_seq = True
        else:
            if(frame - last > 2):
                in_seq = False
                seq.append(last)
        last = frame
    seq.append(last)
    final_output[key] = seq


frames_per_sec = 30

def build_answer(dict):
    out = ''
    for key, list in dict.items():
        for i in range(0, len(list)/2):
            res = key + ": "
            res += "from second {:10.4f} to second {:10.4f} \n".format( float(list[i*2])/frames_per_sec , float(list[i*2+1]) /frames_per_sec )
            out += res
    return out

text =  build_answer(final_output)

print text
with open('results.json', 'w') as file:
    file.write(json.dumps(info)) 
    file.write(text)
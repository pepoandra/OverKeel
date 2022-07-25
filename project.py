import subprocess
import fnmatch
import os, os.path
import sys
import multiprocessing
from multiprocessing.dummy import Pool as ThreadPool
import json

if len(sys.argv) > 1:
    video_name = sys.argv[1]
else:
    video_name = "420.mp4"

threshold = 0.5  # min threshold to even consider a feature
number_of_cores = 4  # number of cores on the CPU running it
number_of_features_per_frame = 3  # features extracted from each frame when running overfeat


# helper functions

def build_answer(obj):
    frames_per_sec = 30
    out = ''
    for k, arr in obj.items():
        for i in range(0, len(arr) / 2):
            if arr[i * 2] == arr[2 * i + 1]:
                continue
            res = k + ": "
            res += "from second {:10.4f} to second {:10.4f} \n".format(float(arr[i * 2]) / frames_per_sec,
                                                                       float(arr[i * 2 + 1]) / frames_per_sec)
            out += res
    return out


# splits lists in sublists of length n
def split_list(l, n):
    return [l[i:i + n] for i in xrange(0, len(l), n)]


def filter_blanks(line):
    return line != ''


# it splits a list in #num sublists of approx equal length
def split_in_chunks(input, num):
    avg = len(input) / float(num)
    out = []
    last = 0.0
    while last < len(input):
        out.append(input[int(last):int(last + avg)])
        last += avg
    return out


print("\nNumber of cores used: " + str(number_of_cores))
print("Number features analyzed per frame: " + str(number_of_features_per_frame))
print("\nExtracting frames from: " + video_name)

folder = 'ffmpeg_stuff'

# removing folder if it exists
clean_cmd = 'rm -r ' + folder
setup_cmd = 'mkdir ' + folder
ffmpeg_cmd = 'ffmpeg -i ' + video_name + ' ' + folder + '/%04d.jpg -hide_banner -loglevel panic'
_and_ = ' && '
rm_odds = 'rm -f ' + folder + '/*[13579].jpg'

# cmd = clean_cmd + _and_ + setup_cmd + _and_ + ffmpeg_cmd + _and_ + rm_odds
os.system(clean_cmd)
os.system(setup_cmd)
os.system(ffmpeg_cmd)
os.system(rm_odds)

folder_to_search = os.getcwd() + '/' + folder
files = fnmatch.filter(os.listdir(folder_to_search), '*.jpg')
number_files = len(files)
print(files)

info = {}
cmd = os.getcwd() + '/overfeat/bin/linux_64/overfeat -n ' + str(number_of_features_per_frame)
print("Finished frame extraction.\n\nAnalyzing frames of: " + video_name)


# used to analyze one frame, deprecated in favor of analyze_frames_by_chunks
def analyze_frame(file_name):
    frame_cmd = cmd + folder + '/' + file_name
    p = os.popen(frame_cmd)
    process = p.read()
    result = {}
    lines = process.split('\n')
    for line in lines:
        if line == '':
            continue
        tokens = line.split('0.')
        result[tokens[0]] = float('0.' + tokens[1])
    number = int(file_name.strip('.jpg').strip('0'))
    info[number] = result


# Analyze lists of files & populates global dictionary info
def analyze_frames_by_chunks(filenames):
    pre_file = ' ' + folder + '/'
    frames_cmd = cmd + pre_file + pre_file.join(str(p) for p in filenames)

    process = subprocess.Popen(frames_cmd, shell=True,
                               stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    print("\nProcess #" + str(process.pid) + ": " + frames_cmd + " ")

    (output, err) = process.communicate()
    # This makes the wait possible
    p_status = process.wait()

    result = {}
    lines = output.split('\n')
    lines = filter(filter_blanks, lines)
    l = lines
    n = 3
    res = split_list(lines, number_of_features_per_frame)

    for i, result in enumerate(res, start=0):
        res = {}
        for line in result:
            tokens = line.split('0.')
            res[tokens[0]] = float('0.' + tokens[1])

        number = int(filenames[i].strip('0').strip('.jpg'))
        info[number] = res


# separate files in equal groups, one group per thread
files_in_chunks = split_in_chunks(files, number_of_cores)

# start one thread per core
pool = ThreadPool(number_of_cores)

print("Main process #" + str(os.getpid()))
results = pool.map(analyze_frames_by_chunks, files_in_chunks)  # real    6m2.109s
# results = pool.map(analyze_frame, files) # 7m41.077s

print("\nFinished analysis. Gathering results")

features_to_frames = {}
for idx, features in info.items():
    for feature, value in features.items():
        if value > threshold:
            if feature in features_to_frames:
                features_to_frames[feature].append(idx)
            else:
                features_to_frames[feature] = [idx]

final_output = {}

for key, frames in features_to_frames.items():
    in_seq = False
    seq = []
    last = 1
    for frame in frames:
        if not in_seq:
            seq.append(frame)
            in_seq = True
        else:
            if frame - last > 2:
                in_seq = False
                seq.append(last)
        last = frame
    seq.append(last)
    final_output[key] = seq

text = build_answer(final_output)

if final_output:
    print(text)
else:
    print("\nNo object on the video was successfully recognized.")

with open('results.json', 'w') as file:
    file.write(text)

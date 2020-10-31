# sam file filtering script
# Alec Bahcheli, Daniel Giguire from Gloor Lab, Western University, Canada

import sys, getopt, re, time, math
from concurrent.futures import ProcessPoolExecutor
import concurrent.futures

t1 = time.time()

# number of processes
worker_process_count = 1

# maximum ratio of length to score
max_len_to_score = 2

# minimum ratio of the number of matches to the length
min_match_to_length = 1

# minimum length for a read to be considered
min_length = 1000

# minimum score for an alignment to be considered
min_score = 1

# error code to return without necessary input
error_code = '''
cigar-parse_phased.py

Required inputs:
-i / --input <input raw samfile>
 -o / --output <output filtered samfile>

Optional inputs:
-l / --length <minimum read length for cutoff (default 1000)>
-m / --matchlength <sequence identity, also known as minimum ratio of matches to read length (default 0.5)>
-s / --score <minimum score for the whole alignment (default 1)>
-q / --lengthscore <maximum ratio of length to score, may be considered as the inverse of the average score per base (default 2)>
-t / --threads <number of processes to run (default 1)>'''

# get the options and files required for the input
try:
    opts, args = getopt.getopt(sys.argv[1:],"hi:o:l:m:s:q:t:",["input=","output=", "length=", "matchlength=", "score=", "lengthscore=", "threads="])
except getopt.GetoptError:
    print (error_code)
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print (error_code)
        sys.exit()
    elif opt in ("-i", "--input"):
        sam = str(arg)
    elif opt in ("-o", "--output"):
        results_file = str(arg)
    elif opt in ("-l", "--length"):
        min_length = int(arg)
    elif opt in ("-m", "--matchlength"):
        min_match_to_length = float(arg)
    elif opt in ("-s", "--score"):
        min_score = int(arg)
    elif opt in ("-q", "--lengthscore"):
        max_len_to_score = float(arg)
    elif opt in ("-t", "--threads"):
        worker_process_count = int(arg)

# dictionary for vcf of phase
option = {}

# list of reads that satisfy the cutoff requirements
reads_of_interest = []

future_list = []

def it_meets_filters(length, num_of_matches):
    if int(length) > min_length and (int(num_of_matches) / int(length)) > min_match_to_length:
        return True
    else:
        return False

def it_is_good_score(length, score):
    if int(score) > min_score and (int(length) / int(score)) < max_len_to_score:
        return True
    else:
        return False

def filter_reads(read):
    # split the read into the expected fields
    read = read.split("\t")
    if int(read[1]) == 16 or int(read[1]) == 0:
        # read mapping score
        score = int(read[13][5:])
        # read length 
        length = 0
        # number of matches
        num_of_matches = 0
        # get the cigar string
        cigar = re.findall("([0-9]*[MISH])", read[5])
        for element in cigar:
            # if the read doesn't match with the chromosome, the length of alignment increase but not the matches
            if re.search("[ISH]", element):
                length += int(element.strip("[ISH]")) 
            # if the read at a position does match the chromosome sequence, the length and the number of matches increase
            elif re.search("M", element):
                length += int(element.strip("M")) 
                num_of_matches += int(element.strip("M"))
        # if it meets the filter cutoffs, return the whole read
        if it_is_good_score(length, score):
            if it_meets_filters(length, num_of_matches):
                return "\t".join(read)

def main():
    # test if the minimmum input parameters are defined
    try:
        sam
        results_file
    except NameError:
        return print(error_code)
    
    # open the samfile
    samfile_raw = open(sam).readlines()

    # open the results file
    results = open(results_file, "w")

    # make a list of just reads
    samfile = []

    # get the headers
    for read in samfile_raw:
        if read.startswith("@"):
            results.write(read)
        else:
            samfile.append(read)

    print("Samfile read into memory for parallelization")
    print(round((time.time() - t1), 2))

    chunks = math.floor(0.2 * len(samfile) / worker_process_count)

    # parallelize read evaluations
    with ProcessPoolExecutor(max_workers = worker_process_count) as executor:
        for reads in executor.map(filter_reads, samfile, chunksize = chunks):
            if reads != None:
                reads_of_interest.append(reads)

    print("Done filtering reads")
    print(round(time.time() - t1), 2)

    for read in reads_of_interest:
        # write the good reads to a file
        results.write(read)
    
    results.close()

    print("Finished writing filtered samfile")
    print(round(time.time() - t1), 2)



if __name__ == '__main__':
    main()





# https://labs.spotify.com/2014/02/28/how-to-shuffle-songs/
# Fisher-Yates
import math
import random

class ShuffleElement(object):

    def __init__(self, key, ref, index):
        self.key = key
        self.ref = ref
        self.index = index
        self.score = 0

def fisher_yates(data):
    N = len(data)
    for i in range(N):
        j = random.randint(i, N - 1)
        data[i], data[j] = data[j], data[i]

def binshuffle(data, group_mapping=lambda x: x):
    grpcounts = {}
    grpoffset = {}
    temp = []

    N = len(data)

    if N < 2:
        return data

    # pre shuffle the data to randomize the output
    # Otherwise items within a group would always be output
    # in the same order found in the input array
    fisher_yates(data)

    # count the number of elements in each group
    # assign a value from 0 to G to each element in a group
    for elem in data:
        k = group_mapping(elem)
        if k not in grpcounts:
            grpcounts[k] = 1
        else:
            grpcounts[k] += 1
        temp.append(ShuffleElement(k, elem, grpcounts[k] - 1))

    # generate an initial offset for each group
    # the offset is random, and the range is chosen to
    # solve the degenerate problem where some groups contain a few
    # elements, and others contain many elements.
    for grp, count in grpcounts.items():
        grpoffset[grp] = random.random() * (N / count)

    # calculate a score for each element
    # the score ranges from 0-h/2 to N+h/2.
    # elements within a group are spaced
    # evenly within this range.
    for i, elem in enumerate(temp):
        count = grpcounts[elem.key]
        h = (N / count) / 2
        offset = random.random() * h - h / 2 + grpoffset[elem.key]
        elem.score = N * elem.index / count + offset

    # finally sort by the score, randomizing the elements
    # while separating items that belong to the same group
    temp = sorted(temp, key=lambda x: x.score)

    return [x.ref for x in temp]


import numpy as np
import json
from datetime import datetime, timedelta
import collections
import itertools
import math
from operator import mul
import functools
from multiprocessing import Pool



risk_curve = [1,2,2,2,2,1,1,0,0,0,0,0,0,0]
risk_begin = -2 #start fot he curve is two days before symptoms

#pre calculate the curves for each offset:

curves = {}
curves[-1] = np.array([[0,0,1] for i in range(15)])
for onset in range(0,15):
    curve = np.zeros((15,3),dtype='int')
    for i,risk in enumerate(risk_curve):
        day_since_onset = i+risk_begin
        index = onset+day_since_onset
        if 0<= index < 15:
            curve[index,risk] = 1
    curves[onset] = curve



def itter_hypotoses(keycounts,sofar = None,hyp = None,last_added = -1):
    # itter all combinations with replacement, but stop a path as soon as a smaller combination is to large already
    if sofar is None:
        sofar = np.zeros(keycounts.shape,dtype='int')

    if hyp == None:
        hyp = []

    for new_onset in range(last_added,15):
        new_sofar = sofar+curves[new_onset]
        if np.all(keycounts-new_sofar>=-1):
            # We accept at most -1 in a slot, so this if does not run if there are 2 more keys missing than generated for a slot, which is conservative.
            new_hyp = hyp+[new_onset]
            yield new_sofar,new_hyp
            yield from itter_hypotoses(keycounts,new_sofar,new_hyp,new_onset)

def score_hypo(keycounts,hyp_and_cost):
    hyp_cost,hyp = hyp_and_cost
    #hyp_cost = sum(curves[onset] for onset in hyp)
    expected_keys_per_risk = sum(hyp_cost)
    expected_keys = sum(expected_keys_per_risk)

    left = keycounts - hyp_cost

    # everything where keys are left we know that these must be generated
    positive = left * (left>=0)
    known_generated_per_risk = sum(positive)
    known_generated = sum(known_generated_per_risk)

    # everything where there is a negative value, we know that a key must be missing
    negative = - left * (left<0)
    known_missing_per_risk = sum(negative)
    known_missing = sum(known_missing_per_risk)

    # what is left is keys that are generated in spots where a key is missing
    # this is relevant because it offsets the balance between the risks for the generated keys

    # note that the G (generated keys) = 150 - E (expected) + M (missing)
    # Expending both sides in known and unkown we get kG+uG = 150 - E + kM + uM
    # since uM = uG we get
    # kG = 150 - E + kM

    # next we check all possible values of uM/uG and compute the values per risk
    # There can never be more missing in total then expected keys
    for unknown_missing in range(expected_keys-known_missing+1):
        # try all possible numbers of missing keys, the higher the less likely.
        uploaded_keys = expected_keys-known_missing - unknown_missing
        generated = 150 - uploaded_keys
        generated_per_risk = np.array([generated//3]*3)
        generated_per_risk[0] += 1 if generated % 3 >= 1 else 0
        generated_per_risk[1] += 1 if generated % 3 == 2 else 0
        unknown_generated_per_risk  = generated_per_risk - known_generated_per_risk
        unknown_missing_per_risk = unknown_generated_per_risk

        if np.any(unknown_generated_per_risk < 0 ):
            # it is not possible to have a negative number of unkown missing
            continue

        missing_per_risk = unknown_missing_per_risk + known_missing_per_risk
        if np.any(missing_per_risk>expected_keys_per_risk):
            # can not have more missing then there should be
            continue


        # missing fraction, this will always be the lowest for the firstplausible loop, so we return
        fraction_missing =(unknown_missing+known_missing)/ expected_keys

        # More likely that symtomps started recently, say twice as likely
        given_onset = [onset for onset in hyp if onset >=0]
        fraction_start = sum(1-onset/15 for onset in given_onset)/len(given_onset) if len(given_onset)>0 else .5

        return fraction_missing,fraction_start
    return float('inf'),float('inf')

def load_keysets(fn):
    with open(fn) as fp:
        return json.load(fp)


def find_best_match(keycounts):
    best_hypo = min(itter_hypotoses(),key=lambda hyp: score_hypo(keycounts,hyp))
    return score_hypo(best_hypo),best_hyp

def iter_exact(keycounts):
    for hyp in itter_hypotoses():
        error = score_hypo(keycounts,hyp)
        if error[0] == 0:
            yield error,hyp

def score_and_hyp(inp):
    keycount,x = inp
    return score_hypo(keycounts,x),x


def find_multiproc(keycounts):
    res = []
    with Pool() as pool:
        for score,hyp in pool.imap_unordered(score_and_hyp,zip(itertools.repeat(keycounts),itter_hypotoses(keycounts)),1000):
            if score[0]< 0.05:
                # we accepts 5% of the keys are missing, which is rather high.
                res.append(hyp[1])
    return res

def find_max_hyp(keycounts):
    res = []
    best_score = 2
    best_hyp = None
    for hyp in itter_hypotoses(keycounts):
        score = score_hypo(keycounts,hyp)
        if score[0] < best_score or (score[0] == best_score and len(hyp)> len(best_hyp)):
            best_score = score[0]
            best_hyp = hyp[1]
    return best_score,best_hyp


def to_keycounts(setdate,keyset):
    res = np.zeros((15,3),dtype='int')
    for k in keyset:
        date = datetime.fromtimestamp(k["rollingStartIntervalNumber"]*600).date()
        days_ago = (setdate-date)/timedelta(days=1)
        transmission = k['transmissionRiskLevel'] - 1
        res[14-int(days_ago+.1),transmission]+=1
    return res

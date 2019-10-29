# -*- coding: utf-8 -*-

import csv
import itertools
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from functools import partial

from tqdm import tqdm
from sequitur_tools import get_phones

VALID_DIPHONES_PATH = './pron_data/diphones/complete_ipa.txt'

phonemes = [
    'a', 'r', 't', 's', 'n', 'ɪ', 'l', 'ʏ', 'k', 'm',
    'ð', 'ɛ', 'v', 'p', 'h', 'f', 'j', 'c', 'i', 'ɔ', 'r̥',
    'ei', 'ŋ', 'ɣ', 'ou', 'œ', 'ouː', 'au', 'ai', 'aː', 'auː',
    'iː', 'eiː', 'ɪː', 'ɛː', 'θ', 'l̥', 'tʰ', 'uː', 'aiː',
    'kʰ', 'u', 'ɔː', 'x', 'œː', 'œy', 'n̥', 'cʰ', 'œyː', 'pʰ',
    'ɲ', 'ʏː', 'ç', 'ŋ̊', 'm̥', 'ʏi', 'ɲ̊', 'ɔi']

diphones = []
list_diphones  = []
with open(VALID_DIPHONES_PATH) as i_f:
    for line in i_f:
        p1, p2 = line.split('\t')
        diphones.append("".join([p1, p2.strip()]))
        list_diphones.append((p1, p2))

def get_diphones(phone_string: str):
    '''
    A string of space seperated phones phonetically
    representing a single word, e.g. for the original word
    "mig" we get phone_string="m ɪː ɣ"
    '''
    phones = phone_string.split()
    return [phones[i]+phones[i+1] for i in range(len(phones) - 1)]

def g2p_pickle(src_path, out_path, n_jobs=4):
    '''
    '''
    import pickle

    executor = ProcessPoolExecutor(max_workers=n_jobs)
    futures = []

    print('Loading from disk')
    tokens = pickle.load(open(src_path, 'rb'))
    print('Finished')
    for line in tqdm(tokens):
            futures.append(executor.submit(partial(get_phones, line)))

    with open(out_path, 'w') as out_file:
        for res in [
                future.result() for future in tqdm(futures)
                if future.result() is not None]:
            out_file.write('{}\n'.format('\t'.join([res[0].strip()]+res[1][:])))


def g2p_file(src_path, out_path, n_jobs=4):
    '''
    '''
    executor = ProcessPoolExecutor(max_workers=n_jobs)
    futures = []

    with open(src_path, 'r') as token_file:
        for line in token_file:
            futures.append(executor.submit(partial(get_phones, line)))

    with open(out_path, 'w') as out_file:
        for res in [
                future.result() for future in tqdm(futures)
                if future.result() is not None]:
            out_file.write('{}\n'.format('\t'.join([res[0].strip()]+res[1][:])))

def score_file(src_path, out_path, n_jobs=4):

    all_diphones = [''.join(p) for p in list(itertools.permutations(phonemes, 2))]
    corpus_diphones = defaultdict(int)

    # calculate total diphone coverage
    with open(src_path, 'r') as g2p_file:
        for line in tqdm(g2p_file):
            token, *phone_strings = line.split('\t')[0:]
            for phone_string in phone_strings:
                diphones = get_diphones(phone_string)
                for diphone in diphones:
                    corpus_diphones[diphone] += 1

    # calculate the scores
    executor = ProcessPoolExecutor(max_workers=n_jobs)
    futures = []
    with open(src_path, 'r') as g2p_file:
        for line in tqdm(g2p_file):
            futures.append(executor.submit(partial(get_score, line, corpus_diphones)))

    futures = [future.result() for future in tqdm(futures)
        if future.result() is not None]
    results = sorted(futures, key=lambda r: r[1], reverse=True)

    out_file = open(out_path, 'w')
    for res in results:
        out_file.write('{}\t{}\n'.format(*res))

    out_file.close()

def get_score(line, corpus_diphones):
    token, *phone_strings = line.split('\t')[0:]

    unique_diphones = unique(itertools.chain.from_iterable(
        get_diphones(ps) for ps in phone_strings))

    score = 0.0
    for diphone in unique_diphones:
        score += 1.0/corpus_diphones[diphone]
    score *= 1/len(token)
    return [token, score]

def unique(seq):
   # Not order preserving
   keys = {}
   for e in seq:
       keys[e] = 1
   return keys.keys()

if __name__ == '__main__':
    # g2p_pickle('./data/tokens/rmh_150K.txt', './data/tokens/rmh_g2p.txt', n_jobs=30)
    # g2p_file('./data/tokens/eiki.txt', './data/tokens/eiki_g2p.txt', n_jobs=24)
    score_file('./data/tokens/rmh_g2p.txt', './data/tokens/rmh_scored.txt', n_jobs=30)

#!/usr/bin/env python

from __future__ import print_function
from util.profiler import Profiler
from util.db import DataDB, MetadataDB
from datetime import datetime

import hatchet as ht
import config as conf

import os
import glob
import json
import sys
import platform
import uuid


# from pyinstrument import Profiler

prf = Profiler()
ddb = DataDB()
md_db = MetadataDB()
curr_time = datetime.now()
isotime = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

def write_run_metadata():
    # create a directory for this run and dump metadata in there
    non_std_time = curr_time.strftime("%d-%m-%Y-%H%M")
    profile_runs_dir = "/usr/workspace/scullyal/hatchet_optimization_project/profiling/profile_data/{}_profile_runs/".format(non_std_time)
    uname = platform.uname()

    if not os.path.exists(profile_runs_dir):
        os.mkdir(profile_runs_dir)
        with open(profile_runs_dir+"metadata.txt", "w") as f:
            f.write("Description: {}\n".format(conf.run_metadata['description']))
            f.write("Keywords: {}\n".format(conf.run_metadata['keywords']))
            f.write("System: {}\n".format(uname.system))
            f.write("Node Name: {}\n".format(uname.node))
            f.write("Release: {}\n".format(uname.release))
            f.write("Version: {}\n".format(uname.version))
            f.write("Machine: {}\n".format(uname.machine))
            f.write("Processor: {}\n".format(uname.processor))

    return profile_runs_dir

def filter_profile(numtrials, filename, gf, run_d):
    print("Profiling filter:", filename)
    for x in range(0, numtrials):
        print(".", end='', flush=True)
        prf.start()
        gf_filtered = gf.filter(lambda x: x['nid'] % 2 == 0)
        run_d['runtime'] = prf.end()
        if conf.log_to_db == True:
            ddb.add(run_d)
    print('\n')

def union_profile(numtrials, filename, gf1, gf2, run_d):
    print("Profiling union", filename)
    for x in range(0, numtrials):
        print(".", end='')
        prf.start()

        run_d['runtime'] = prf.end()
        if conf.log_to_db == True:
            ddb.add(run_d)
    print('\n')

def iter_profile(numtrials, filename, filepath, run_d):
    print("Profiling", filename)
    for x in range(0, numtrials):
        print(".", end='')
        prf.start()
        gf = ht.GraphFrame.from_hpctoolkit(filepath)
        run_d['runtime'] = prf.end()
        if conf.log_to_db == True:
            ddb.add(run_d)
    print('\n')

if __name__ == "__main__":

    if conf.debug == True:
        d_conf = conf.debug_conf
        dir = d_conf['files'][d_conf['selection']]
        gf = ht.GraphFrame.from_hpctoolkit(dir)

        prf.start()
        gf = gf.filter(lambda x: x['nid'] % 2 == 0)
        prf.end()

        if d_conf['output'] == True:
            gf = gf.squash()
            print(gf.dataframe)
            print(gf.tree())

        print("DB: {} \n Runtime: {} \n".format(dir, prf.getRuntime()))

    else:
        r_conf = conf.run_configuration
        run_d = {
                    'profile':None,
                    'dir':None,
                    'md_id':None,
                    'runtime':None,
                    'description':conf.run_metadata['description'],
                    'keywords':conf.run_metadata['keywords'],
                    'run_id':None,
                    'datetime':isotime
                }

        if r_conf['profile_type'] == "batch":
            profile_runs_dir = write_run_metadata()
            subset = r_conf['file_selection']

            for ndx, record in subset.iterrows():
                run_uuid = uuid.uuid1().hex
                run_d['profile'] = record['filename']
                run_d['dir'] = profile_runs_dir
                run_d['md_id'] = ndx
                run_d['run_id'] = run_uuid

                gf = ht.GraphFrame.from_hpctoolkit(record['filepath'])
                filter_profile(r_conf['numtrials'], record['filename'], gf, run_d)

                # load runtime data
                run_d['runtime'] = prf.getAverageRuntime(r_conf['numtrials'])

                prf.dumpAverageStats('cumulative', \
                    profile_runs_dir+'{}_{}-{}-{}-{}-{}-{}-profile.txt'.format(record['filename'], \
                        r_conf['numtrials'], \
                        record['nodes'], \
                        record['threads'], \
                        record['ranks'], \
                        record['callsites'], \
                        record['records']), r_conf['numtrials'])

                prf.reset()

        elif r_conf['profile_type'] == "single":
            run_uuid = uuid.uuid1().hex
            idx = r_conf['md_indx']
            profile_runs_dir = '/usr/workspace/scullyal/hatchet_optimization_project/profiling/single_run_data/'
            record = md_db.p_md.iloc[idx]
            numtrials = r_conf['numtrials']
            run_d['profile'] = record['filename']
            run_d['dir'] = profile_runs_dir
            run_d['md_id'] = idx
            run_d['run_id'] = run_uuid

            print("Reading in graphframe.")
            gf = ht.GraphFrame.from_hpctoolkit(record['filepath'])
            print("Done reading.")
            filter_profile(r_conf['numtrials'], record['filename'], gf, run_d)

            prf.dumpAverageStats('cumulative', \
                    profile_runs_dir+'{}_{}-{}-{}-{}-{}-{}-profile.txt'.format(record['filename'], \
                    r_conf['numtrials'], \
                    record['nodes'], \
                    record['threads'], \
                    record['ranks'], \
                    record['callsites'], \
                    record['records']), r_conf['numtrials'])

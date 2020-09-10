#!/usr/bin/env python
# -*- coding: utf-8 -*-
##
# @file lite2.py
# @brief 
# @author Zhijie Xie
# @date 2015-11-27

from __future__ import print_function

import sys
import os
import argparse
import subprocess
import shutil
from rmatspipeline import run_pipe


VERSION = 'v4.1.0'
USAGE = '''%(prog)s [options]'''
pipe_tasks = set(['prep', 'post', 'both',])


def getstatusoutput(cmd):
    """ behave like commands.getstatusoutput which moved to
    subprocess.getstatusoutput in Python 3.
    Implmented with subprocess.check_output which is available
    in both Python 2 and 3.
    """
    status = 0
    try:
        output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        status = e.returncode
        output = e.output

    output = output.decode()
    if output[-1] == '\n':
        output = output[:-1]

    return (status, output)


def doSTARMapping(args): ## do STAR mapping
    fastqs = [args.s1, args.s2,]
    bams = [[], [],]

    for i in range(len(fastqs)):
        if fastqs[i] != '':
            sample = [pair.split(':') for pair in fastqs[i].split(',')]
            print("mapping the first sample")
            for rr, pair in enumerate(sample):
                map_folder = os.path.join(args.tmp, 'bam%d_%d' % (i+1, rr+1));

                if os.path.exists(map_folder):
                    if os.path.isdir(map_folder):
                        os.rmdir(map_folder)
                    else:
                        os.unlink(map_folder)

                os.makedirs(map_folder)
                cmd = 'STAR --chimSegmentMin 2 --outFilterMismatchNmax 3 --alignEndsType EndToEnd --runThreadN 4 --outSAMstrandField intronMotif --outSAMtype BAM SortedByCoordinate ';
                cmd += '--alignSJDBoverhangMin ' + str(args.tophatAnchor) + ' --alignIntronMax 299999 --genomeDir ' + args.bIndex + ' --sjdbGTFfile ' + args.gtf; 
                cmd += ' --outFileNamePrefix ' + map_folder + '/ --readFilesIn ';
                cmd += ' '.join(pair)
                if pair[0].endswith('.gz'):
                    cmd += ' --readFilesCommand zcat';
                status,output = getstatusoutput(cmd)
                print("mapping sample_%d, %s is done with status %s" % (i, ' '.join(pair), status))
                if (int(status)!=0): ## it did not go well
                    print("error in mapping sample_%d, %s: %s" % (i, ' '.join(pair),status))
                    print("error detail: %s" % output)
                    raise Exception();
                print(output)
                bams[i].append(os.path.join(map_folder, 'Aligned.sortedByCoord.out.bam'))

    return ','.join(bams[0]), ','.join(bams[1])
##### end of doSTARMapping ####


def get_args():
    """TODO: Docstring for get_args.
    :returns: TODO

    """
    parser = argparse.ArgumentParser(usage=USAGE)

    group1 = parser.add_mutually_exclusive_group()
    group2 = parser.add_mutually_exclusive_group()

    parser.add_argument('--version', action='version', version=VERSION)
    parser.add_argument('--gtf', action='store',
                        help='An annotation of genes and transcripts in GTF format', dest='gtf')

    group1.add_argument('--b1', action='store', default='',
                        help='A text file containing a comma separated list of the BAM files for sample_1. (Only if using BAM)', dest='b1')
    group2.add_argument('--b2', action='store', default='',
                        help='A text file containing a comma separated list of the BAM files for sample_2. (Only if using BAM)', dest='b2')
    group1.add_argument('--s1', action='store', default='',
                        help='A text file containing a comma separated list of the FASTQ files for sample_1. If using paired reads the format is ":" to separate pairs and "," to separate replicates. (Only if using fastq)', dest='s1')
    group2.add_argument('--s2', action='store', default='',
                        help='A text file containing a comma separated list of the FASTQ files for sample_2. If using paired reads the format is ":" to separate pairs and "," to separate replicates. (Only if using fastq)', dest='s2')

    parser.add_argument('--od', action='store',
                        help='The directory for final output', dest='od')
    parser.add_argument('--tmp', action='store',
                        help='The directory for intermediate output such as ".rmats" files from the prep step', dest='tmp')
    parser.add_argument('-t', action='store', default='paired',
                        choices=['paired', 'single'],
                        help='Type of read used in the analysis: either "paired" for paired-end data or "single" for single-end data. Default: %(default)s', dest='readtype')
    parser.add_argument('--libType', action='store', default='fr-unstranded',
                        choices=['fr-unstranded', 'fr-firststrand',
                                 'fr-secondstrand',],
                        help='Library type. Use fr-firststrand or fr-secondstrand for strand-specific data. Default: %(default)s', dest='dt')
    parser.add_argument('--readLength', action='store', type=int,
                        help='The length of each read', dest='readLength')
    parser.add_argument('--variable-read-length', action='store_true',
                        help='Allow reads with lengths that differ from --readLength to be processed. --readLength will still be used to determine IncFormLen and SkipFormLen',
                        dest='variable_read_length')
    parser.add_argument('--anchorLength', action='store', type=int, default=1,
                        help='The anchor length. Default is %(default)s', dest='anchorLength')
    parser.add_argument('--tophatAnchor', action='store', type=int, default=6,
                        help='The "anchor length" or "overhang length" used in the aligner. At least "anchor length" NT must be mapped to each end of a given junction. The default is %(default)s. (Only if using fastq)', dest='tophatAnchor')
    parser.add_argument('--bi', action='store', default='',
                        help='The directory name of the STAR binary indices (name of the directory that contains the SA file). (Only if using fastq)', dest='bIndex')
    parser.add_argument('--nthread', action='store', type=int, default=1,
                        help='The number of threads. The optimal number of threads should be equal to the number of CPU cores. Default: %(default)s', dest='nthread')

    parser.add_argument('--tstat', action='store', type=int,
                        help='The number of threads for the statistical model. If not set then the value of --nthread is used', dest='tstat')
    parser.add_argument('--cstat', action='store', type=float, default=0.0001,
                        help='The cutoff splicing difference. The cutoff used in the null hypothesis test for differential splicing. The default is 0.0001 for 0.01%% difference. Valid: 0 <= cutoff < 1. Does not apply to the paired stats model', dest='cstat')

    parser.add_argument('--task', action='store', default='both',
                        choices=['prep', 'post', 'both', 'inte',],
                        help='Specify which step(s) of rMATS to run. Default: %(default)s. prep: preprocess BAMs and generate a .rmats file. post: load .rmats file(s) into memory, detect and count alternative splicing events, and calculate P value (if not --statoff). both: prep + post. inte (integrity): check that the BAM filenames recorded by the prep task(s) match the BAM filenames for the current command line', dest='task')
    parser.add_argument('--statoff', action='store_false',
                        help='Skip the statistical analysis', dest='stat')
    parser.add_argument('--paired-stats', action='store_true',
                        help='Use the paired stats model', dest='paired_stats')

    parser.add_argument('--novelSS', action='store_true',
                        help='Enable detection of novel splice sites (unannotated splice sites). Default is no detection of novel splice sites', dest='novelSS')
    parser.add_argument('--mil', action='store', type=int, default=50,
                        help='Minimum Intron Length. Only impacts --novelSS behavior. Default: %(default)s', dest='mil')
    parser.add_argument('--mel', action='store', type=int, default=500,
                        help='Maximum Exon Length. Only impacts --novelSS behavior. Default: %(default)s', dest='mel')
    # The help text for --imbalance ratio is not added to the parser
    # since the parameter is only intended for internal use and it
    # defaults to no filtering.
    #
    # Filter events where the ratio of upstream junction reads to
    # downstream junction reads (or downstream to upstream) exceeds
    # --imbalance-ratio. The events are filtered before running the
    # stats model so that the FDR is based on the filtered
    # events. If not specified then no events are filtered
    parser.add_argument('--imbalance-ratio', type=float,
                        help=argparse.SUPPRESS,
                        dest='imbalance_ratio')

    args = parser.parse_args()

    if args.b1 == '' and args.b2 == '' and args.s1 == '' and args.s2 == '':
        sys.exit('ERROR: BAM/FASTQ required. Please check b1, b2, s1 and s2.')
    if args.gtf == None or args.od == None or args.tmp == None:
        sys.exit('ERROR: GTF file, output folder and temporary folder required. Please check --gtf, --od and --tmp.')
    if (args.s1 != '' or args.s2 != '') and args.bIndex == '':
        sys.exit('ERROR: STAR binary indexes required. Please check --bi.')
    if args.readLength is None:
        sys.exit('ERROR: --readLength is required. An average or median'
                 ' --readLength can be used in combination with'
                 ' --variable-read-length when the reads do not have the'
                 ' same length.')

    if len(args.b1) > 0:
        with open(args.b1, 'r') as fp:
            args.b1 = fp.read().strip(' ,\n')
    if len(args.b2) > 0:
        with open(args.b2, 'r') as fp:
            args.b2 = fp.read().strip(' ,\n')
    if len(args.s1) > 0:
        with open(args.s1, 'r') as fp:
            args.s1 = fp.read().strip(' ,\n')
    if len(args.s2) > 0:
        with open(args.s2, 'r') as fp:
            args.s2 = fp.read().strip(' ,\n')

    if (args.task != 'prep' and args.stat
        and (len(args.b1) * len(args.b2) == 0)
        and (len(args.s1) * len(args.s2) == 0)):
        sys.exit('ERROR: while performing statistical analysis, user should provide two groups of samples. Please check b1,b2 or s1,s2.')

    if args.b1 == '' and args.b2 == '' and (args.s1 != '' or args.s2 != ''):
        args.b1, args.b2 = doSTARMapping(args)

    args.bams = ','.join([args.b1, args.b2]).strip(',')
    args.junctionLength = 2 * (args.readLength - args.anchorLength)

    dt_map = {'fr-unstranded':0, 'fr-firststrand':1, 'fr-secondstrand':2}
    args.dt = dt_map[args.dt]

    if args.tstat is None:
        args.tstat = args.nthread

    return args


def check_integrity(input_bams_string, tmp_dir):
    """TODO: Docstring for check_integrity.
    :returns: TODO

    """
    input_bams = input_bams_string.split(',')
    duplicate_input_bams = list()
    prep_count_by_bam = dict()
    for input_bam in input_bams:
        if input_bam in prep_count_by_bam:
            duplicate_input_bams.append(input_bam)
        else:
            prep_count_by_bam[input_bam] = 0

    all_files = [os.path.join(root, name)
                 for root, dirs, files in os.walk(tmp_dir)
                 for name in files if name.endswith('.rmats')]

    bams_only_in_prep = list()
    for name in all_files:
        with open(name, 'r') as fp:
            prep_bams = fp.readline().strip().split(',')

        for prep_bam in prep_bams:
            if prep_bam not in prep_count_by_bam:
                bams_only_in_prep.append(prep_bam)
                prep_count_by_bam[prep_bam] = 1
            else:
                prep_count_by_bam[prep_bam] += 1

    missing_preps = list()
    duplicate_preps = list()
    for bam, prep_count in prep_count_by_bam.items():
        if prep_count == 0:
            missing_preps.append(bam)
        elif prep_count > 1:
            duplicate_preps.append(bam)

    def update_errors(errors, description, values):
        if not values:
            return

        errors.append('{}:\n\t{}'.format(description, '\n\t'.join(values)))

    errors = list()
    update_errors(errors, 'duplicate input bam files', duplicate_input_bams)
    update_errors(errors,
                  'bam files with multiple associations with prep output',
                  duplicate_preps)
    update_errors(errors,
                  'input bam files with no associated prep output',
                  missing_preps)
    update_errors(errors,
                  'bam files not in input but associated with prep output',
                  bams_only_in_prep)

    if errors:
        sys.exit('\n'.join(errors))

    print('Ok.')


def filter_countfile(fn):
    """TODO: Docstring for filter_countfile.
    :returns: TODO

    """
    with open(fn, 'r+') as fp:
        data = fp.readlines()
        header = data[0]
        rest = [header,]

        for line in data[1:]:
            eles = line.split('\t')
            if len(eles) != 7:
                sys.exit('ERROR: corrupted read count file: %s' % (fn))
            sum_ic_1 = 0
            sum_sc_1 = 0
            sum_ic_2 = 0
            sum_sc_2 = 0
            incv1 = list(map(int, eles[1].split(',')))
            skpv1 = list(map(int, eles[2].split(',')))
            incv2 = list(map(int, eles[3].split(',')))
            skpv2 = list(map(int, eles[4].split(',')))
            inc_len = int(eles[5])
            skp_len = int(eles[6])

            for i in range(len(incv1)):
                sum_ic_1 += incv1[i]
                sum_sc_1 += skpv1[i]
            for i in range(len(incv2)):
                sum_ic_2 += incv2[i]
                sum_sc_2 += skpv2[i]

            if (sum_ic_1 + sum_sc_1 > 0 and\
                    sum_ic_2 + sum_sc_2 > 0 and\
                    (sum_ic_1 != 0 or sum_ic_2 != 0) and\
                    (sum_sc_1 != 0 or sum_sc_2 != 0) and\
                    inc_len != 0 and skp_len != 0):
                rest.append(line)

        fp.seek(0)
        fp.writelines(rest)
        fp.truncate()

    return


def process_counts(istat, tstat, counttype, ase, cstat, od, tmp, stat,
                   paired_stats, python_executable, root_dir, imbalance_ratio):
    """TODO: Docstring for process_counts.
    :returns: TODO

    """
    efn = '%s/fromGTF.%s.txt' % (od, ase)
    sec_tmp = os.path.join(tmp, '%s_%s' % (counttype, ase))
    if os.path.exists(sec_tmp):
        if os.path.isdir(sec_tmp):
            shutil.rmtree(sec_tmp)
        else:
            os.unlink(sec_tmp)
    os.mkdir(sec_tmp)
    ostat = os.path.join(sec_tmp, 'rMATS_result_%s.txt')

    FNULL = open(os.devnull, 'w')
    resfp = open(ostat % (''), 'w')
    finfn = os.path.join(od, '%s.MATS.%s.txt' % (ase, counttype))
    indiv_counts_file_name = os.path.join(
        od, 'individualCounts.{}.txt'.format(ase))
    indiv_counts_temp_file_name = '{}.tmp'.format(indiv_counts_file_name)
    ostat_id = ostat % ('ID')
    ostat_inp = ostat % ('INP')
    ostat_il = ostat % ('I-L')
    ostat_pv = ostat % ('P-V')
    ostat_fdr = ostat % ('FDR')
    ostat_paired = ostat % ('paired')

    rmats_c = os.path.join(root_dir, 'rMATS_C/rMATSexe')
    paired_model = os.path.join(root_dir, 'rMATS_R/paired_model.R')
    pas_out = os.path.join(root_dir, 'rMATS_P/paste.py')
    inc_lvl = os.path.join(root_dir, 'rMATS_P/inclusion_level.py')
    fdr_cal = os.path.join(root_dir, 'rMATS_P/FDR.py')
    join_2f = os.path.join(root_dir, 'rMATS_P/joinFiles.py')

    if stat:
        filter_countfile(istat)

    if imbalance_ratio is not None:
        filter_countfile_by_imbalance_ratio(
            istat, indiv_counts_file_name, indiv_counts_temp_file_name,
            imbalance_ratio, ase)

    # Calculate inclusion levels
    subprocess.call([python_executable, pas_out, '-i', istat, '--o1', ostat_id, '--o2', ostat_inp,], stdout=FNULL)
    subprocess.call([python_executable, inc_lvl, ostat_inp, ostat_il,], stdout=FNULL)

    # Calculate PValue and FDR
    if stat:
        if paired_stats:
            # PAIRADISE writes a status file to the working directory.
            # Use the cwd kwarg of subprocess.call to set which
            # directory the status file gets written to.
            # This requires passing absolute path names to paired_model.R
            abs_istat = os.path.abspath(istat)
            abs_ostat_fdr = os.path.abspath(ostat_fdr)
            paired_command = ['Rscript', paired_model, abs_istat, str(tstat),
                              abs_ostat_fdr]
            with open(ostat_paired, 'wb') as paired_fp:
                paired_model_return_code = subprocess.call(
                    paired_command, stdout=paired_fp, stderr=subprocess.STDOUT,
                    cwd=sec_tmp)

            if paired_model_return_code != 0:
                print('error in paired model', file=sys.stderr)
                print_file_to_stderr(ostat_paired)
        else:
            subprocess.call([rmats_c, '-i', istat, '-t', str(tstat), '-o', ostat_pv, '-c', str(cstat),], stdout=FNULL)
            subprocess.call([python_executable, fdr_cal, ostat_pv, ostat_fdr,], stdout=FNULL)
    else:
        append_columns_with_defaults(istat, ostat_fdr, ['PValue', 'FDR'], ['NA', 'NA'])

    # Combine into final output
    subprocess.call(['paste', ostat_fdr, ostat_il,], stdout=resfp)
    subprocess.call([python_executable, join_2f, efn, resfp.name, '0', '0', finfn,], stdout=FNULL)
    append_individual_counts(indiv_counts_file_name, finfn,
                             indiv_counts_temp_file_name)

    FNULL.close()
    resfp.close()


def print_file_to_stderr(filename):
    with open(filename, 'rt') as file_handle:
        for line in file_handle:
            print(line, file=sys.stderr)


def append_columns_with_defaults(in_file_name, out_file_name, column_names, default_values):
    column_names_addition = '\t{}\n'.format('\t'.join(column_names))
    default_values_addition = '\t{}\n'.format('\t'.join(default_values))

    with open(in_file_name, 'rt') as in_file:
        with open(out_file_name, 'wt') as out_file:
            for i, raw_line in enumerate(in_file):
                line = raw_line.rstrip('\n')
                out_file.write(line)
                if i == 0:
                    out_file.write(column_names_addition)
                else:
                    out_file.write(default_values_addition)


def filter_countfile_by_imbalance_ratio(
        counts_file_name, indiv_counts_file_name, temp_file_name,
        imbalance_ratio, splicing_event_type):
    with open(counts_file_name, 'rt') as counts_file_handle:
        with open(indiv_counts_file_name, 'rt') as indiv_counts_file_handle:
            with open(temp_file_name, 'wt') as temp_file_handle:
                error = filter_countfile_by_imbalance_ratio_with_handles(
                    counts_file_handle, indiv_counts_file_handle,
                    temp_file_handle, imbalance_ratio, splicing_event_type)

    if error:
        formatted_message = (
            'error in filter_countfile_by_imbalance_ratio({}, {}, {}, {}, {})'
            .format(counts_file_name, indiv_counts_file_name, temp_file_name,
                    imbalance_ratio, splicing_event_type))
        print(formatted_message, file=sys.stderr)

    shutil.move(temp_file_name, counts_file_name)


def filter_countfile_by_imbalance_ratio_with_handles(
        counts_file_handle, indiv_counts_file_handle, temp_file_handle,
        imbalance_ratio, splicing_event_type):
    inverse_imbalance_ratio = 1 / imbalance_ratio
    calculate_ratios = get_calculate_ratios_for_event_type(splicing_event_type)
    if calculate_ratios is None:
        return 'unexpected splicing_event_type: {}'.format(splicing_event_type)

    for i, counts_line in enumerate(counts_file_handle):
        counts_line = counts_line.rstrip('\n')
        if i == 0:
            temp_file_handle.write('{}\n'.format(counts_line))
            indiv_counts_header_line = (
                indiv_counts_file_handle.readline().rstrip('\n'))
            indiv_counts_header_columns = indiv_counts_header_line.split('\t')
            continue

        counts_columns = counts_line.split('\t')
        counts_id = counts_columns[0]
        indiv_counts_columns = get_indiv_counts_columns_for_id(
            counts_id, indiv_counts_file_handle)
        if indiv_counts_columns is None:
            return 'ID: {} not found in individual count file'.format(counts_id)

        is_imbalanced, error = check_if_imbalanced(
            imbalance_ratio, inverse_imbalance_ratio,
            indiv_counts_header_columns, indiv_counts_columns, calculate_ratios)
        if error:
            return error

        if is_imbalanced:
            continue

        temp_file_handle.write('{}\n'.format(counts_line))

    return None


def append_individual_counts(counts_file_name, mats_file_name, temp_file_name):
    with open(counts_file_name, 'rt') as counts_file_handle:
        with open(mats_file_name, 'rt') as mats_file_handle:
            with open(temp_file_name, 'wt') as temp_file_handle:
                error = append_individual_counts_with_handles(
                    counts_file_handle, mats_file_handle, temp_file_handle)

    if error:
        formatted_message = (
            'error in append_individual_counts({}, {}, {}): {}'
            .format(counts_file_name, mats_file_name, temp_file_name, error))
        print(formatted_message, file=sys.stderr)

    shutil.move(temp_file_name, mats_file_name)


def append_individual_counts_with_handles(counts_file_handle, mats_file_handle,
                                          temp_file_handle):
    for i, mats_line in enumerate(mats_file_handle):
        mats_line = mats_line.rstrip('\n')
        mats_columns = mats_line.split('\t')
        if i == 0:
            counts_header_line = counts_file_handle.readline().rstrip('\n')
            counts_header_columns = counts_header_line.split('\t')
            counts_header_cols_without_id = counts_header_columns[1:]
            combined_line = '\t'.join(mats_columns
                                      + counts_header_cols_without_id)
            temp_file_handle.write('{}\n'.format(combined_line))
            continue

        mats_id = mats_columns[0]
        counts_columns = get_indiv_counts_columns_for_id(mats_id,
                                                         counts_file_handle)
        if counts_columns is None:
            return 'ID: {} not found in individual count file'.format(mats_id)

        counts_cols_without_id = counts_columns[1:]
        combined_line = '\t'.join(mats_columns + counts_cols_without_id)
        temp_file_handle.write('{}\n'.format(combined_line))

    return None


def try_parse_float(float_str):
    try:
        return float(float_str), None
    except ValueError as e:
        return None, 'error in try_parse_float({}): {}'.format(float_str, e)


def try_sum_floats(floats_string):
    float_strings = floats_string.split(',')
    float_sum = 0
    for float_string in float_strings:
        parsed_float, error = try_parse_float(float_string)
        if error:
            return None, 'try_sum_floats({}): {}'.format(floats_string, error)

        float_sum += parsed_float

    return float_sum, None


def calculate_ratio(a, b):
    if 0 in [a, b]:
        return 0

    return a / b


def calculate_ratios_se(headers, values):
    upstream_to_target_count = None
    target_to_downstream_count = None
    for i, header in enumerate(headers):
        if header == 'upstream_to_target_count':
            upstream_to_target_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'target_to_downstream_count':
            target_to_downstream_count, error = try_sum_floats(values[i])
            if error:
                return None, error

    if None in [upstream_to_target_count, target_to_downstream_count]:
        error = ('Missing expected headers in calculate_ratios_se({}, {})'
                 .format(headers, values))
        return None, error

    ratio = calculate_ratio(upstream_to_target_count, target_to_downstream_count)
    return [ratio], None


def calculate_ratios_mxe(headers, values):
    upstream_to_first_count = None
    first_to_downstream_count = None
    upstream_to_second_count = None
    second_to_downstream_count = None
    for i, header in enumerate(headers):
        if header == 'upstream_to_first_count':
            upstream_to_first_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'first_to_downstream_count':
            first_to_downstream_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'upstream_to_second_count':
            upstream_to_second_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'second_to_downstream_count':
            second_to_downstream_count, error = try_sum_floats(values[i])
            if error:
                return None, error

    if None in [upstream_to_first_count, first_to_downstream_count,
                upstream_to_second_count, second_to_downstream_count]:
        error = ('Missing expected headers in calculate_ratios_mxe({}, {})'
                 .format(headers, values))
        return None, error

    first_ratio = calculate_ratio(upstream_to_first_count,
                                  first_to_downstream_count)
    second_ratio = calculate_ratio(upstream_to_second_count,
                                   second_to_downstream_count)
    return [first_ratio, second_ratio], None


def calculate_ratios_alt_ss(headers, values):
    across_short_boundary_count = None
    long_to_flanking_count = None
    for i, header in enumerate(headers):
        if header == 'across_short_boundary_count':
            across_short_boundary_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'long_to_flanking_count':
            long_to_flanking_count, error = try_sum_floats(values[i])
            if error:
                return None, error

    if None in [across_short_boundary_count, long_to_flanking_count]:
        error = ('Missing expected headers in calculate_ratios_alt_ss({}, {})'
                 .format(headers, values))
        return None, error

    ratio = calculate_ratio(across_short_boundary_count, long_to_flanking_count)
    return [ratio], None


def calculate_ratios_ri(headers, values):
    upstream_to_intron_count = None
    intron_to_downstream_count = None
    for i, header in enumerate(headers):
        if header == 'upstream_to_intron_count':
            upstream_to_intron_count, error = try_sum_floats(values[i])
            if error:
                return None, error

        if header == 'intron_to_downstream_count':
            intron_to_downstream_count, error = try_sum_floats(values[i])
            if error:
                return None, error

    if None in [upstream_to_intron_count, intron_to_downstream_count]:
        error = ('Missing expected headers in calculate_ratios_ri({}, {})'
                 .format(headers, values))
        return None, error

    ratio = calculate_ratio(upstream_to_intron_count, intron_to_downstream_count)
    return [ratio], None


def get_calculate_ratios_for_event_type(event_type):
    if event_type == 'SE':
        return calculate_ratios_se
    if event_type == 'MXE':
        return calculate_ratios_mxe
    if event_type in ['A3SS', 'A5SS']:
        return calculate_ratios_alt_ss
    if event_type == 'RI':
        return calculate_ratios_ri

    return None


def check_if_imbalanced(imbalance_ratio, inverse_imbalance_ratio,
                        header_columns, counts_columns, calculate_ratios_func):
    ratios, error = calculate_ratios_func(header_columns,
                                          counts_columns)
    if error:
        return None, error

    for ratio in ratios:
        if ratio > imbalance_ratio or ratio < inverse_imbalance_ratio:
            return True, None

    return False, None


def get_indiv_counts_columns_for_id(mats_id, counts_file_handle):
    # The IDs have the same order in both files, but some IDs may only be
    # in the counts file.
    for counts_line in counts_file_handle:
        counts_line = counts_line.rstrip('\n')
        counts_columns = counts_line.split('\t')
        counts_id = counts_columns[0]
        if counts_id == mats_id:
            return counts_columns

    return None


def get_python_executable():
    # Try to get the absolute path of the executable for the running
    # Python interpreter.
    python_executable = sys.executable
    if not python_executable:
        # Fallback
        print('Absolute path for current Python interpreter not found.'
              ' Using "python" without a full path to run scripts',
              file=sys.stderr)
        python_executable = 'python'

    return python_executable


def generate_summary(python_executable, out_dir, root_dir):
    summary_script = os.path.join(root_dir, 'rMATS_P', 'summary.py')
    summary_out_file_path = os.path.join(out_dir, 'summary.txt')
    with open(summary_out_file_path, 'wb') as f_handle:
        subprocess.call([python_executable, summary_script, out_dir],
                        stdout=f_handle)


def main():
    """TODO: Docstring for main.
    :returns: TODO

    """
    args = get_args()

    if not os.path.exists(args.od) or not os.path.isdir(args.od):
        os.mkdir(args.od)
    if not os.path.exists(args.tmp) or not os.path.isdir(args.tmp):
        os.mkdir(args.tmp)

    if args.task == 'inte':
        check_integrity(args.bams, args.tmp)
    if args.task in pipe_tasks:
        run_pipe(args)

    if args.task not in ['post', 'both']:
        return

    jc_it = os.path.join(args.od, 'JC.raw.input.%s.txt')
    jcec_it = os.path.join(args.od, 'JCEC.raw.input.%s.txt')

    python_executable = get_python_executable()
    root_dir = os.path.abspath(os.path.dirname(__file__))

    print('Processing count files.')
    for event_type in ['SE', 'MXE', 'A3SS', 'A5SS', 'RI']:
        process_counts(jc_it % (event_type), args.tstat, 'JC', event_type,
                       args.cstat, args.od, args.tmp, args.stat,
                       args.paired_stats, python_executable, root_dir,
                       args.imbalance_ratio)
        process_counts(jcec_it % (event_type), args.tstat, 'JCEC', event_type,
                       args.cstat, args.od, args.tmp, args.stat,
                       args.paired_stats, python_executable, root_dir,
                       args.imbalance_ratio)

    generate_summary(python_executable, args.od, root_dir)
    print('Done processing count files.')

    return


if __name__ == "__main__":
    main()

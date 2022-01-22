# -----------------------------------------------------------------------------
# at_cascade: Cascading Dismod_at Analysis From Parent To Child Regions
#           Copyright (C) 2021-22 University of Washington
#              (Bradley M. Bell bradbell@uw.edu)
#
# This program is distributed under the terms of the
#     GNU Affero General Public License version 3.0 or later
# see http://www.gnu.org/licenses/agpl.txt
# -----------------------------------------------------------------------------
import os
import csv
import math
import at_cascade.ihme
# -----------------------------------------------------------------------------
#
# data_table = get_data_table(data_inp_file)
def get_data_table(data_inp_file) :
    #
    # map_location_id
    map_location_id = at_cascade.ihme.map_location_id
    #
    # data_table
    file_ptr   = open(data_inp_file)
    reader     = csv.DictReader(file_ptr)
    data_table = list()
    for row_in in reader :
        #
        # location_id
        location_id  = int( row_in['location_id'] )
        if location_id in map_location_id :
            location_id = map_location_id[location_id]
        #
        # is_outlier
        is_outlier   = int( row_in['is_outlier'] )
        #
        # nid
        if row_in['nid'] == 'NA' :
            nid = None
        else :
            nid          = int( row_in['nid'] )
        #
        # age_lower, age_upper
        age_lower    = float( row_in['age_start'] )
        age_upper    = float( row_in['age_end'] )
        if 'age_demographer' in row_in :
            if int( row_in['age_demographer'] ) != 0 :
                age_upper = age_upper + 1.0
        #
        # c_seq
        if row_in['seq'] == 'NA' :
            c_sed = None
        else :
            c_seq = int( row_in['seq'] )
        #
        # sex_name
        sex_name     = row_in['sex']
        assert sex_name in { 'Male', 'Female' }
        #
        # time_lower, time_upper
        time_lower   = float( row_in['year_start'] )
        time_upper   = float( row_in['year_end'] )  + 1.0
        #
        # meas_value
        meas_value   = float( row_in['mean'] )
        #
        # meas_std
        meas_std     = float( row_in['standard_error'] )
        if meas_std <= 0.0 :
            sample_size = float( row_in['sample_size'] )
            std_5 = math.sqrt( meas_value / sample_size )
            if meas_value * sample_size < 5.0 :
                std_0 = 1.0 / sample_size
                meas_std  = (5.0 - meas_value * sample_size) * std_0
                meas_std += meas_value * sample_size * std_5
                meas_std  = meas_std / 5.0
        #
        # integrand_name
        integrand_name = row_in['measure']
        if integrand_name == 'incidence' :
            integrand_name = 'Sincidence'
        #
        # row_out
        row_out = {
            'c_seq' :          c_seq,
            'location_id' :    location_id,
            'sex_name' :       sex_name,
            'integrand_name' : integrand_name,
            'is_outlier' :     is_outlier,
            'nid'        :     nid,
            'age_lower' :      age_lower,
            'age_upper' :      age_upper,
            'time_lower' :     time_lower,
            'time_upper' :     time_upper,
            'meas_value' :     meas_value,
            'meas_std' :       meas_std,
        }
        #
        data_table.append( row_out )
    file_ptr.close()
    return data_table
# -----------------------------------------------------------------------------
#
# csmr_table = get_csmr_table(csmr_inp_file, age_group_id_dict)
def get_csmr_table(csmr_inp_file, age_group_id_dict) :
    #
    # map_location_id
    map_location_id = at_cascade.ihme.map_location_id
    #
    # csmr_table
    file_ptr   = open(csmr_inp_file)
    reader     = csv.DictReader(file_ptr)
    csmr_table = list()
    for row_in in reader :
        #
        # location_id
        location_id  = int( row_in['location_id'] )
        if location_id in map_location_id :
            location_id = map_location_id[location_id]
        #
        # age_group_id
        age_group_id = int( row_in['age_group_id'] )
        #
        # is_outlier, c_seq
        is_outlier   = 0
        c_seq        = None
        #
        # age_lower, age_upper
        age_lower    = age_group_id_dict[age_group_id]['age_lower']
        age_upper    = age_group_id_dict[age_group_id]['age_upper']
        #
        # sex_name
        sex_name     = row_in['sex']
        #
        # time_lower, time_upper
        time_lower   = float( row_in['year_id'] )
        time_upper   = float( row_in['year_id'] )  + 1.0
        #
        # meas_value
        meas_value   = float( row_in['val'] )
        #
        # meas_std
        lower    = float( row_in['lower'] )
        upper    = float( row_in['upper'] )
        meas_std = (upper - lower) / 2.0
        #
        # integrand_name
        integrand_name = 'mtspecific'
        #
        # row_out
        row_out = {
            'c_seq' :          c_seq,
            'location_id' :    location_id,
            'sex_name' :       sex_name,
            'integrand_name' : integrand_name,
            'is_outlier' :     is_outlier,
            'nid'        :     None,
            'age_lower' :      age_lower,
            'age_upper' :      age_upper,
            'time_lower' :     time_lower,
            'time_upper' :     time_upper,
            'meas_value' :     meas_value,
            'meas_std' :       meas_std,
        }
        if sex_name != 'Both' :
            assert sex_name in { 'Male', 'Female' }
            csmr_table.append( row_out )
    file_ptr.close()
    return csmr_table
# -----------------------------------------------------------------------------
#
# write_data_table(
#   data_inp_file, csmr_inp_file, covariate_csv_file_dict, data_table_file
# )
def write_data_table(
    result_dir              = None,
    data_inp_file           = None,
    csmr_inp_file           = None,
    covariate_csv_file_dict = None,
    log_scale_covariate_set = None,
    ) :
    assert type(result_dir) == str
    assert type(data_inp_file) == str
    assert type(csmr_inp_file) == str or csmr_inp_file is None
    assert type(covariate_csv_file_dict) == dict
    assert type(log_scale_covariate_set) == set
    #
    # data_table_file
    data_table_file = at_cascade.ihme.csv_file['data']
    data_table_file = f'{result_dir}/{data_table_file}'
    #
    if os.path.exists(data_table_file) :
        print( f'Using existing {data_table_file}' )
        return
    else :
        print( f'Creating {data_table_file}' )
    #
    # node_table_file
    node_table_file = at_cascade.ihme.csv_file['node']
    node_table_file = f'{result_dir}/{node_table_file}'
    #
    # age_group_id_dict
    age_group_id_table = at_cascade.ihme.get_age_group_id_table()
    age_group_id_dict   = dict()
    for row in age_group_id_table :
        age_group_id = row['age_group_id']
        age_group_id_dict[age_group_id] = row
    #
    # data_table
    data_table = get_data_table(data_inp_file)
    #
    # This data is not for fitting but rather to adjust the omega constraint
    # 2DO: remove get_csmr_table from this file.
    if csmr_inp_file is not None :
        # csmr_table
        csmr_table = get_csmr_table(csmr_inp_file, age_group_id_dict)
        #
        # data_table
        assert set( data_table[0].keys() ) == set( csmr_table[0].keys() )
        data_table += csmr_table
    #
    # location_id2node_id
    file_ptr            = open(node_table_file)
    reader              = csv.DictReader(file_ptr)
    location_id2node_id = dict()
    node_id             = 0
    for row in reader :
        assert node_id == int( row['node_id'] )
        location_id = int( row['location_id'] )
        location_id2node_id[location_id] = node_id
        node_id += 1
    file_ptr.close()
    #
    # data_table
    for row in data_table :
        row['node_id'] = location_id2node_id[ row['location_id'] ]
    #
    # data_table
    for covariate_name in covariate_csv_file_dict :
        #
        # covariate_file_path
        covariate_file_path = covariate_csv_file_dict[covariate_name]
        assert covariate_file_path.endswith( '_covariate.csv')
        #
        # interpolate_covariate
        log_scale = covariate_name in log_scale_covariate_set
        (one_age_group, interpolate_covariate) = \
            at_cascade.ihme.get_interpolate_covariate(
                covariate_file_path, log_scale, age_group_id_dict
        )
        #
        # row
        for row in data_table :
            #
            # location_id
            location_id = row['location_id']
            #
            # row[covariate_name]
            if location_id not in interpolate_covariate :
                row[covariate_name] = None
            else :
                #
                # sex_name, location_id
                sex_name    = row['sex_name']
                assert sex_name in [ 'Male', 'Female' ]
                #
                # age, time
                age  = (row['age_lower']  + row['age_upper'])  / 2.0
                time = (row['time_lower'] + row['time_upper']) / 2.0
                #
                # fun
                if sex_name in interpolate_covariate[location_id] :
                    fun   = interpolate_covariate[location_id][sex_name]
                elif 'Both' in interpolate_covariate[location_id] :
                    fun   = interpolate_covariate[location_id]['Both']
                else :
                    fun  = None
                #
                # value
                if fun is None :
                    value = None
                elif one_age_group :
                    value = fun(time)
                else :
                    value = fun(age, time, grid = False)
                #
                # row[covariate_name]
                row[covariate_name] = value
    #
    # data_table_file
    at_cascade.ihme.write_csv(data_table_file, data_table)

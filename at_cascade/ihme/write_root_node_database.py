# -----------------------------------------------------------------------------
# at_cascade: Cascading Dismod_at Analysis From Parent To Child Regions
#           Copyright (C) 2021-22 University of Washington
#              (Bradley M. Bell bradbell@uw.edu)
#
# This program is distributed under the terms of the
#     GNU Affero General Public License version 3.0 or later
# see http://www.gnu.org/licenses/agpl.txt
# -----------------------------------------------------------------------------
import copy
import math
import statistics
import dismod_at
import at_cascade.ihme
# -----------------------------------------------------------------------------
def get_file_path(csv_file_key, result_dir) :
    csv_file  = at_cascade.ihme.csv_file
    file_name = csv_file[csv_file_key]
    file_name = f'{result_dir}/{file_name}'
    return file_name
# -----------------------------------------------------------------------------
def write_root_node_database(
    result_dir              = None,
    root_node_database      = None,
    hold_out_nid_set        = None,
    covariate_csv_file_dict = None,
    gamma_factor            = None,
    root_node_name          = None,
    random_seed             = None,
    model_rate_age_grid     = None,
    model_rate_time_grid    = None,
) :
    assert type(result_dir) == str
    assert type(root_node_database) == str
    assert type(hold_out_nid_set) == set
    assert type(covariate_csv_file_dict) == dict
    assert type(root_node_name) == str
    assert type(random_seed) == int
    assert type(model_rate_age_grid) == list
    assert type(model_rate_time_grid) == list
    #
    print( 'Creating ' + root_node_database )
    #
    data_table_file       = get_file_path('data', result_dir)
    node_table_file       = get_file_path('node', result_dir)
    omega_age_table_file  = get_file_path('omega_age', result_dir)
    omega_time_table_file = get_file_path('omega_time', result_dir)
    #
    # table_in
    table_in = dict()
    table_in['data']      = at_cascade.ihme.get_table_csv(data_table_file )
    table_in['node']      = at_cascade.ihme.get_table_csv(node_table_file )
    table_in['omega_age'] = at_cascade.ihme.get_table_csv(omega_age_table_file)
    table_in['omega_time'] = \
        at_cascade.ihme.get_table_csv(omega_time_table_file)
    # sex_name2covariate_value
    sex_name2covariate_value = dict()
    sex_info_dict            = at_cascade.ihme.sex_info_dict
    for sex_name in sex_info_dict :
        sex_name2covariate_value[sex_name] = \
            sex_info_dict[sex_name]['covariate_value']
    #
    # integrand_median
    integrand_list = dict()
    for row in table_in['data'] :
        integrand = row['integrand_name']
        if integrand not in integrand_list :
            integrand_list[integrand] = list()
        integrand_list[integrand].append( float(row['meas_value']) )
    integrand_median = dict()
    for integrand in integrand_list :
        integrand_median[integrand] = \
            statistics.median( integrand_list[integrand] )
    #
    # subgroup_table
    subgroup_table = [ {'subgroup': 'world', 'group':'world'} ]
    #
    # age_min, age_max, time_min, time_max
    age_min =   math.inf
    age_max =   125.0        # maximum age in get_age_group_id_table
    time_min =  math.inf
    time_max =  2021         # year after last year_id in predict_csv
    for row in table_in['data'] :
        age_min  = min(age_min,  float( row['age_lower'] ) )
        time_min = min(time_min, float( row['time_lower'] ) )
        age_max  = max(age_max,  float( row['age_upper'] ) )
        time_max = max(time_max, float( row['time_upper'] ) )
    #
    # age_list, age_grid_id_list
    if 0.0 in model_rate_age_grid :
        age_list         = copy.copy( model_rate_age_grid )
        age_grid_id_list = list( range(0, len(model_rate_age_grid) ) )
    else :
        age_list         = [ 0.0 ] + model_rate_age_grid
        age_grid_id_list = list( range(1, len(model_rate_age_grid) ) )
    for row in table_in['omega_age'] :
        age = float( row['age'] )
        age = round(age, at_cascade.ihme.age_grid_n_digits)
        if age not in age_list :
            age_list.append(age)
    if age_min < min( age_list ) :
        age_list.append(age_min)
    if age_max > max( age_list ) :
        age_list.append( age_max)
    #
    # , time_grid_id_list
    time_list   = copy.copy( model_rate_time_grid )
    time_grid_id_list = list( range(0, len(time_list) ) )
    for row in table_in['omega_time'] :
        time = float( row['time'] )
        if time not in time_list :
            time_list.append(time)
    if time_min < min( time_list ) :
        time_list.append(time_min)
    if time_max > max( time_list ) :
        time_list.append( time_max)
    #
    # mulcov_table
    mulcov_table = [
        {   # alpha_iota_obesity
            'covariate': 'obesity',
            'type':      'rate_value',
            'effected':  'iota',
            'group':     'world',
            'smooth':    'alpha_smooth',
        },
        {   # alpha_chi_log_ldi
            'covariate': 'log_ldi',
            'type':      'rate_value',
            'effected':  'chi',
            'group':     'world',
            'smooth':    'alpha_smooth',
        },
        {   # alpha_iota_sex
            'covariate': 'sex',
            'type':      'rate_value',
            'effected':  'iota',
            'group':     'world',
            'smooth':    'alpha_smooth',
        },
        {   # alpha_chi_sex
            'covariate': 'sex',
            'type':      'rate_value',
            'effected':  'chi',
            'group':     'world',
            'smooth':    'alpha_smooth',
        },
    ]
    for integrand in integrand_median :
        mulcov_table.append(
            {   # gamma_integrand
                'covariate':  'one',
                'type':       'meas_noise',
                'effected':   integrand,
                'group':      'world',
                'smooth':     f'gamma_{integrand}',
            }
        )
    #
    # integrand_table
    integrand_table = list()
    for integrand_name in at_cascade.ihme.integrand_name2measure_id :
        row = { 'name' : integrand_name, 'minimum_meas_cv' : '0.1' }
        integrand_table.append( row )
    for j in range( len(mulcov_table) ) :
        integrand_table.append( { 'name' : f'mulcov_{j}' } )
    #
    # node_table, location_id2node_id
    node_table          = list()
    location_id2node_id = dict()
    node_id    = 0
    for row_in in table_in['node'] :
        location_id    = int( row_in['location_id'] )
        node_name      = row_in['node_name']
        if row_in['parent_node_id'] == '' :
            parent_node_name = ''
        else :
            parent_node_id   = int( row_in['parent_node_id'] )
            parent_node_name = table_in['node'][parent_node_id]['node_name']
        row_out = { 'name' : node_name, 'parent' : parent_node_name }
        node_table.append( row_out )
        location_id2node_id[location_id] = node_id
        #
        assert node_id == int( row_in['node_id'] )
        node_id += 1
    #
    # covarite_table
    # Becasue we are using data4cov_reference, the reference for the relative
    # covariates obesity and log_ldi will get replaced.
    # The names in this table must be 'sex', 'one', and the keys in the
    # covariate_csv_file_dict.
    covariate_table = [
        { 'name':'sex',     'reference':0.0, 'max_difference':0.6},
        { 'name':'one',     'reference':0.0 },
        { 'name':'obesity', 'reference':0.0},
        { 'name':'log_ldi', 'reference':0.0},
    ]
    #
    # data_table
    data_table = list()
    for row_in in table_in['data'] :
        location_id = int( row_in['location_id'] )
        is_outlier  = int( row_in['is_outlier'] )
        sex_name    = row_in['sex_name']
        #
        if row_in['nid'] == '' :
            nid = None
        else :
            nid = int( row_in['nid'] )
        #
        if row_in['c_seq'] == '' :
            c_seq = None
        else :
            c_seq = int( row_in['c_seq'] )
        #
        hold_out    = is_outlier
        if nid in hold_out_nid_set :
            hold_out = 1
        #
        node_id     = location_id2node_id[location_id]
        node_name   = node_table[node_id]['name']
        sex         = sex_name2covariate_value[ row_in['sex_name'] ]
        #
        row_out  = {
            'integrand'       : row_in['integrand_name'],
            'node'            : node_name,
            'subgroup'        : 'world',
            'weight'          : '',
            'age_lower'       : float( row_in['age_lower'] ),
            'age_upper'       : float( row_in['age_upper'] ),
            'time_lower'      : float( row_in['time_lower'] ),
            'time_upper'      : float( row_in['time_upper'] ),
            'sex'             : sex,
            'one'             : 1.0,
            'hold_out'        : hold_out,
            'density'         : 'gaussian',
            'meas_value'      : float( row_in['meas_value'] ),
            'meas_std'        : float( row_in['meas_std'] ),
            'c_seq'           : c_seq,
        }
        for cov_name in covariate_csv_file_dict.keys() :
            if row_in[cov_name] == '' :
                cov_value = None
            else :
                cov_value = float( row_in[cov_name] )
            row_out[cov_name] = cov_value
        data_table.append( row_out )
    #
    # prior_table
    prior_table = [
        {
            'name'    :    'parent_rate_value',
            'density' :    'log_gaussian',
            'lower'   :    1e-7,
            'upper'   :    1.0,
            'mean'    :    1e-2,
            'std'     :    3.0,
            'eta'     :    1e-7,
        },{
            'name'    :    'parent_pini_value',
            'density' :    'gaussian',
            'lower'   :    0.0,
            'upper'   :    1e-4,
            'mean'    :    1e-5,
            'std'     :    1.0,
        },{
            'name'    :    'parent_chi_delta',
            'density' :    'log_gaussian',
            'lower'   :    None,
            'upper'   :    None,
            'mean'    :    0.0,
            'std'     :    1.0,
            'eta'     :    1e-7,
        },{
            'name'    :    'parent_iota_dage',
            'density' :    'log_gaussian',
            'lower'   :    None,
            'upper'   :    None,
            'mean'    :    0.0,
            'std'     :    1.0,
            'eta'     :    1e-7,
        },{
            'name'    :    'parent_iota_dtime',
            'density' :    'log_gaussian',
            'lower'   :    None,
            'upper'   :    None,
            'mean'    :    0.0,
            'std'     :    0.3,
            'eta'     :    1e-7,
        },{
            'name'    :   'child_rate_value',
            'density' :   'gaussian',
            'lower'   :   None,
            'upper'   :   None,
            'mean'    :   0.0,
            'std'     :   .1,
        },{
            'name'    :   'alpha_value',
            'density' :   'gaussian',
            'lower'   :   None,
            'upper'   :   None,
            'mean'    :   0.0,
            'std'     :   1.0,
        }
    ]
    for integrand in integrand_median :
        gamma = gamma_factor * integrand_median[integrand]
        prior_table.append(
            {
                'name'    :   f'gamma_{integrand}',
                'density' :   'uniform',
                'lower'   :   gamma,
                'upper'   :   gamma,
                'mean'    :   gamma,
            }
        )
    # ------------------------------------------------------------------------
    # smooth_table
    smooth_table = list()
    #
    # parrent_chi
    fun = lambda a, t :  \
        ('parent_rate_value', 'parent_chi_delta', 'parent_chi_delta')
    smooth_table.append({
        'name':     'parent_chi',
        'age_id':   age_grid_id_list,
        'time_id':  time_grid_id_list,
        'fun':      fun
    })
    #
    # parrent_iota
    fun = lambda a, t :  \
        ('parent_rate_value', 'parent_iota_dage', 'parent_iota_dtime')
    smooth_table.append({
        'name':     'parent_iota',
        'age_id':   age_grid_id_list,
        'time_id':  time_grid_id_list,
        'fun':      fun
    })
    #
    # parent_pini
    fun = lambda a, t :  \
        ('parent_pini_value', None, None)
    smooth_table.append({
        'name':     'parent_pini',
        'age_id':   [0],
        'time_id':  [0],
        'fun':      fun
    })
    #
    # child_smooth
    fun = lambda a, t : ('child_rate_value', None, None)
    smooth_table.append({
         'name':    'child_smooth',
        'age_id':    [0],
        'time_id':   [0],
        'fun':       fun
    })
    #
    # alpha_smooth
    fun = lambda a, t : ('alpha_value', None, None)
    smooth_table.append({
        'name':    'alpha_smooth',
        'age_id':    [0],
        'time_id':   [0],
        'fun':       fun
    })
    #
    # gamma_integrand
    for integrand in integrand_median :
        # fun = lambda a, t : ('gamma_{integrand}', None, None) )
        fun = eval( f"lambda a, t : ( 'gamma_{integrand}', None, None)" )
        smooth_table.append({
            'name':    f'gamma_{integrand}',
            'age_id':   [0],
            'time_id':  [0],
            'fun':      copy.copy(fun)
        })
    #
    # rate_table
    rate_table = [
        {
            'name':          'pini',
            'parent_smooth': 'parent_pini',
            'child_smooth':  None,
        },{
            'name':           'iota',
            'parent_smooth': 'parent_iota',
            'child_smooth':  'child_smooth',
        },{
            'name':           'chi',
            'parent_smooth': 'parent_chi',
            'child_smooth':  'child_smooth',
        }
    ]
    #
    # option_table
    option_table = [
        { 'name':'parent_node_name',     'value':root_node_name},
        { 'name':'zero_sum_child_rate',  'value':'iota chi'},
        { 'name':'random_seed',          'value':str(random_seed)},
        { 'name':'trace_init_fit_model', 'value':'true'},
        { 'name':'data_extra_columns',   'value':'c_seq'},
        { 'name':'meas_noise_effect',    'value':'add_std_scale_none'},
        { 'name':'age_avg_split',        'value':'0.1 1.0'},
        #
        { 'name':'quasi_fixed',                  'value':'false' },
        { 'name':'tolerance_fixed',              'value':'1e-8'},
        { 'name':'max_num_iter_fixed',           'value':'40'},
        { 'name':'print_level_fixed',            'value':'5'},
        { 'name':'accept_after_max_steps_fixed', 'value':'10'},
    ]
    # Diabetes does not have enough incidence data to estimate
    # both iota and chi without mtexcess. Also see the minimum_cv setting
    # for mtexcess in the integand table.
    # { 'name':'hold_out_integrand',   'value':'mtexcess'},
    #
    # create_database
    file_name      = root_node_database
    nslist_table   = list()
    avgint_table   = list()
    weight_table   = list()
    dismod_at.create_database(
         file_name,
         age_list,
         time_list,
         integrand_table,
         node_table,
         subgroup_table,
         weight_table,
         covariate_table,
         avgint_table,
         data_table,
         prior_table,
         smooth_table,
         nslist_table,
         rate_table,
         mulcov_table,
         option_table
    )
# ----------------------------------------------------------------------------

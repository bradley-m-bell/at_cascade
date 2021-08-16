# -----------------------------------------------------------------------------
# at_cascade: Cascading Dismod_at Analysis From Parent To Child Regions
#           Copyright (C) 2021-21 University of Washington
#              (Bradley M. Bell bradbell@uw.edu)
#
# This program is distributed under the terms of the
#     GNU Affero General Public License version 3.0 or later
# see http://www.gnu.org/licenses/agpl.txt
# -----------------------------------------------------------------------------
'''
{xsrst_begin create_child_node_db}

Create Child Database From Fit in Parent Database
#################################################

Syntax
******
{xsrst_file
    # BEGIN syntax
    # END syntax
}

all_node_database
*****************
is a python string containing the name of the :ref:`all_node_db`.
This argument can't be ``None``.

root_node_database
******************
is a python string containing the name of the
:ref:`glossary.root_node_database`.
The option table in this database must have ``parent_node_name``
and must not have ``parent_node_id``.
This argument can't be ``None``.

parent_node_database
********************
is a python string containing the name of a :ref:`glossary.fit_node_database`
that has the results of a dismod_at sample command for both the fixed
and random effects. These will be used to create priors in the
child not databases.

parent_node
===========
We use *parent_node* to refer to the parent node in the
dismod_at option table in the *parent_node_database*.

child_node_databases
********************
is a python dictionary and if *child_name* is a key for *child_node_databases*,
*child_name* is a :ref:`glossary.node_name` and a child of the *parent_node*.
The value *child_node_databases[child_name]* is the name of
a *fit_node_database* that is created by this command.
In this database, *child_name* will be the parent node in
the dismod_at option table.
This database will only have the dismod_at input tables.
The value priors for the variables in the model will be constructed using
the samples in the *parent_node_database*.
Other priors will be the same as in the *root_node_database*

{xsrst_end create_child_node_db}
'''
def table_name2id(table, col_name, row_name) :
    for (row_id, row) in emumerate(table) :
        if row[col_name] == row_name :
            return row_id
    assert False
#
def create_child_node_db(
# BEGIN syntax
# at_cascade.create_child_node_db(
    all_node_database    = None ,
    root_node_database   = None ,
    parent_node_database = None ,
    child_node_databases = None ,
# )
# END syntax
) :
    # covariate_reference_table
    new        = False
    connection = dismod_at.create_connection(all_node_database, new)
    covariate_reference_table = dismod_at.get_table_dict(
        connection, 'covariate_reference'
    )
    connection.close()
    #
    # root_tables
    new         = False
    connection  = dismod_at.create_connection(root_node_database, new)
    root_tables = dict()
    for name in [
        'covariate',
        'density',
        'node',
        'option',
    ] :
        root_tables[name] = dismod_at.get_table_dict(connection, name)
    #
    # parent_tables
    new           = False
    connection    = dismod_at.create_connection(parent_node_database, new)
    parent_tables = dict()
    for name in [
        'covariate',
        'fit_var',
        'mulcov',
        'rate',
        'sample',
        'smooth',
        'smooth_grid',
        'var'
    ] :
        parent_tables[name] = dismod_at.get_table_dict(connection, name)
    connection.close()
    #
    # parent_var_id2key
    parent_var_id2key= list()
    for row in var_table :
        mulcov_id = row['mulcov_id']
        rate_id   = row['rate_id']
        node_id   = row['node_id']
        age_id    = row['age_id']
        time_id   = row['time_id']
        key       = (mulcov_id, rate_id, node_id, age_id, time_id )
        parent_var_id2key.append(key)
    #
    # parent_fit_value
    parend_fit_value = dict()
    for (var_id, row) in enumerate(parent_tables['fit_var']) :
        key                   = parent_var_id2key[var_id]
        parent_fit_value[key] = row['fit_var_value']
    #
    # parent_sample_list
    # Note that index in parent_sample_list[key] is the sample_index because
    # sample_index is monotone non-decreasing in the sample_table.
    parent_sample_list = dict()
    for row in parent_tables['sample'] :
        var_id  = row['var_id']
        key     = parent_var_id2key[var_id]
        if not key in parent_sample_list :
            parent_sample_list[key] = list()
        parent_sample_list[key].append( ['var_value'] )
    #
    # parent_node_name
    parent_node_name = None
    for row in root_tables['option'] :
        assert row['option_name'] != 'parent_node_id'
        if row['option_name'] == 'parent_node_name' :
            parent_node_name = row['option_value']
    assert parent_node_name is not None
    #
    # parent_node_id
    parent_node_id = table_name2id(node_table, 'node_name', parent_node_name)
    #
    # node_table
    node_table = root_tables['node']
    #
    # gaussian_density_id
    table              = root_tables['density']
    gaussian_density_id = table_name2id(table, 'density_name', 'gaussian')
    #
    for child_name in child_node_databases :
        # ---------------------------------------------------------------------
        # create child_node_databases[child_name]
        # ---------------------------------------------------------------------
        #
        # child_node_id
        child_node_id = table_name2id(node_table, 'node_name', child_name)
        assert node_table[child_node]['parent'] == parent_node_id
        #
        # child_node_database = root_node_database
        child_database = child_node_databases[child_name]
        shiutil.copyfile(root_node_database, child_database)
        #
        # child_connection
        new        = False
        child_connection = dismod_at.create_connection(child_database, new)
        #
        # child_option_table
        child_option_table = copy.copy(root_tables['option'])
        for row in child_option_table :
            if row['option_name'] == 'parent_node_name' :
                row['option_value'] = child_name
        tbl_name = 'option'
        dismod_at.replace_table(child_connection, tbl_name, child_option_table)
        #
        # child_covariate_table
        child_covariate_table = copy.copy(root_tables['covariate'])
        for child_row in child_covariate_table :
            child_row['reference'] = None
        for row in covariate_reference_table :
            if row['node_id'] == child_node_id :
                covariate_id           = row['covariate_id']
                child_row              = child_covariate_table[covariate_id]
                child_row['reference'] = row['reference']
        for child_row in child_covariate_table :
            assert not child_row['reference'] is None
        #
        # covariate_difference
        covariate_difference = list()
        for covaraite_id in range(len(child_covaraite_table)) :
            child_row  = child_covaraite_table[covariate_id]
            parent_row = parent_tables['covariate'][covariate_id]
            difference = child_row['reference'] - parent_row['reference']
            covariate_difference.append(difference)
        # --------------------------------------------------------------------
        # initilaize child smooth and smooth_grid tables as empty
        child_smooth_table      = list()
        child_smooth_grid_table = list()
        #
        # initialize child_prior_table
        child_prior_table = copy.copy( root_table['prior'] )
        # --------------------------------------------------------------------
        # child_mulcov_table
        # and corresponding entries in the following child tables:
        # smooth, smooth_grid, and prior
        child_mulcov_table = copy.copy( parent_tables['mulcov'] )
        for (mulcov_id, child_mulcov_row) in enumerate(child_mulcov_table) :
            assert child_mulcov_row['subgroup_smooth_id'] is None
            parent_smooth_id = child_mulcov_row['group_smooth_id']
            if not parent_smooth_id is None :
                #
                smooth_row = parent_tables['smooth'][parent_smooth_id]
                smooth_row = copy.copy(parent_smooth_row)
                #
                # update: child_smooth_table
                child_smooth_table.append(smooth_row)
                child_smooth_id = len(child_smooth_table)
                #
                # change child_mulcov_table to use the new smoothing
                child_mulcov_row['group_smooth_id'] = child_smooth_id
                #
                # add rows for this smoothing to child_smooth_grid_table
                for parent_grid_row in parent_tables['smooth_grid'] :
                    if parent_grid_row['smooth_id'] == parent_smooth_id :
                        #
                        # parent_prior_row
                        prior_id         = parent_grid_row['value_prior_id']
                        parent_prior_row = parent_tables['prior'][prior_id]
                        #
                        # key
                        rate_id   = None
                        node_id   = None
                        age_id    = parent_grid_row['age_id']
                        time_id   = parent_grid_row['time_id']
                        key = (mulcov_id, rate_id, node_id, age_id, time_id)
                        #
                        mean = parent_fit_value[key]
                        std  = statistics.stdev(parent_sample_list, xbar=mean)
                        #
                        # update: child_prior_table
                        child_prior_row         = copy.copy( parent_prior_row )
                        child_prior_row['mean'] = mean
                        child_prior_row['std']  = std
                        child_prior_row['density_id'] = gaussian_density_id
                        child_prior_table.append( child_prior_row )
                        #
                        # update: child_smooth_grid_table
                        child_grid_row = copy.copy( parent_grid_row )
                        child_prior_id = len(child_prior_table)
                        child_grid_row['value_prior_id'] = child_prior_id
                        child_grid_row['smooth_id']      = child_smooth_id
                        child_smooth_grid_table.append( child_grid_row )

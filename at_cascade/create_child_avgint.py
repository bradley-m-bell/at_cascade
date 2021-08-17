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
{xsrst_begin create_child_avgint}
{xsrst_spell
    integrands
    mulcov
}

Create avgint Table That Predicts Rates for Child Nodes
#######################################################

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

parent_node_database
********************
is a python string containing the name of a :ref:`glossary.fit_node_database`
that will be the parent node for this predictions.
The avgint table will be placed in this database.
The previous avgint table in this database is lost.
This argument can't be ``None``.

parent_node
===========
We use *parent_node* to refer to the parent node in the
dismod_at option table in the *parent_node_database*.

integrand_table
===============
The integrand table in the *parent_node_database* must include the following:
:ref:`glossary.Sincidence`,
:ref:`glossary.remission`,
:ref:`glossary.mtexcess`.
Integrands with a null parent smoothing id need not be included.
In addition, the integrand table must include all the covariate multipliers;
i.e., ``mulcov_``\ *mulcov_id* where *mulcov_id* is the id
for any covariate multiplier.
Integrands with a null group smoothing id need not be included.

avgint Table
************
The new avgint table has all the standard dismod_at columns
plus the following extra columns:

c_mulcov_id
===========
If this column is not null,
it identifies the covariate multiplier that this prediction is for.
All of the covariate multipliers,
except for ones that have null for the group_smooth_id in the
mulcov table in the *parent_node_database*,
are represented the new avgint table.


c_rate_id
=========
If this column is not null,
it identifies which rate a prediction is for.
(Either *c_mulcov_id* or *c_rate_id* is null but not both.)
All the rates, except omega and rates that do not do not have null for the
parent_smooth_id in the rate table in the *parent_node_database*,
are represented the new avgint table.

c_node_id
=========
If this is a rate prediction,
this column identifies which child a prediction is for
(otherwise this column is null).
All the children of the parent node are represented in the new avgint table.

c_age_id
========
This column identifies the age,
in the *parent_node_database*, that this prediction are for.

c_time_id
_========
This column identifies the time,
in the *parent_node_database*, that this prediction are for.

Rectangular Grid
================
For each rate (or covariate multiplier) that has a non-null
parent smoothing (group smoothing) in the *parent_node_database*,
all of the age time pairs in the smoothing are represented
in the new avgint table

{xsrst_end create_child_avgint}
'''
# ----------------------------------------------------------------------------
import dismod_at
# ----------------------------------------------------------------------------
def table_name2id(table, col_name, row_name) :
    for (row_id, row) in enumerate(table) :
        if row[col_name] == row_name :
            return row_id
    assert False
# ----------------------------------------------------------------------------
def create_child_avgint(
# BEGIN syntax
# at_cascade.create_child_avgint(
    all_node_database    = None ,
    parent_node_database = None ,
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
    # parent_tables
    new           = False
    connection    = dismod_at.create_connection(parent_node_database, new)
    parent_tables = dict()
    for name in [
        'age',
        'covariate',
        'integrand',
        'mulcov',
        'node',
        'option',
        'rate',
        'smooth_grid',
        'time',
    ] :
        parent_tables[name] = dismod_at.get_table_dict(connection, name)
    connection.close()
    #
    # rate_table
    rate_table = parent_tables['rate']
    #
    # node_table
    node_table = parent_tables['node']
    #
    # n_covariate
    n_covariate = len( parent_tables['covariate'] )
    #
    # parent_node_id
    parent_node_name = None
    for row in parent_tables['option'] :
        assert row['option_name'] != 'parent_node_id'
        if row['option_name'] == 'parent_node_name' :
            parent_node_name = row['option_value']
    assert parent_node_name is not None
    parent_node_id = table_name2id(node_table, 'node_name', parent_node_name)
    #
    # child_covariate_reference
    child_covariate_reference = dict()
    for (node_id, row) in enumerate(node_table) :
        if row['parent'] == parent_node_id :
            reference = n_covariate * [0.0]
            for row in covariate_reference_table :
                if row['node_id'] == node_id :
                    covariate_id = row['covariate_id']
                    reference[covariate_id] = row['reference']
            child_covariate_reference[node_id] = reference
    #
    # tbl_name
    tbl_name = 'avgint'
    #
    # col_name
    col_name = [
        'integrand_id',
        'node_id',
        'subgroup_id',
        'weight_id',
        'age_lower',
        'age_upper',
        'time_lower',
        'time_upper',
    ]
    #
    # col_tyype
    col_type = [
        'integer',
        'integer',
        'integer',
        'integer',
        'real',
        'real',
        'real',
        'real',
    ]
    #
    # add covariates to col_name and col_type
    for covariate_id in range( n_covariate ) :
        col_name.append( 'x_' + str(covariate_id) )
        col_type.append( 'real' )
    #
    # add the smoothing grid columns to col_name and col_type
    col_name += [
        'c_mulcov_id', 'c_rate_id', 'c_node_id', 'c_age_id', 'c_time_id',
    ]
    col_type += 5 * ['integer']
    #
    # name_rate2integrand
    name_rate2integrand = {
        'iota':   'Sincidence',
        'rho':    'remission',
        'chi':    'mtexcess',
    }
    #
    # initialize row_list
    row_list = list()
    #
    # mulcov_id
    for mulcov_id in range( len( parent_tables['mulcov'] ) ) :
        #
        # mulcov_row
        mulcov_row = parent_tables['mulcov'][mulcov_id]
        #
        # group_smooth_id
        group_smooth_id = mulcov_row['group_smooth_id']
        if not group_smooth_id is None :
            #
            # integrand_id
            integrand_name  = 'mulcov_' + str(mulcov_id)
            integrand_table = parent_tables['integrand']
            integrand_id    = table_name2id(
                integrand_table, 'integrand_name', integrand_name
            )
            #
            # grid_row
            for grid_row in parent_tables['smooth_grid'] :
                if grid_row['smooth_id'] == group_smooth_id :
                    #
                    # age_id
                    age_id    = grid_row['age_id']
                    age_lower = parent_tables['age'][age_id]['age']
                    age_upper = age_lower
                    #
                    # time_id
                    time_id    = grid_row['time_id']
                    time_lower = parent_tables['time'][time_id]['time']
                    time_upper = time_lower
                    #
                    # row
                    rate_id     = None
                    node_id     = None
                    subgroup_id = 0
                    weight_id   = None
                    row = [
                        integrand_id,
                        node_id,
                        subgroup_id,
                        weight_id,
                        age_lower,
                        age_upper,
                        time_lower,
                        time_upper,
                    ]
                    row += n_covariate * [ None ]
                    row += [
                        mulcov_id,
                        rate_id,
                        node_id,
                        age_id,
                        time_id,
                    ]
                    #
                    # add to row_list
                    row_list.append( row )
    #
    # rate_name
    for rate_name in name_rate2integrand :
        #
        # rate_id
        rate_id = table_name2id(rate_table, 'rate_name', rate_name)
        #
        # parent_smooth_id
        parent_smooth_id = rate_table[rate_id]['parent_smooth_id']
        if not parent_smooth_id is None :
            #
            # integrand_id
            integrand_name  = name_rate2integrand[rate_name]
            integrand_table = parent_tables['integrand']
            integrand_id    = table_name2id(
                integrand_table, 'integrand_name', integrand_name
            )
            #
            # grid_row
            for grid_row in parent_tables['smooth_grid'] :
                if grid_row['smooth_id'] == parent_smooth_id :
                    #
                    # age_id
                    age_id    = grid_row['age_id']
                    age_lower = parent_tables['age'][age_id]['age']
                    age_upper = age_lower
                    #
                    # time_id
                    time_id    = grid_row['time_id']
                    time_lower = parent_tables['time'][time_id]['time']
                    time_upper = time_lower
                    #
                    # node_id
                    for node_id in child_covariate_reference :
                        #
                        # row
                        mulcov_id   = None
                        subgroup_id = 0
                        weight_id   = None
                        row = [
                            integrand_id,
                            node_id,
                            subgroup_id,
                            weight_id,
                            age_lower,
                            age_upper,
                            time_lower,
                            time_upper,
                        ]
                        row += child_covariate_reference[node_id]
                        row += [
                            mulcov_id,
                            rate_id,
                            node_id,
                            age_id,
                            time_id,
                        ]
                        #
                        # add to row_list
                        row_list.append( row )
    #
    # put new avgint table in parent_node_database
    new           = False
    connection    = dismod_at.create_connection(parent_node_database, new)
    command       = 'DROP TABLE IF EXISTS ' + tbl_name
    dismod_at.sql_command(connection, command)
    dismod_at.create_table(connection, tbl_name, col_name, col_type, row_list)
    connection.close()

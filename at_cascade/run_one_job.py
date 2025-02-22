# SPDX-License-Identifier: AGPL-3.0-or-later
# SPDX-FileCopyrightText: University of Washington <https://www.washington.edu>
# SPDX-FileContributor: 2021-23 Bradley M. Bell
# ----------------------------------------------------------------------------
'''
{xrst_begin run_one_job}
{xrst_spell
   dir
   obj
   var
}

Run One Job
###########

Syntax
******
{xrst_literal
   # BEGIN syntax
   # END syntax
}

Default Value
*************
The only argument that can be None is *trace_file_obj*.

job_table
*********
This is a :ref:`create_job_table@job_table` containing the jobs
necessary to fit the :ref:`glossary@fit_goal_set`.

run_job_id
**********
This is the :ref:`create_job_table@job_table@job_id`
for the job that is run.

all_node_database
*****************
is a python string specifying the location of the
:ref:`all_node_db-name`
relative to the current working directory.

node_table
**********
is a ``list`` of ``dict`` containing the node table for this cascade.

fit_integrand
*************
is a ``set`` of integrand_id values that occur in the data table; see
:ref:`get_fit_integrand-name`.

fit_type
********
is a ``str`` equal to 'both' or 'fixed' and specifies the type
of fit that dismod_at will do.

first_fit
*********
If *first_fit* is True, this is assumed to be an
:ref:`glossary@input_node_database`.
Otherwise, it is assumed that this
routine has previously been called with *first_fit* equal to True.

trace_file_obj
**************
If this argument is not None, it is a ``io.TextIOBase`` object
corresponding to a file that is opened for writing the tracing output
for this job.

fit_node_database
*****************
The :ref:`glossary@fit_node_database` for this fit is
*fit_node_dir*\ ``/dismod.db`` where *fit_node_dir*
is the :ref:`get_database_dir@database_dir` returned by
get_database_dir for the fit node and split_reference_id corresponding
to *run_job_id*.

Upon Input
==========
On input, *fit_node_database* is an :ref:`glossary@input_node_database`.

fit_var
=======
Upon return, the fit_var table correspond to the posterior
mean for the model variables for the fit_node.

sample
======
Upon return,
the sample table contains the corresponding samples from the posterior
distribution for the model variables for the fit_node.

log
===
If *fit_type* is 'both', the previous contents of the log are removed.
Upon return,
a summary of the operations preformed on dismod.db is added to the log table.

{xrst_end run_one_job}
'''
# ----------------------------------------------------------------------------
import io
import os
import time
import dismod_at
import at_cascade
# -----------------------------------------------------------------------------
def system_command(command, file_stdout) :
   if file_stdout is None :
      dismod_at.system_command_prc(
         command,
         print_command = True,
         return_stdout = False,
         return_stderr = False,
         file_stdout   = None,
         file_stderr   = None,
         write_command = False,
      )
   else :
      dismod_at.system_command_prc(
         command,
         print_command = False,
         return_stdout = False,
         return_stderr = False,
         file_stdout   = file_stdout,
         file_stderr   = None,
         write_command = True,
      )
# ----------------------------------------------------------------------------
# BEGIN syntax
# at_cascade.run_one_job
def run_one_job(
   job_table               ,
   run_job_id              ,
   all_node_database       ,
   node_table              ,
   fit_integrand           ,
   fit_type                ,
   first_fit               ,
   trace_file_obj    = None,
# )
) :
   assert type(job_table) == list
   assert type(run_job_id) == int
   assert type(all_node_database) == str
   assert type(node_table) == list
   assert type(fit_integrand) == set
   assert fit_type in [ 'both', 'fixed' ]
   assert type(first_fit) == bool
   # END syntax
   #
   # file_stdout
   if trace_file_obj is not None :
      assert isinstance(trace_file_obj, io.TextIOBase)
   file_stdout = trace_file_obj
   #
   # fit_node_id
   fit_node_id = job_table[run_job_id]['fit_node_id']
   #
   # fit_split_reference_id
   fit_split_reference_id = job_table[run_job_id]['split_reference_id']
   #
   # start_child_job_id
   start_child_job_id = job_table[run_job_id]['start_child_job_id']
   #
   # end_child_job_id
   end_child_job_id = job_table[run_job_id]['end_child_job_id']
   #
   # all_table
   connection  = dismod_at.create_connection(
      all_node_database, new = False, readonly = True
   )
   all_table = dict()
   for tbl_name in [
      'option_all',
      'split_reference',
      'node_split',
      'mulcov_freeze',
   ] :
      all_table[tbl_name] = dismod_at.get_table_dict(connection, tbl_name)
   connection.close()
   #
   # double_max_fit
   double_max_fit = False
   for row in all_table['mulcov_freeze'] :
      if fit_node_id == row['fit_node_id'] :
         if fit_split_reference_id == row['split_reference_id'] :
            double_max_fit = True
   #
   # option_all_dict
   option_all_dict = dict()
   for row in all_table['option_all'] :
      option_all_dict[ row['option_name']  ] = row['option_value']
   #
   # sample_method
   if 'sample_method' in option_all_dict :
      sample_method = option_all_dict['sample_method']
      if sample_method not in [ 'asymptotic', 'simulate' ] :
         msg = 'opton_all table: sample_method is not asymptotic or simulate'
         assert False, msg
   else :
      sample_method = 'asymptotic'
   #
   # refit_split
   if 'refit_split' in option_all_dict :
      refit_split = option_all_dict['refit_split']
      assert refit_split in [ 'true', 'false' ]
      refit_split = refit_split == 'true'
   else :
      refit_split = False
   #
   # result_dir
   result_dir = option_all_dict['result_dir']
   #
   # root_node_id
   name         = option_all_dict['root_node_name']
   root_node_id = at_cascade.table_name2id(node_table, 'node', name)
   #
   # root_split_reference_id
   if 'root_split_reference_name' not in option_all_dict :
      root_split_reference_id = None
      assert refit_split == False
   else :
      name = option_all_dict['root_split_reference_name']
      root_split_reference_id   = at_cascade.table_name2id(
         all_table['split_reference'], 'split_reference', name
      )
   #
   # balance_fit
   if 'balance_fit' not in option_all_dict :
      balance_fit = None
   else :
      balance_fit = option_all_dict['balance_fit']
      balance_fit = balance_fit.split()
      if 'max_fit' not in option_all_dict :
         msg  = 'balance_fit appears in option_all table '
         msg += 'but max_fit does not.'
         assert False, msg
      if len(balance_fit) != 3 :
         msg = 'option_all table: balance_fit is not a space separated '
         msg += 'list with three elements'
         assert False, msg
   #
   # perturb_optimization
   perturb_optimization = dict()
   for key in [ 'start', 'scale' ] :
      long_key = f'perturb_optimization_{key}'
      if long_key in option_all_dict :
         sigma = option_all_dict[long_key]
         if float(sigma) < 0.0 :
            msg = f'run_one_job: perturb_optimization_{key} = '
            msg += sigma
            msg += ' is less than zero'
            assert False, msg
         if float(sigma) > 0.0 :
            perturb_optimization[key] = sigma
   #
   # node_split_set
   node_split_set = set()
   for row in all_table['node_split'] :
      node_split_set.add( row['node_id'] )
   #
   # fit_node_database
   database_dir = at_cascade.get_database_dir(
      node_table              = node_table,
      split_reference_table   = all_table['split_reference'],
      node_split_set          = node_split_set,
      root_node_id            = root_node_id,
      root_split_reference_id = root_split_reference_id,
      fit_node_id             = fit_node_id ,
      fit_split_reference_id  = fit_split_reference_id,
   )
   fit_node_database = f'{result_dir}/{database_dir}/dismod.db'
   #
   # check fit_node_database
   parent_node_name = at_cascade.get_parent_node(fit_node_database)
   assert parent_node_name == node_table[fit_node_id]['node_name']
   #
   # connection
   connection = dismod_at.create_connection(
      fit_node_database, new = False, readonly = False
   )
   #
   # integrand_table
   root_node_database = option_all_dict['root_node_database']
   fit_or_root        = at_cascade.fit_or_root_class(
      fit_node_database, root_node_database
   )
   integrand_table = fit_or_root.get_table('integrand')
   fit_or_root.close()
   #
   # log table
   if first_fit :
      cmd = 'drop table if exists log'
      dismod_at.sql_command(connection, cmd)
      #
      # omega_constraint
      at_cascade.omega_constraint(all_node_database, fit_node_database)
      at_cascade.add_log_entry(connection, 'omega_constraint')
   #
   # init
   command = [ 'dismod_at', fit_node_database, 'init' ]
   system_command(command, file_stdout)
   #
   # max_fit
   if 'max_fit' in option_all_dict :
      max_fit = option_all_dict['max_fit']
      if double_max_fit :
         max_fit = str( 2 * int(max_fit) )
      for integrand_id in fit_integrand :
         integrand_name = integrand_table[integrand_id]['integrand_name']
         command = [
            'dismod_at', fit_node_database,
            'hold_out', integrand_name, max_fit
         ]
         if balance_fit is not None :
            command += balance_fit
         system_command(command, file_stdout)
   #
   # max_abs_effect
   if 'max_abs_effect' in option_all_dict:
      max_abs_effect = option_all_dict['max_abs_effect']
      command =[
         'dismod_at', fit_node_database, 'bnd_mulcov', max_abs_effect
      ]
      system_command(command, file_stdout)
   #
   # perturb_optimization
   for key in perturb_optimization :
      sigma = perturb_optimization[key]
      table = f'{key}_var'
      command = [
         'dismodat.py', fit_node_database, 'perturb', table, sigma
      ]
      system_command(command, file_stdout)
   #
   # fit
   command = [ 'dismod_at', fit_node_database, 'fit', fit_type ]
   system_command(command, file_stdout)
   #
   # number_simulate
   if 'number_sample' not in option_all_dict :
      number_simulate = '20'
   else :
      number_simulate = option_all_dict['number_sample']
   #
   # sample
   if sample_method == 'simulate' :
      if int( number_simulate ) > 20 :
         msg  = 'option_all table: number_sample > 20 and '
         msg += 'sample_method is simulate.'
         assert False, msg
      command = [
         'dismod_at', fit_node_database, 'set', 'truth_var', 'fit_var'
      ]
      system_command(command, file_stdout)
      command = [
         'dismod_at', fit_node_database, 'simulate', number_simulate
      ]
      system_command(command, file_stdout)
   command = [
      'dismod_at',
      fit_node_database,
      'sample',
      sample_method,
      fit_type,
      number_simulate
   ]
   system_command(command, file_stdout)
   #
   # avgint_parent_grid
   at_cascade.avgint_parent_grid(
      all_node_database = all_node_database ,
      fit_node_database = fit_node_database ,
      job_table         = job_table         ,
      fit_job_id        = run_job_id        ,
   )
   at_cascade.add_log_entry(connection, 'avgint_parent_grid')
   #
   # c_shift_predict_fit_var
   command = [ 'dismod_at', fit_node_database, 'predict', 'fit_var' ]
   system_command(command, file_stdout)
   at_cascade.move_table(connection, 'predict', 'c_shift_predict_fit_var')
   #
   # c_shift_predict_sample
   command = [ 'dismod_at', fit_node_database, 'predict', 'sample' ]
   system_command(command, file_stdout)
   at_cascade.move_table(connection, 'predict', 'c_shift_predict_sample')
   #
   # c_shift_avgint
   # is the table created by avgint_parent_grid
   at_cascade.move_table(connection, 'avgint', 'c_shift_avgint')
   #
   # shift_databases
   shift_databases = dict()
   for job_id in range(start_child_job_id, end_child_job_id) :
      #
      # shift_node_id
      shift_node_id = job_table[job_id]['fit_node_id']
      #
      # shift_split_reference_id
      shift_split_reference_id = job_table[job_id]['split_reference_id']
      #
      # shift_database_dir
      database_dir = at_cascade.get_database_dir(
         node_table              = node_table,
         split_reference_table   = all_table['split_reference'],
         node_split_set          = node_split_set,
         root_node_id            = root_node_id,
         root_split_reference_id = root_split_reference_id,
         fit_node_id             = shift_node_id ,
         fit_split_reference_id  = shift_split_reference_id,
      )
      shift_database_dir = f'{result_dir}/{database_dir}'
      if not os.path.exists(shift_database_dir) :
         os.makedirs(shift_database_dir)
      #
      # shift_node_database
      shift_node_database = f'{shift_database_dir}/dismod.db'
      #
      # skip_refit
      if refit_split :
         skip_refit = False
      else :
         skip_refit = fit_split_reference_id != shift_split_reference_id
      #
      # shift_name
      dir_list = shift_database_dir.split('/')
      if skip_refit :
         shift_name = dir_list[-2] + '/' + dir_list[-1]
      else :
         shift_name = dir_list[-1]
      #
      # shfit_databases
      shift_databases[shift_name] = shift_node_database
   #
   # create shifted databases
   at_cascade.create_shift_db(
      all_node_database,
      fit_node_database,
      shift_databases,
   )
   #
   # empty_avgint_table
   at_cascade.empty_avgint_table(connection)
   #
   # connection
   connection.close()

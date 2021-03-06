Getting Started
===============

Installing PADE
---------------

Pade is written in Python, and depends heavily on several Python
libraries, such as:

* jinja2
* matplotlib
* scipy
* numpy
* redis
* celery
* h5py
* flask
* Flask-WTF

PADE has been primarily tested on Ubuntu 12.04.1, so installing it on
similar Ubuntu systems should be easy. You can most likely install it
on other Linux distributions or Mac OS X, although OS X can be a bit
tricky.

On an Amazon EC2 Instance
^^^^^^^^^^^^^^^^^^^^^^^^^

Installing and running PADE on an Amazon EC2 instance is very straightforward. We recommend starting an instance based on the ``ami-3fec7956`` AMI. Then ssh to the instance, and run::

  wget https://raw.github.com/itmat/pade/master/ubuntu_dev_setup.sh -O - | bash

This will install git and several Python packages system-wide, create
a local Python environment using virtual env, install PADE's
dependencies into that environment, and link PADE's executable and
libraries into that environment. Then simply run::

  source padeenv/bin/activate

to activate the environment, and then you should be able to run
``pade``.

On Ubuntu
^^^^^^^^^

You should be able to use the above instructions for installing PADE
on an Amazon EC2 instance to install PADE on any Ubuntu machine,
however the ubuntu_dev_setup.sh script has been primarily tested on
fresh EC2 instances.

We recommend installing the following packages via apt-get::

  apt-get install git python-numpy python-scipy python-matplotlib python-h5py redis-server python-setuptools python-pip

Then install virtualenv via pip::

  pip install virtualenv

Create a virtualenv environment::

  virtualenv --system-site-packages padeenv 

Activate the environment::

  source padeenv/bin/activate

Obtain pade and install it into your newly active padeenv environment:

  git clone https://github.com/itmat/pade.git
  cd pade
  python setup.py develop

Then you should be able to run ``pade``.

On Mac OS X
^^^^^^^^^^^

Installing numpy, scipy and h5py on a Mac can be difficult. The
easiest way to get up and running may be to use a Python distribution
that has scientific computing libraries pre-packaged with it. You
should be able to use the *Enthought Python Distribution*, available
here: http://www.enthought.com/products/epd.php. After you install
EPD, *please make sure that the python you're using when you run
``python`` is actually the one from EPD*. Then you should be able to
install PADE by running ``sudo python setup.py install`` from within
the PADE source directory.

   
Running a sample job
--------------------

We recommend running a small job using the sample data provided in the
pade distribution in order to familiarize yourself with the program
before attempting to run it on your own data.

The pade distribution includes a couple very small sample data files,
in the ``sample_data`` directory.

Input files
^^^^^^^^^^^

The input to any pade job is a tab-delimited file. The file must
contain a header row, plus one row for each feature. There should be
one column that contains a unique identifier for the features (for
example a gene id). Then each of the samples should have their
expression values for each feature in its own column. So for example
if you 2 conditions, each with 4 replicates, and 1000 features, you
would have a tab file with a header row plus 1000 data rows, with 9
columns (1 for the feature id and 8 for the expression data).

The names of the columns do not matter, except that each column's name
must be unique. 

Creating the schema
^^^^^^^^^^^^^^^^^^^

The first step of any pade job is to run ``pade setup`` on the input
file, which will create a "schema" file that you will then edit to
describe the grouping of columns in the input file. You run ``pade
setup`` and provide the input file on the command line, plus a
``--factor`` argument for each factor that you want to use to group
the columns. For example, suppose say we are trying to find genes that
are differentially expressed due to some treatment, and we want to
treat gender as a "nuisance" variables. So we have two factors:
"treated" and "gender". We would setup the job as follows::

  pade setup --factor gender --factor treated sample_data/sample_data_4_class.txt -o schema.yaml

This will read in the input file and create a skeleton "schema" file
based on it, in schema.yaml. We then need to edit this file to list
the values available for each of the two factors, and to assign those
factor values to each of the sample column names.

First, in the very top section of the schema.yaml file,
list the valid values for the factors. Change it to look like this::

  factors:
  - name: treated
    values: [no, yes]
  - name: gender
    values: [male, female]

Next, look for the section called ``sample_factor_mapping``. This
lists each sample column in the input file, like this::

  sample_factor_mapping:
    c0r1:
      gender: null
      treated: null
    c0r2:
      gender: null
      treated: null
  ...

You will need to edit the settings for each column to indicate the
gender and whether or not it was treated::

  sample_factor_mapping:
    c0r1:
      gender: male
      treated: no
    c0r2:
      gender: male
      treated: no
  ...
    c3r4:
      gender: female
      treated: yes

Running the analysis
^^^^^^^^^^^^^^^^^^^^

Once you have created the schema file, you are ready to run the
analysis, using ``pade run``. You'll need to specify a couple options,
most importantly ``--condition`` and ``--schema``.

Condition and Block
"""""""""""""""""""

``--condition`` allows you to specify the factor the represents the
experimental condition that you want to test for differential
effects. ``--block`` allows you to optionally specify "nuisance
variables". If you specify one or more blocking factors, permutations
will be restricted by those factors, so that for every permutation,
the labelling of those blocking factors does not change for any sample.

For example, if you have factors "gender" and "treated", and you want
to test for differential effects due to treatment within each value of
gender, you would run::

  --condition treated --block gender

Default settings
""""""""""""""""

The simplest Pade job for our 4-class sample input would be something like::

  pade run --condition treated --block gender --schema schema.yaml sample_data/sample_data_4_class.txt -o results.pade

This should take less than a minute. Note that you need to provide the
input file on the command line.

Interesting options
"""""""""""""""""""

By default, Pade computes the false discovery rate by using a
permutation test with the f-statistic. You can change the method used
for computing the false discovery rate with the "--sample-method" and
"--sample-from" options. This allows you to do bootstrapping instead
of permutation, and to sample from either the raw data values or from
the residuals of the data values (from the means predicted by the
reduced model). Please see ``pade run -h`` for more details.

You can change the number of samples used for bootstrapping (or the
permutation test) with ``--num-samples`` or ``-R``.

By default Pade prints very little output; just a report at the end
showing the distribution of the confidence levels. You can make it be
more verbose with the ``--verbose`` or ``-v`` option. It will print
even more debugging-level output if you give it ``--debug`` or ``-d``.

You can change the statistic pade uses with the '--stat'
option. Currently we support the following statistics:

f_test:
  F-test. Can only be used where each group has two or more samples.

one_sample_t_test:
  Single sample t-test, for paired input only.

means_ratio:
  Ratio of means. Can only be used when there are two conditions. Can
  be used with or without blocking. Works with paired data also.

glm: A generalized linear model. If you specify this statistic, you
  must also specify a distribution family using the '--glm-family'
  option. Please see ``pade help run`` for a list of the supported
  families.

Viewing reports
^^^^^^^^^^^^^^^

When you run ``pade run``, it will store the results of the analysis
in a binary file (you specify the path with the --output option).
Once that step is done, you can generate a tab-delimited text file
containing the results, or launch a small web server to display the
results in HTML format. To generate the text file output, run::

  pade report results.pade

To start the HTML viewer, run::

  pade view results1.pade results2.pade ...

It will take a few seconds to start up, and should open a web browser
pointing to the results.


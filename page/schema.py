"""Describes a PaGE input file."""

import numpy as np
import textwrap
import yaml
import logging
from collections import OrderedDict
from itertools import product

def write_yaml_block_comment(fh, comment):
    result = ""
    for line in comment.splitlines():
        result += textwrap.fill(line, initial_indent = "# ", subsequent_indent="# ")
        result += "\n"
    fh.write(unicode(result))



class Schema(object):

    """Describes a PaGE input file.

    """

    def __init__(self, 
                 is_feature_id=None,
                 is_sample=None,
                 column_names=None):
        """Construct a Schema. 

  column_names  - a list of strings, giving names for the columns.

  is_feature_id - a list of booleans of the same length as
                  column_names. is_feature_id[i] indicates if the ith
                  column contains feature ids (e.g. gene names).

  is_sample     - a list of booleans of the same length as
                  column_names. is_sample[i] indicates if the ith
                  column contains a sample.

Any columns for which is_feature_id is true will be treated as feature
ids, and any for which is_sample is true will be assumed to contain
intensity values. No column should have both is_feature_id and
is_sample set to true. Any columns where both is_feature_id and
is_sample are false will simply be ignored.

  """

        if column_names is None:
            raise Exception("I need column names")
        else:
            column_names = np.array(column_names)

        self.factors = OrderedDict()


        self.sample_to_factor_values = OrderedDict()
        self.is_feature_id = np.array(is_feature_id, dtype=bool)
        self.is_sample     = np.array(is_sample,     dtype=bool)
        self.column_names  = column_names
        self.sample_to_column  = []
        self.sample_name_index = {}

        for i, name in enumerate(column_names):
            if self.is_sample[i]:
                self.sample_name_index[name] = len(self.sample_name_index)
                self.sample_to_factor_values[name] = {}


    @property
    def factor_names(self):
        """List of the factor names for this schema.

        The factors are given in the same order they appear in the
        schema file.

        """
        return self.factors.keys()

    def factor_values(self, factor):

        """Return the list of valid values for the given factor.

        The result is sorted according to the order the values are
        given in the schema file.

        """
        return self.factors[factor]

    @property
    def sample_column_names(self):
        """List of the names of columns that contain intensities."""

        return self.column_names[self.is_sample]

    @property
    def feature_id_column_names(self):
        """Name of column that contains feature ids."""
        return self.column_names[self.is_feature_id]

    def _check_factors(self, factors):

        if factors is None:
            factors = self.factor_names

        factors = list(factors)
        correct_order = [f for f in self.factors if f in factors]
        
        if factors != correct_order:
            raise Exception("Please request factors in correct order: "
                            + str(correct_order) + ", not " + str(factors))

        return factors

    def factor_combinations(self, factors=None):
        """Return list of possible combinations of values for given factors.

        Each item of the returned list is a tuple of values, where
        value i is one of the values defined in the schema for factor i.
        """

        factors = self._check_factors(factors)
        values = [self.factor_values(f) for f in factors]
        return list(product(*values))

    def baseline_value(self, factor):
        """Return the first value listed in the schema for given factor."""
        return self.factors[factor][0]

    def baseline_values(self, factors):
        """Return first value defined for each of the factors given."""        
        return [self.baseline_value(f) for f in factors]


    def has_baseline(self, assignment):
        """Return true if any of the variables is assigned to their baseline.

        assignment must be a dictionary mapping factors in this schema to
        a valid value for that factor. Returns true if any of those mappings
        is to the 'baseline' value for that factor.

        """
        for factor, value in assignment.items():
            if value == self.baseline_value(factor):
                return True
        return False

    def sample_matches_assignments(self, sample_name, assignments):
        """Return true if the sample with the given has the given assignments.

        sample_name - must be the name of one of the samples in this schema.
        assignments - must be a mapping from factor name to value

        """
        for f, v in assignments.items():
            if self.get_factor(sample_name, f) != v:
                return False
        return True

    def samples_with_assignments(self, assignments):
        """Return list of sample names that have the given assignments.

        assignments - must be a mapping from factor name to value

        """
        matches = lambda name: self.sample_matches_assignments(name, assignments)
        return filter(matches, self.sample_column_names)

    def indexes_with_assignments(self, assignments):
        """Return list of indexes that have the given assignments.
        
        assignments - must be a mapping from factor name to value

        """
        samples = self.samples_with_assignments(assignments)
        indexes = [self.sample_num(s) for s in samples]
        return indexes

    def possible_assignments(self, factors=None):
        """Return a list of all possible mappings from factor name to value.

        Optionally provide the factors argument to limit combinations
        to those factors.

        """
        factors = self._check_factors(factors)
        return [
            OrderedDict(zip(factors, values))
            for values in self.factor_combinations(factors)]

    def add_factor(self, name, values=[]):
        """Add a factor with the given name and values."""
        self.factors[name] = values
        for sample in self.sample_to_factor_values:
            self.sample_to_factor_values[sample][name] = None

    @classmethod
    def load(cls, stream):
        """Load a schema from the specified stream.

        The stream can be any type accepted by yaml.load, and must
        represent a YAML document in the format produced by
        Schema.dump.

        """
        doc = yaml.load(stream)

        col_names = doc['headers']

        # Build the arrays of column names, feature id booleans, and
        # sample booleans
        feature_id_cols = set(doc['feature_id_columns'])

        is_feature_id = [c in feature_id_cols for c in col_names]
        is_sample     = [c in doc['sample_factor_mapping'] for c in col_names]

        schema = Schema(
            column_names=col_names,
            is_feature_id=is_feature_id,
            is_sample=is_sample)

        # Now add all the factors and their types
        factors = doc['factors']
        for factor in factors:
            schema.add_factor(factor['name'], factor['values'])

        for sample, attrs in doc['sample_factor_mapping'].iteritems():
            for name, value in attrs.iteritems():
                schema.set_factor(sample, name, value)

        return schema
    
    def save(self, out):
        """Save the schema to the specified file."""
        logging.info("Saving schema to " + out.name)

        # Need to convert column names to strings, from whatever numpy
        # type they're stored as.
        names = [str(name) for name in self.column_names]

        sample_cols     = {}
        feature_id_cols = []

        for i, name in enumerate(names):

            if self.is_feature_id[i]:
                feature_id_cols.append(name)

            elif self.is_sample[i]:
                

                sample_cols[name] = {}
                for factor in self.factors:
                    if factor in self.sample_to_factor_values[name]:
                        value = self.get_factor(name, factor)
                        sample_cols[name][factor] = value

        factors = []
        for name, values in self.factors.items():
            factors.append({ "name" : name, "values" : values })

        doc = {
            'headers'               : names,
            "factors"               : factors,
            "feature_id_columns"    : feature_id_cols,
            "sample_factor_mapping" : sample_cols,
            }

        data = yaml.dump(doc, default_flow_style=False, encoding=None)

        for line in data.splitlines():
            if (line == "factors:"):
                write_yaml_block_comment(out, """This lists all the factors defined for this file.
""")

            elif (line == "feature_id_columns:"):
                out.write(unicode("\n"))
                write_yaml_block_comment(out, """This lists all of the columns that contain feature IDs (for example gene ids).""")

            elif (line == "headers:"):
                out.write(unicode("\n"))
                write_yaml_block_comment(out, """These are the headers in the input file. YOU MUST NOT CHANGE THESE!""")

            elif (line == "sample_factor_mapping:"):
                out.write(unicode("\n"))
                write_yaml_block_comment(out, """This sets all of the factors for all columns that represent samples. You should fill out this section to set each factor for each sample. For example, if you had a sample called sample1 that recieved some kind of treatment, and one called sample2 that did not, you might have:

sample_factor_mapping:
  sample1:
    treated: yes
  sample2:
    treated: no

""")

            out.write(unicode(line) + "\n")


    def set_factor(self, sample_name, factor, value):
        """Set a factor for a sample, identified by sample name."""
        allowed = self.factor_values(factor)
        if value not in allowed:
            raise Exception("""\
                Value {value} is not allowed for factor {factor};
                allowable values are {allowed}.
                """.format(value=value, factor=factor, allowed=allowed))

        self.sample_to_factor_values[sample_name][factor] = value

    def get_factor(self, sample_name, factor):
        """Get an factor for a sample, identified by sample
        name."""

        return self.sample_to_factor_values[sample_name][factor]


    def sample_num(self, sample_name):
        """Return the sample number for sample with the given
        name. The sample number is the index into the table for the
        sample."""

        return self.sample_name_index[sample_name]

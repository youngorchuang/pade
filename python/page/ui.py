import core
import re
import argparse
from textwrap import fill
from schema import Schema
from core import Config
import cmd

class AttributePrompt(cmd.Cmd):

    def __init__(self, schema):
        cmd.Cmd.__init__(self)
        self.schema = schema

    def do_add(self, line):
        """Add an attribute, optionally with a type.

Usage:

  add ATTR [TYPE]

If type is supplied, it must be a valid numpy dtype, like S100, float,
or int.

"""

        tokens = line.split()
        type_ = "S100"

        if len(tokens) > 1:
            type_ = tokens[1]
            
        self.schema.add_attribute(tokens[0], type_)

    def do_remove(self, line):
        """Remove an attribute.

Usage:

  remove ATTR
"""
        schema.drop_attribute(line)

    def do_show(self, line):
        """Show the attributes that are currently defined."""

        print "\nAttributes are " + str(self.schema.attributes) + "\n"


    def do_quit(self, line):
        """Stop editing the schema."""
        return True

    def complete_set(self, text, line, begidx, endidx):
        values = self.schema.sample_column_names()
        return [v for v in values if v.startswith(text)]

    def do_set(self, line):
        tokens = line.split()

        settings = {}
        columns  = []

        for token in tokens:
            parts = token.split('=')
            if len(parts) == 2:
                settings[parts[0]] = parts[1]
            else:
                columns.append(parts[0])

        print "I would set " + str(settings) + " for columns " + str(columns)
        for factor in settings:
            value = settings[factor]
            print "Setting {0} to {1} for samples {2}".format(
                factor, value, str(columns))
            for column in columns:
                self.schema.set_attribute(column, factor, value)


def do_setup(args):
    """Ask the user for the list of factors, the values for each
    factor, and mapping from column name to factor values. Also
    establish whether the input file has a header line and a feature
    id column.
    """

    print "Here I am"
    header_line = args.infile.next().rstrip()
    headers = header_line.split("\t")

    is_feature_id = [i == 0 for i in range(len(headers))]
    is_sample     = [i != 0 for i in range(len(headers))]

    print fill("""
I am assuming that the input file is tab-delimited, with a header
line. I am also assuming that the first column ({0}) contains feature
identifiers, and that the rest of the columns ({1}) contain expression
levels. In a future release, we will be more flexible about input
formats. In the meantime, if this assumption is not true, you will
need to reformat your input file.
""".format(headers[0],
           ", ".join(headers[1:])))

    print ""

    schema = Schema(
        is_feature_id=is_feature_id,
        is_sample=is_sample,
        column_names=headers)

    prompt = AttributePrompt(schema)
    prompt.prompt = "attributes: "
    prompt.cmdloop("Enter a space-delimited list of attributes (factors)")

    with open(args.schema, 'w') as out:
        schema.save(out)

def do_run(args):
    config = validate_args(args)
    schema = Schema.load(args.schema)

    if len(schema.attribute_names) > 1:
        raise UsageException("I currently only support schemas with one attribute")
    
    groups = schema.sample_groups(schema.attribute_names[0])
    
    (data, row_ids) = core.load_input(config.infile)
    conditions = groups.values()

    alphas = core.find_default_alpha(data, conditions)
    core.do_confidences_by_cutoff(data, conditions, alphas, config.num_bins)

def validate_args(args):
    """Validate command line args and prompt user for any missing args.
    
    args is a Namespace object as returned by get_arguments(). Checks
    to make sure there are no conflicting arguments. Prompts user for
    values of any missing arguments. Returns a Config object
    representing the configuration of the job, taking into account
    both the command-line options and the values we had to prompt the
    user for.
    """

    c = Config(args)

    pos_int_re = re.compile("\d+")

    if 'channels' in args:
        if args.channels == 1 and 'design' in args:
            raise Exception("Error: if the number of channels is 1, do not speicfy the design type")
    elif 'design' in args:
        c.channels = 2

    while c.channels is None:
        s = raw_input("Are the arrays 1-channel or 2-channel arrays? (Enter 1 or 2): ")
        if pos_int_re.match(s) is not None:
            channels = int(s)

            if channels == 1 or channels == 2:
                c.channels = channels

    return c



def show_banner():
    """Print the PaGE banner.
    
    """

    print """
------------------------------------------------------------------------------

                       Welcome to PaGE {version}
                   Microarray and RNA-Seq analysis tool

------------------------------------------------------------------------------

For help, please use {script} --help or {script} -h
""".format(version=core.__version__,
           script=__file__)



def get_arguments():
    """Parse the command line options and return an argparse args
    object."""

    uberparser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    subparsers = uberparser.add_subparsers()

    setup_parser = subparsers.add_parser('setup')
    setup_parser.add_argument(
        'infile',
        help="""Name of input file""",
        default=argparse.SUPPRESS,
        type=file)
    setup_parser.add_argument(
        'schema',
        help="""Location to write schema file""",
        default=argparse.SUPPRESS)
    setup_parser.set_defaults(func=do_setup)
    
    check_parser = subparsers.add_parser("check")
    check_parser.add_argument(
        'infile',
        help="""Name of input file""",
        default=argparse.SUPPRESS,
        type=file)
    check_parser.add_argument(
        'schema',
        help="""Location to read schema file from""",
        default=argparse.SUPPRESS)

    parser = subparsers.add_parser('run')
    parser.set_defaults(func=do_run)
    file_locations = parser.add_argument_group("File locations")

    file_locations.add_argument(
        'infile',
        help="""Name of the input file containing the table of
        data. Must conform to the format in the README file.""",
        default=argparse.SUPPRESS,
        type=file)

    file_locations.add_argument(
        'schema',
        help="""Path to the schema describing the input file""",
        type=file)

    file_locations.add_argument(
        '--outfile',
        help="""Name of the output file. If not specified outfile name will be
        derived from the infile name.""",
        default=argparse.SUPPRESS,
        type=file)

    file_locations.add_argument(
        "--id2info",
        help="""Name of the file containing a mapping of gene id's to
        names or descriptions.""",
        default=argparse.SUPPRESS,
        type=file)

    file_locations.add_argument(
        "--id2url",  
        help="""Name of the file containing a mapping of gene id's to urls.""",
        default=argparse.SUPPRESS,
        type=file)

    file_locations.add_argument(
        "--id-filter-file", 

        help="""If you just want to run the algorithm on a subset of
        the genes in your data file, you can put the id's for those
        genes in a file, one per line, and specify that file with
        this option.""",
        default=argparse.SUPPRESS,
        type=file)

    output_options = parser.add_argument_group("Output options")

    output_options.add_argument(
            "--output-gene-confidence-list",

            help="""Set this to output a tab delimited file that maps
            every gene to its confidence of differential expression.
            For each comparison gives separate lists for up and down
            regulation. """,
            default=argparse.SUPPRESS,
            type=file)

    output_options.add_argument(
            "--output-gene-confidence-list-combined",

            help="""Set this to output a tab delimited file that maps
            every gene to its confidence of differential expression.
            For each comparison gives one list with up and down
            regulation combined. """,
            default=argparse.SUPPRESS,
            type=file)

    output_options.add_argument(
            "--output-text",
            help="""Set this to output the results also in text format. """,
            default=argparse.SUPPRESS,
            action='store_true')

    output_options.add_argument(
            "--note",
            default=argparse.SUPPRESS,
            help="""A string that will be included at the top of the
            output file.""")

    output_options.add_argument(
            "--aux-page-size", 
            type=int,
            default=500,
            help="""A whole number greater than zero.  This specifies
            the minimum number of tags there can be in one pattern
            before the results for that pattern are written to an
            auxiliary page (this keeps the main results page from
            getting too large).""")

    design = parser.add_argument_group(
        "Study design and nature of the input data")

    design.add_argument(
        "--num-bins",
        type=int,
        default=1000,        
        help="""The number of bins to use in granularizing the
        statistic over its range. This is set to a default of 1000 and
        you probably shouldn't need to change it.""")

    design.add_argument(
        "--channels",
        type=int,
        default=argparse.SUPPRESS,        
        choices=[1,2],
        help="""Is your data one or two channels?  (note: Affymetrix
        is considered one channel).""")

    design.add_argument(
        "--design", 
        default=argparse.SUPPRESS,
        choices=['d', 'r'],
        help="""For two channel data, either set this to "r" for
        "reference" design or "d" for "direct comparisons"
        (see the documentation for more  information on this
        setting). """)

    logged = design.add_mutually_exclusive_group()

    logged.add_argument(
        "--data-is-logged", 
        default=argparse.SUPPRESS,
        action='store_true',
        dest='data_is_logged',
        help="Use this option if your data has already been log transformed.")

    logged.add_argument(
        """--data-not-logged""",
        action='store_const',
        dest='data_is_logged',
        const=False,
        default=argparse.SUPPRESS,
        help="Use this option if your data has not been log transformed. ")

    paired = design.add_mutually_exclusive_group()

    paired.add_argument(
        "--paired", 
        action='store_const',
        dest='paired',
        const=True,
        default=argparse.SUPPRESS,
        help="The data is paired.")

    paired.add_argument(
        "--unpaired", 
        action='store_const',
        dest='paired',
        const=False,
        default=argparse.SUPPRESS,
        help="The data is not paired.")

    design.add_argument(
        "--missing-value", 
        default=argparse.SUPPRESS,
        help="""If you have missing values designated by a string
        (such as \"NA\"), specify  that string with this option.  You
        can either put quotes around the string  or not, it doesn't
        matter as long as the string has no spaces."""
)

    stats = parser.add_argument_group('Statistics and parameter settings')

    stats.add_argument(
        "--level-confidence",
        type=float,
        default=argparse.SUPPRESS,
        help="""A number between 0 and 1. Generate the levels with
        this confidence. See the README file for more information on
        this parameter. This can be set separately for each group
        using --level-confidence-list (see below).  NOTE: This
        parameter can be set at the end of the run after the program
        has displayed a summary breakdown of how many genes are found
        with what confidence. To do this either set the command line
        option to "L" (for "later"), or do not specify this command
        line option and enter "L" when the program prompts for the
        level confidence.""")

    stats.add_argument(
        "--level-confidence-list",
        default=argparse.SUPPRESS,
        help="""Comma-separated list of confidences. If there are more
        than two conditions (or more than one direct comparision),
        each position in the pattern can have its own confidence
        specified by this list. E.g. if there are 4 conditions, the
        list might be .8,.7,.9 (note four conditions gives patterns of
        length 3)""")

    stats.add_argument(
        "--min-presence",
        default=argparse.SUPPRESS,
        help="""A positive integer specifying the minimum number of
        values a tag should  have in each condition in order to not
        be discarded.  This can be set  separately for each condition
        using --min-presence-list """)

    stats.add_argument(
        "--min-presence-list",
        default=argparse.SUPPRESS,
        help="""Comma-separated list of positive integers, one for
        each condition,  specifying the minimum number of values a
        tag should have, for each  condition, in order not to be
        discarded.  E.g. if there are three  conditions, the list
        might be 4,6,3 """)

    use_logged = design.add_mutually_exclusive_group()

    use_logged.add_argument(
        "--use-logged-data",
        default=argparse.SUPPRESS,
        action='store_true',
        help="""Use this option to run the algorithm on the logged
        data (you can only  use this option if using the t-statistic
        as statistic).  Logging the  data usually give better
        results, but there is no rule.  Sometimes  different genes
        can be picked up either way.  It is generally best,  if using
        the t-statistic, to go with the logged data.  You might try 
        both ways and see if it makes much difference.  Both ways give
        valid  results, what can be effected is the power. """)

    use_logged.add_argument(
        "--use-unlogged-data",
        default=argparse.SUPPRESS,
        action='store_true',
        help="""Use this option to run the algorithm on the unlogged
        data.  (See  --use-loggged-data option above for more
        information.) """)

    the_stat = stats.add_mutually_exclusive_group()

    the_stat.add_argument(
        "--tstat",
        action='store_true',
        default=argparse.SUPPRESS,
        help="Use the t-statistic as statistic. ")

    the_stat.add_argument(
        "--means",
        action='store_true',
        default=argparse.SUPPRESS,
        help="Use the ratio of the means of the two groups as statistic. ")

    stats.add_argument(
        "--tstat-tuning-parameter",
        default=argparse.SUPPRESS,
        help="""The value of the t-statistic tuning
        parameter.  This is set to  a default value determined
        separately for each pattern position, but can be  set by hand
        using this command.  See the documentation for more 
        information on this parameter. """)

    stats.add_argument(
        "--shift",
        default=argparse.SUPPRESS,
        help="""A real number greater than zero.  This number will be
        added to all intensities (of the unlogged data).  See the
        documentation for more on why you might use this parameter.""")

    try:
        return uberparser.parse_args()
    except IOError as e:
        print e
        print ""
        exit(1)


def main():
    """Run PaGE."""
    show_banner()
    args = get_arguments()
    args.func(args)

if __name__ == '__main__':
    main()

"""Low-level statistical methods.

This module should be general-purpose, and not have any dependencies
on the data model used in Pade or the workflow. The idea is that we
may use these functions outside of the standard Pade workflow.

"""

import numbers
import numpy as np
import numpy.ma as ma
import scipy.stats

import collections
from itertools import combinations, product
from pade.performance import profiling, profiled

from pade.common import *
from scipy.misc import comb

class UnsupportedLayoutException(Exception):
    """Thrown when a statistic is used with a layout that it can't support."""
    pass

class InvalidLayoutException(Exception):
    """Thrown when a layout is supplied that is invalid in some way."""

def apply_layout(data, layout):
    """Splits data into groups based on layout.

    1d data:
    
    >>> data = np.array([9, 8, 7, 6])
    >>> layout = [ [0, 1], [2, 3] ]
    >>> apply_layout(data, layout) # doctest: +NORMALIZE_WHITESPACE
    [array([9, 8]), array([7, 6])]

    2d data:
    
    >>> data = np.array([[9, 8, 7, 6], [5, 4, 3, 2]])
    >>> layout = [ [0, 1], [2, 3] ]
    >>> apply_layout(data, layout) # doctest: +NORMALIZE_WHITESPACE
    [array([[9, 8], [5, 4]]), array([[7, 6], [3, 2]])]

    """
    return [ data[..., list(idxs)] for idxs in layout]

def layout_is_paired(layout):
    """Returns true of the layout appears to be 'paired'.

    A paired layout is one where each group contains two values.

    :param layout:
       A :term:`layout`      

    :return:
      Boolean indicating if layout appears to be paired.

    """
    for grp in layout:
        if len(grp) != 2:
            return False
    return True

def group_means(data, layout):
    """Get the means for each group defined by layout.

    Groups data according to the given layout and returns a new
    ndarray with the same number of dimensions as data, but with the
    last dimension replaced by the means according to the specified
    grouping.
    
    One dimensional input:

    >>> group_means(np.array([-1, -3, 4, 6]), [[0, 1], [2, 3]])
    array([-2.,  5.])

    Two dimensional input:

    >>> data = np.array([[-1, -3, 4, 6], [10, 12, 30, 40]])
    >>> layout = [[0, 1], [2, 3]]
    >>> group_means(data, layout) # doctest: +NORMALIZE_WHITESPACE
    array([[ -2.,  5.],
           [ 11., 35.]])

    :param data: An ndarray. Any number of dimensions is allowed.

    :param layout: A :term:`layout` describing the data.

    :return: An ndarray giving the means for each group obtained by
      applying the given layout to the given data.

    """
    # We'll take the mean of the last axis of each group, so change
    # the shape of the array to collapse the last axis down to one
    # item per group.
    shape = np.shape(data)[:-1] + (len(layout),)
    res = np.zeros(shape)

    for i, group in enumerate(apply_layout(data, layout)):
        res[..., i] = np.mean(group, axis=-1)

    return res

def residuals(data, layout):
    """Return the residuals for the given data and layout.

    >>> residuals(np.array([1, 2, 3, 6], float), [[0, 1], [2, 3]])
    array([-0.5,  0.5, -1.5,  1.5])

    :param data: An ndarray. Any number of dimensions is allowed.

    :param layout: A :term:`layout` describing the data.

    :return: The residuals obtained by subtracting the means of the
    groups defined by the layout from the values in data.

    """
    means = group_means(data, layout)
    diffs = np.zeros_like(data)
    for i, idxs in enumerate(layout):
        these_data  = data[..., idxs]
        these_means = means[..., i].reshape(np.shape(these_data)[:-1] + (1,))
        diffs[..., idxs] = these_data - these_means
    return diffs

def group_rss(data, layout):

    """Return the residual sum of squares for the data with the layout.

    >>> group_rss(np.array([1, 2, 3, 6], float), [[0, 1], [2, 3]])
    5.0

    """
    r = residuals(data, layout)
    rs = r ** 2
    return np.sum(rs, axis=-1)


def rss(data):
    """Return a tuple of the mean and residual sum of squares.

    :param data:
      An n-dimensional array.

    :return:
      The means and residual sum of squares over the last axis.

    """
    y   = np.mean(data, axis=-1).reshape(np.shape(data)[:-1] + (1,))
    return double_sum((data  - y)  ** 2)

class Ftest:

    name = "F-test"

    """Computes the F-test.

    Some sample data

    >>> a = np.array([1., 2.,  3., 6.])
    >>> b = np.array([2., 1.,  1., 1.])
    >>> c = np.array([3., 1., 10., 4.])

    The full layout has the first two columns in one group and the
    second two in another. The reduced layout has all columns in one
    group.

    >>> full_layout = [[0, 1], [2, 3]]
    >>> reduced_layout = [[0, 1, 2, 3]]
    
    Construct one ftest based on our layouts

    >>> ftest = Ftest(full_layout, reduced_layout)
    
    Test one row

    >>> round(ftest(a), 1)
    3.6

    Test multiple rows at once

    >>> data = np.array([a, b, c])
    >>> ftest(data)
    array([ 3.6,  1. ,  2.5])

    """
    def __init__(self, layout_full, layout_reduced, alphas=None):

        pair_lens = [len(pair) for pair in layout_full]
        if not all([n > 1 for n in pair_lens]):
            raise UnsupportedLayoutException(
                """I can't use an FTest with the specified full model, because some of the groups contain only one sample.""")

        self.layout_full = layout_full
        self.layout_reduced = layout_reduced
        self.alphas = alphas

    def __call__(self, data):
        # Degrees of freedom
        p_red  = len(self.layout_reduced)
        p_full = len(self.layout_full)
        n      = sum(map(len, self.layout_reduced))

        # Means and residual sum of squares for the reduced and full
        # model
        rss_full = group_rss(data, self.layout_full)
        rss_red  = group_rss(data, self.layout_reduced)

        numer = (rss_red - rss_full) / (p_full - p_red)
        denom = rss_full / (n - p_full)

        if self.alphas is not None:
            denom = np.array([denom + x for x in self.alphas])
        return numer / denom



def random_indexes(layout, R):
    """Generates R samplings of indexes based on the given layout.

    >>> indexes = random_indexes([[0, 1], [2, 3]], 10)
    >>> np.shape(indexes)
    (10, 4)

    """
    layout = [ np.array(grp, int) for grp in layout ]
    n = sum([ len(grp) for grp in layout ])
    res = np.zeros((R, n), int)
    
    for i in range(R):
        p = 0
        q = 0
        for j, grp in enumerate(layout):
            nj = len(grp)
            q  = p + nj
            res[i, p : q] = grp[np.random.random_integers(0, nj - 1, nj)]
            p = q

    return res

Accumulator = collections.namedtuple(
    'Accumulator',
    ['initializer', 'reduce_fn', 'finalize_fn'])


DEFAULT_ACCUMULATOR = Accumulator(
    [],
    lambda res, val: res + [ val ],
    lambda x: np.array(x))

def _binning_accumulator(bins, num_samples):
    initializer = np.zeros(cumulative_hist_shape(bins))

    def reduce_fn(res, val):
        hist = cumulative_hist(val, bins)
        return res + hist
    
    def finalize_fn(res):
        return res / num_samples

    return Accumulator(initializer, reduce_fn, finalize_fn)

@profiled
def bootstrap(data,
              stat_fn,
              R=1000,
              sample_layout=None,
              indexes=None,
              residuals=None,
              bins=None):
    """Run bootstrapping.

    This function should most likely accept data of varying
    dimensionality, but this documentation uses two dimensional data
    as an example.

    :param data:
      An (M x N) array.

    :param stat_fn:
      A callable that accepts an array of shape (M x N) and returns statistics of shape (M).

    :param R:
      The number of bootstrapping samples to generate, if *indexes* is
      not supplied.

    :param sample_layout:
      If *indexes* is not supplied, sample_layout can be used to
      specify a :layout: to restrict the randomized sampling. If
      supplied, it must be a list of lists which divides the N indexes
      of the columns of *data* up into groups.

    :param indexes:
      If supplied, it must be an (M x N) table of indexes into the
      data, which we will use to extract data points for
      bootstrapping. If not supplied, *R* indexes will be generated
      randomly, optionally restricted by the :layout: given in
      *sample_layout*.

    :param residuals:
      You can use this in conjunction with the *data* parameter to
      construct artificial samples. If this is supplied, it must be
      the same shape as *data*. Then *data* should be the values
      predicted by the model, and *residuals* should be the residuals
      representing the predicted values subtracted from the original
      data. The samples will be constructed by selecting random
      samples of the residuals and adding them back onto *data*. So if
      residuals are provided, then *data + residuals* should be equal
      to the original, raw data.

    :param bins:
      An optional list of numbers representing the edges of bins into
      which we will accumulate mean counts of statistics.


    :return:
      If *bins* is not provided, I will return an :math:`(R x M)` array giving
      the value of the statistic for each row of *data* for sample.

      If *bins* is not provided, I will return a list of length
      :math:`len(bins) - 1` where each item is the average number of
      rows of *data* across all samples that have statistic value
      falling in the range associated with the corresponding bin.

      """
    accumulator = DEFAULT_ACCUMULATOR

    build_sample = None
    if residuals is None:
        build_sample = lambda idxs: data[..., idxs]
    else:
        build_sample = lambda idxs: data + residuals[..., idxs]

    if indexes is None:
        if sample_layout is None:
            sample_layout = [ np.arange(np.shape(data)[1]) ]
        indexes = random_indexes(sample_layout, R)

    if bins is not None:
        accumulator = _binning_accumulator(bins, len(indexes))
        
    # We'll return an R x n array, where n is the number of
    # features. Each row is the array of statistics for all the
    # features, using a different random sampling.
    
    logging.info("Processing {0} samples".format(len(indexes)))
    samples = (build_sample(p) for p in indexes)
    stats   = (stat_fn(s)      for s in samples)

    reduced = reduce(accumulator.reduce_fn, stats, accumulator.initializer)


    logging.info("Finalizing results")
    return accumulator.finalize_fn(reduced)

def cumulative_hist_shape(bins):
    """Returns the shape of the histogram with the given bins.

    The shape is similar to that of bins, except the last dimension
    has one less element.

    """
    shape = np.shape(bins)
    shape = shape[:-1] + (shape[-1] - 1,)
    return shape

def cumulative_hist(values, bins):
    """Create a cumulative histogram for values using the given bins.

    The shape of values and bins must be the same except for the last
    dimension.  So np.shape(values)[:-1] must equal
    np.shape(bins[:-1]). The last dimension of values is simply a
    listing of values. The last dimension of bins is the list of bin
    edges for the histogram.

    """
    shape = cumulative_hist_shape(bins) 
    res = np.zeros(shape)
    for idx in np.ndindex(shape[:-1]): 
        (hist, ignore) = np.histogram(values[idx], bins[idx]) 
        res[idx] = np.array(np.cumsum(hist[::-1])[::-1], float)
    return res


def bins_uniform(num_bins, stats):
    """Returns a set of evenly sized bins for the given stats.

    Stats should be an array of statistic values, and num_bins should
    be an integer. Returns an array of bin edges, of size num_bins +
    1. The bins are evenly spaced between the smallest and largest
    value in stats.

    Note that this may not be the best method for binning the
    statistics, especially if the distribution is heavily skewed
    towards one end.

    """
    base_shape = np.shape(stats)[:-1]
    bins = np.zeros(base_shape + (num_bins + 1,))
    for idx in np.ndindex(base_shape):
        maxval = np.max(stats[idx])
        edges = np.concatenate((np.linspace(0, maxval, num_bins), [np.inf]))
        edges[0] = - np.inf
        bins[idx] = edges

    return bins


def bins_custom(num_bins, stats):
    """Get an array of bin edges based on the actual computed
    statistic values. stats is an array of length n. Returns an array
    of length num_bins + 1, where bins[m, n] and bins[m + 1, n] define
    a bin in which to count features for condition n. There is a bin
    edge for negative and positive infinity, and one for each
    statistic value.

    """
    base_shape = np.shape(stats)[:-1]
    bins = np.zeros(base_shape + (num_bins + 1,))
    bins[ : -1] = sorted(stats)
    bins[-1] = np.inf
    return bins


def num_orderings(full, reduced=None):

    # If there is no reduced layout, just find the number of
    # orderings of indexes in the full layout.
    if reduced is None or len(reduced) == 0:

        # If we only have one group in the full layout, there's only
        # one ordering of the indexes in that group.
        if len(full) <= 1:
            return 1

        # Otherwise say N is the total number of items in the full
        # layout and k is the number in the 0th group of the full
        # layout. The number of orderings is (N choose k) times the
        # number of orderings for the rest of the groups.
        N = sum(map(len, full))
        k   = len(full[0])
        return comb(N, k) * num_orderings(full[1:])

    # Since we got a reduced layout, we need to find the number of
    # orderings *within* the first group in the reduced layout,
    # then multiply that by the orderings in the rest of the
    # reduced layout. First find the number of groups in the full
    # layout that correspond to the first group in the reduced layout.

    # First find the number of groups in the full layout that fit in
    # the first group of the reduced layout.
    r = 0
    size = 0
    while size < len(reduced[0]):
        size += len(full[r])
        r += 1

    if size > len(reduced[0]):
        raise InvalidLayoutException("The layout is invalid")

    num_arr_first = num_orderings(full[ : r])
    num_arr_rest  = num_orderings(full[r : ], reduced[1 : ])
    return num_arr_first * num_arr_rest


def all_orderings_within_group(items, sizes):

    """

    One index, one group of size one:

    >>> list(all_orderings_within_group([0], [1]))
    [[0]]

    Two indexes, one group of size two:

    >>> list(all_orderings_within_group([0, 1], [2]))
    [[0, 1]]

    Two indexes, two groups of size one:
    
    >>> list(all_orderings_within_group([0, 1], [1, 1]))
    [[0, 1], [1, 0]]

    >>> list(all_orderings_within_group([0, 1, 2, 3], [2, 2])) # doctest: +NORMALIZE_WHITESPACE
    [[0, 1, 2, 3], 
     [0, 2, 1, 3],
     [0, 3, 1, 2],
     [1, 2, 0, 3],
     [1, 3, 0, 2],
     [2, 3, 0, 1]]
    
    """
    items = set(items)
    if len(items) != sum(sizes):
        raise InvalidLayoutException("Layout is bad")

    for c in map(list, combinations(items, sizes[0])):
        if len(sizes) == 1:
            yield c
        else:
            for arr in all_orderings_within_group(
                items.difference(c), sizes[1:]):
                yield c + arr

def all_orderings(full, reduced):
    
    sizes = map(len, full)

    p = 0
    q = 0

    grouped = []
    for i, grp in enumerate(reduced):

        while sum(sizes[p : q]) < len(grp):
            q += 1

        if sum(sizes[p : q]) > len(grp):
            raise Exception("Bad layout")

        grouped.append(all_orderings_within_group(set(grp), sizes[p : q]))
        p = q

    for prod in product(*grouped):
        row = []
        for grp in prod:
            row.extend(grp)
        yield row

def random_ordering(full, reduced):
    row = []
    for grp in reduced:
        grp = np.copy(grp)
        np.random.shuffle(grp)
        row.extend(grp)
    return row

def random_orderings(full, reduced, R):
    """Get an iterator over at most R random index shuffles.

    :param full: the :term:`layout`
    :param reduced: the reduced :term:`layout`
    :param R: the maximum number of orderings to return

    :return: iterator over random orderings of indexes

    Each item in the resulting iterator will be an ndarray of the
    indexes in the given layouts. The indexes within each group of the
    reduced layout will be shuffled.
    
    """
    # Set of random orderings we've returned so far
    orderings = set()
    
    # The total number of orderings of indexes within the groups of
    # the reduced layout that result in a distinct assignment of
    # indexes into the groups defined by the full layout.
    N = num_orderings(full, reduced)
    
    # If the number of orderings requested is greater than the number
    # of distinct orderings that actually exist, just return all of
    # them.
    if R >= N:
        for arr in all_orderings(full, reduced):
            yield arr

    # Otherwise repeatedly find a random ordering, and if it's not one
    # we've already yielded, yield it.
    else:
        while len(orderings) < R:

            arr = random_ordering(full, reduced)
            key = tuple(arr)

            if key not in orderings:
                orderings.add(key)
                yield arr



class OneSampleTTest:

    def __init__(self, alphas=None):
        self.alphas = alphas

    def __call__(self, data):
        n = np.size(data, axis=-1)
        x = np.mean(data, axis=-1)
        s = np.std(data, axis=-1)

        numer = x
        denom = s / np.sqrt(n)
        if self.alphas is not None:
            denom = np.array([denom + x for x in self.alphas])
        return np.abs(numer / denom)


class MeansRatio:

    """Means ratio statistic.

    Supports layouts where there are two experimental conditions, with
    or without blocking.

    :param condition_layout:
      A layout that groups the sample indexes together into groups
      that have the same experimental condition. MeansRatio only
      supports designs where there are exactly two conditions, so
      len(condition_layout) must be 2.

    :param block_layout: 
      If the input has blocking variables, then block layout
      should be a layout that groups the sample indexes together
      by block.

    :param alphas: 
      Optional array of "tuning parameters". 

    :param symmetric:
      If true, gives the inverse of the ratio when the ratio is less
      than 1. Use this when it does not matter which condition is
      greater than the other one.
      
    """

    name = "means ratio"

    def __init__(self, condition_layout, block_layout, alphas=None, symmetric=True):
        conditions = len(condition_layout)
        blocks     = len(block_layout)

        if conditions != 2:
            raise UnsupportedLayoutException(
                """MeansRatio only supports configurations where there are two conditions and n blocks. You have {conditions} conditions and {blocks} blocks.""".format(
                    conditions=conditions,
                    blocks=blocks))

        self.condition_layout  = map(set, condition_layout)
        self.block_layout      = map(set, block_layout)
        self.alphas            = alphas
        self.symmetric         = symmetric


    def __call__(self, data):

        conds  = self.condition_layout
        blocks = self.block_layout

        # Build two new layouts. c0 is a list of lists of indexes into
        # the data that represent condition 0 for each block. c1 is
        # the same for data that represent condition 1 for each block.
        c0_blocks = [ conds[0].intersection(x) for x in blocks ]
        c1_blocks = [ conds[1].intersection(x) for x in blocks ]

        # Get the mean for each block for both conditions.
        means = np.array([group_means(data, c0_blocks),
                          group_means(data, c1_blocks)])

        # If we have tuning params, add another dimension to the front
        # of each ndarray to vary the tuning param.  First add the
        # alpha dimension to the front of means, then swap it so the
        # dimensionality becomes (alpha, condition, ...)
        if self.alphas is not None:
            means = np.array([ means + x for x in self.alphas ])
            means = means.swapaxes(0, 1)

        ratio = means[0] / means[1]

        # If we have more than one block, we combine their ratios
        # using the geometric mean.
        ratio = scipy.stats.gmean(ratio, axis=-1)

        # 'Symmetric' means that the order of the conditions does not
        # matter, so we should always return a ratio >= 1. So for any
        # ratios that are < 1, use the inverse.
        if self.symmetric:
            # Add another dimension to the front where and 1 is its
            # inverse, then select the max across that dimension
            ratio_and_inverse = np.array([ratio, 1.0 / ratio])
            ratio = np.max(ratio_and_inverse, axis=0)

        return ratio
        

class OneSampleDifferenceTTest:

    def __init__(self, layout_reduced, alphas=None):

        self.alphas = alphas
        self.name   = "OneSampleDifferenceTTest"

        if not layout_is_paired(layout_reduced):
            raise Exception(
                "The reduced layout " + str(layout_reduced) + " " +
                "is invalid for a one-sample difference t-test. " +
                "Each group must have exactly two items in it")
                        
        self.layout_reduced = layout_reduced        
        self.child = OneSampleTTest(alphas=self.alphas)

    def __call__(self, data):
        
        pairs = self.layout_reduced
        idxs_a = [p[0] for p in pairs]
        idxs_b = [p[1] for p in pairs]
        a = data[..., idxs_a]
        b = data[..., idxs_b]

        diffs = data[..., idxs_a] - data[..., idxs_b]

        res = self.child(diffs)
        return res
        

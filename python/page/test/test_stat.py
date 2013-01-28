import numpy as np
import unittest
from page.stat import *

class StatTest(unittest.TestCase):

    def setUp(self):
        self.ftest_in = np.array([
                 6.0,  8.0, 13.0,
                 8.0, 12.0,  9.0,
                 4.0,  9.0, 11.0,
                 5.0, 11.0,  8.0,
                 3.0,  6.0,  7.0,
                 4.0,  8.0, 12.0])

        self.infile = 'sample_data/4_class_testdata_header1.txt'

    def test_tstat(self):
        data = np.array(
            [
                [
                    [2.410962, 0.90775],
                    [1.897421, 0.964438],
                    [2.421239, 1.07578],
                    [1.798668, 1.065872]],
                [
                    [2.410962, 0.90775],
                    [1.897421, 0.964438],
                    [2.421239, 1.07578],
                    [1.798668, 1.065872]],
                ])
        data = np.swapaxes(data, 0, 2)
        alpha = 1.62026604316528 * Ttest.TUNING_PARAM_RANGE_VALUES[4]
        stat = Ttest(alpha)
        result = stat(data)

        expected = [1.51898640652018,
                    1.51898640652018]

        self.assertAlmostEqual(sum(result),
                               sum(expected),
                               )

    def test_3d_tstat(self):
        data = np.array(
            [
                [
                    [2.410962, 0.90775],
                    [1.897421, 0.964438],
                    [2.421239, 1.07578],
                    [1.798668, 1.065872]],
                [
                    [2.410962, 0.90775],
                    [1.897421, 0.964438],
                    [2.421239, 1.07578],
                    [1.798668, 1.065872]],
                [
                    [2.410962, 0.90775],
                    [1.897421, 0.964438],
                    [2.421239, 1.07578],
                    [1.798668, 1.065872]]])
        data = np.swapaxes(data, 0, 2)
        alpha = 1.62026604316528 * Ttest.TUNING_PARAM_RANGE_VALUES[4]
        stat = Ttest(alpha)
        result = stat(data)

        expected = [1.51898640652018,
                    1.51898640652018,
                    1.51898640652018,
                    ]

        self.assertAlmostEqual(sum(result),
                               sum(expected),
                               )

    def test_2d_tstat(self):
        data = np.array(
            [
                [2.410962, 0.90775],
                [1.897421, 0.964438],
                [2.421239, 1.07578],
                [1.798668, 1.065872]])
        data = np.swapaxes(data, 0, 1)
        alpha = 1.62026604316528 * Ttest.TUNING_PARAM_RANGE_VALUES[4]
        stat = Ttest(alpha)
        result = stat(data)

        expected = 1.51898640652018
        self.assertAlmostEqual(result, expected)


    def test_ftest_no_tuning_params(self):

        expected = 9.26470588235
        ftest = Ftest(
            layout_full=[range(i, 18, 3) for i in range(3)],
            layout_reduced=[range(18)])
        self.assertAlmostEqual(expected, ftest(self.ftest_in))

        a2 = np.concatenate((self.ftest_in,
                             self.ftest_in)).reshape((2, 18))
        print a2
        got = ftest(a2)
        self.assertEqual(np.shape(got), (2,))
        self.assertAlmostEqual(got[0], expected)
        self.assertAlmostEqual(got[1], expected)

    def test_ftest_with_tuning_params(self):

        alphas = np.array([0.0, 0.01, 0.1, 1, 3])

        expected = 9.26470588235
        ftest = Ftest(
            layout_full=[range(i, 18, 3) for i in range(3)],
            layout_reduced=[range(18)],
            alphas=alphas)

        self.assertAlmostEqual(expected, ftest(self.ftest_in)[0])

    def test_apply_layout(self):
        np.testing.assert_almost_equal(
            np.array([[0, 1], [2, 3], [4,5]]),
            apply_layout([[0,1], [2,3], [4,5]], np.arange(6)))

        np.testing.assert_almost_equal(
            np.array([[0, 1, 2, 3, 4, 5]]),
            apply_layout([[0, 1, 2, 3, 4, 5]], np.arange(6)))

    def test_num_arrangements(self):

        def assertArrangements(full, reduced, expected):
            got = num_arrangements(full, reduced)
            self.assertEquals(got, expected)

        assertArrangements([[0]], None, 1)
        assertArrangements([[0, 1]],   None, 1)
        assertArrangements([[0], [1]], None, 2)
        assertArrangements([[0, 1], [2, 3]], None, 6)

        assertArrangements([[0, 1], [2, 3], [4, 5]], None, 90)

        assertArrangements([[0, 1], [2, 3], [4, 5], [6, 7]],
                           [[0, 1,   2, 3], [4, 5,   6, 7]],
                           36)

    def test_arrangements(self):
        def assertArrangements(items, sizes, expected):
            got = all_arrangements_within_group(set(items), sizes)
            self.assertEquals(got, expected)

        assertArrangements([0], [1], [[0]])
        assertArrangements([0, 1], [2], [[0, 1]])

        assertArrangements([0, 1], [1, 1], [[0, 1], [1, 0]])

        assertArrangements([0, 1, 2, 3], [2, 2], 
                           [[0, 1, 2, 3], 
                            [0, 2, 1, 3],
                            [0, 3, 1, 2],
                            [1, 2, 0, 3],
                            [1, 3, 0, 2],
                            [2, 3, 0, 1]])
                            


        
#         assertPerms(
#             [[0, 1], [2, 3], [4, 5], [6, 7]],
#             [[0, 1,   2, 3], [4, 5,   6, 7]],
#             [
#                 [0, 1,   2, 3,   4, 5,   6, 7],
#                 [0, 1,   2, 3,   4, 6,   5, 7],
#                 [0, 1,   2, 3,   4, 7,   5, 6],
#                 [0, 1,   2, 3,   5, 6,   4, 7],
#                 [0, 1,   2, 3,   5, 7,   4, 6],
#                 [0, 1,   2, 3,   6, 7,   4, 5],

#                 [0, 2,   1, 3,   4, 5,   6, 7],
#                 [0, 2,   1, 3,   4, 6,   5, 7],
#                 [0, 2,   1, 3,   4, 7,   5, 6],
#                 [0, 2,   1, 3,   5, 6,   4, 7],
#                 [0, 2,   1, 3,   5, 7,   4, 6],
#                 [0, 2,   1, 3,   6, 7,   4, 5],

#                 [0, 3,   1, 2,   4, 5,   6, 7],
#                 [0, 3,   1, 2,   4, 6,   5, 7],
#                 [0, 3,   1, 2,   4, 7,   5, 6],
#                 [0, 3,   1, 2,   5, 6,   4, 7],
#                 [0, 3,   1, 2,   5, 7,   4, 6],
#                 [0, 3,   1, 2,   6, 7,   4, 5],
                     
#                 [1, 2,   0, 3,   4, 5,   6, 7],
#                 [1, 2,   0, 3,   4, 6,   5, 7],
#                 [1, 2,   0, 3,   4, 7,   5, 6],
#                 [1, 2,   0, 3,   5, 6,   4, 7],
#                 [1, 2,   0, 3,   5, 7,   4, 6],
#                 [1, 2,   0, 3,   6, 7,   4, 5],

#                 [1, 3,   0, 2,   4, 5,   6, 7],
#                 [1, 3,   0, 2,   4, 6,   5, 7],
#                 [1, 3,   0, 2,   4, 7,   5, 6],
#                 [1, 3,   0, 2,   5, 6,   4, 7],
#                 [1, 3,   0, 2,   5, 7,   4, 6],
#                 [1, 3,   0, 2,   6, 7,   4, 5],

#                 [2, 3,   0, 1,   4, 5,   6, 7],
#                 [2, 3,   0, 1,   4, 6,   5, 7],
#                 [2, 3,   0, 1,   4, 7,   5, 6],
#                 [2, 3,   0, 1,   5, 6,   4, 7],
#                 [2, 3,   0, 1,   5, 7,   4, 6],
#                 [2, 3,   0, 1,   6, 7,   4, 5]])
        

if __name__ == '__main__':
    unittest.main()

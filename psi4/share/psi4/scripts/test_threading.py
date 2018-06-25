#!/usr/bin/env python

import os
import sys
import math
import time
import importlib
import subprocess

if sys.version_info <= (3, 0):
    print('Much of this script needs py3')
    sys.exit()

# good
#import numpy as np
#import psi4

# bad
import psi4
import numpy as np


def test_threaded_blas(args):
    threads = int(args.nthread)

    times = {}

    size = [200, 500, 2000, 4000]
    threads = [1, threads]

    for th in threads:
        psi4.set_num_threads(th)

        for sz in size:
            nruns = max(1, int(1.e10 / (sz ** 3)))

            a = psi4.core.Matrix(sz, sz)
            b = psi4.core.Matrix(sz, sz)
            c = psi4.core.Matrix(sz, sz)

            tp4 = time.time()
            for n in range(nruns):
                c.gemm(False, False, 1.0, a, b, 0.0)

            retp4 = (time.time() - tp4) / nruns

            tnp = time.time()
            for n in range(nruns):
                np.dot(a, b, out=np.asarray(c))

            retnp = (time.time() - tnp) / nruns
            print("Time for threads %2d, size %5d: Psi4: %12.6f  NumPy: %12.6f" % (th, sz, retp4, retnp))
            if sz == 4000:
                times["p4-n{}".format(th)] = retp4
                times["np-n{}".format(th)] = retnp
                assert psi4.get_num_threads() == th

    rat1 = times["np-n" + str(threads[-1])] / times["p4-n" + str(threads[-1])]
    rat2 = times["p4-n" + str(threads[0])] / times["p4-n" + str(threads[-1])]
    print("  NumPy@n%d : Psi4@n%d ratio (want ~1): %.2f" % (threads[-1], threads[-1], rat1))
    print("   Psi4@n%d : Psi4@n%d ratio (want ~%d): %.2f" % (threads[0], threads[-1], threads[-1], rat2))
    if args.passfail:
        assert math.isclose(rat1, 1.0, rel_tol=0.2), 'PsiAPI:NumPy speedup {} !~= 1.0'.format(rat1)
        assert math.isclose(rat2, threads[-1], rel_tol=0.4), 'PsiAPI speedup {} !~= {}'.format(rat2, threads[-1])


def test_psithon(args):

    inputdat = """
molecule dimer {
0 1
C   0.000000  -0.667578  -2.124659
C   0.000000   0.667578  -2.124659
H   0.923621  -1.232253  -2.126185
H  -0.923621  -1.232253  -2.126185
H  -0.923621   1.232253  -2.126185
H   0.923621   1.232253  -2.126185
--
0 1
C   0.000000   0.000000   2.900503
C   0.000000   0.000000   1.693240
H   0.000000   0.000000   0.627352
H   0.000000   0.000000   3.963929
units angstrom
}

set {
    BASIS jun-cc-pVQZ
    SCF_TYPE DF
    FREEZE_CORE True
}

energy('sapt0')

compare_values(85.189064196429, dimer.nuclear_repulsion_energy(), 9,        "Nuclear Repulsion Energy")
compare_values(-0.00343131388,  psi4.get_variable("SAPT ELST ENERGY"), 6,   "SAPT0 elst")
compare_values( 0.00368418851,  psi4.get_variable("SAPT EXCH ENERGY"), 6,   "SAPT0 exch")
compare_values(-0.00094288048,  psi4.get_variable("SAPT IND ENERGY"), 6,    "SAPT0 ind")
compare_values(-0.00231901067,  psi4.get_variable("SAPT DISP ENERGY"), 6,   "SAPT0 disp")
compare_values(-0.00300901652,  psi4.get_variable("SAPT0 TOTAL ENERGY"), 6, "SAPT0")
"""

    tfn = '_thread_test_input_psi4_yo'
    with open(tfn + '.in', 'w') as fp:
        fp.write(inputdat)

    run_psithon_inputs(args, tfn=tfn, label='Psi4')


def run_psithon_inputs(args, tfn, label):

    times = {}
    threads = [1, int(args.nthread)]

    for nt in threads:
        t0 = time.time()
        cmd = """psi4 -i {tfn}.in -o {tfn}_n{nt}.out -n{nt}""".format(tfn=tfn, nt=nt)
        print('Running {} ...'.format(cmd))
        subprocess.call(cmd.split())

        t1 = time.time()
        times[nt] = t1 - t0
        print("Time for threads %2d: Psi4: %12.6f" % (nt, times[nt]))

    rat1 = times[threads[0]] / times[threads[-1]]
    print("   Psi4@n%d : Psi4@n%d ratio (want ~%d): %.2f" % (threads[0], threads[-1], threads[-1], rat1))
    if args.passfail:
        #assert math.isclose(rat1, threads[-1], rel_tol=0.6), 'Psithon speedup {} !~= {}'.format(rat1, threads[-1])
        assert rat1 > 1.25, '{} Psithon speedup {} !~= {}'.format(label, rat1, threads[-1])


def test_plugin_dfmp2(args):

    inputdat = """
import %s

molecule {
0 1
C     0.0000000    0.0000000    1.0590353
C     0.0000000   -1.2060084    1.7576742
C     0.0000000   -1.2071767    3.1515905
C     0.0000000    0.0000000    3.8485751
C     0.0000000    1.2071767    3.1515905
C     0.0000000    1.2060084    1.7576742
H     0.0000000    0.0000000   -0.0215805
H     0.0000000   -2.1416387    1.2144217
H     0.0000000   -2.1435657    3.6929953
H     0.0000000    0.0000000    4.9301499
H     0.0000000    2.1435657    3.6929953
H     0.0000000    2.1416387    1.2144217
--
0 1
C    -1.3940633    0.0000000   -2.4541524
C    -0.6970468    1.2072378   -2.4546277
C     0.6970468    1.2072378   -2.4546277
C     1.3940633    0.0000000   -2.4541524
C     0.6970468   -1.2072378   -2.4546277
C    -0.6970468   -1.2072378   -2.4546277
H    -2.4753995    0.0000000   -2.4503221
H    -1.2382321    2.1435655   -2.4536764
H     1.2382321    2.1435655   -2.4536764
H     2.4753995    0.0000000   -2.4503221
H     1.2382321   -2.1435655   -2.4536764
H    -1.2382321   -2.1435655   -2.4536764
}

set {
  scf_type df
  mp2_type df
  basis aug-cc-pvdz
  freeze_core true
}

e, wfn = energy('plugdfmp2', return_wfn=True)
compare_values(-1.6309450762271729, wfn.get_variable('MP2 CORRELATION ENERGY'), 5, 'df-mp2 energy')  # aug-cc-pvdz
#compare_values(-1.5720781831194317, wfn.get_variable('MP2 CORRELATION ENERGY'), 5, 'df-mp2 energy')  # cc-pvdz
""" % (args.module)

    tfn = '_dfmp2_plugin_thread_test_input_psi4_yo'
    with open(tfn + '.in', 'w') as fp:
        fp.write(inputdat)

    run_psithon_inputs(args, tfn=tfn, label='Plugin dfmp2')


def print_math_ldd(args):

    module, sharedlibrary = args.module.split('/')
    mod = importlib.import_module(module)
    modcore = os.path.dirname(os.path.abspath(mod.__file__)) + os.path.sep + sharedlibrary

    if sys.platform.startswith('linux'):
        lddish = 'ldd -v'
    elif sys.platform.startswith('darwin'):
        lddish = 'otool -L'
    else:
        print('Not available w/o `ldd` or `otool`')
        return True

    cmd = """{} {} | grep -e ':' -e 'mkl' -e 'openblas' -e 'iomp5' -e 'gomp'""".format(lddish, modcore)
    print('Running {} ...'.format(cmd))
    subprocess.call(cmd, shell=True)
    lddout = subprocess.getoutput(cmd)
    report = {'mkl': lddout.count('libmkl'),
              'iomp5': lddout.count('libiomp5'),
              'openblas': lddout.count('libopenblas'),
              'gomp': lddout.count('libgomp')}
    print(report)
    report = {k : bool(v) for k, v in report.items()}
    okmkl = report['mkl'] and report['iomp5'] and not report['openblas'] and not report['gomp']
    okopenblas = not report['mkl'] and not report['iomp5'] and report['openblas'] and report['gomp']
    if args.passfail:
        assert okmkl != okopenblas


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="Psi4 threading tester. `psi4` and `import psi4` expected in *PATHs")
    parser.add_argument("-n", "--nthread", default=4,
                        help="""Number of threads to use. Psi4 disregards OMP_NUM_THREADS/MKL_NUM_THREADS.""")
    parser.add_argument("--passfail", action='store_true',
                        help="""Instead of just printing, run as tests.""")
    parser.add_argument("--module", default='psi4/core.so',
                        help="""In --ldd mode, module and shared library to analyze, e.g., 'greatplugin/cxxcode.so'.
In --plugin-dfmp2 mode, name of dfmp2 module to load, e.g., 'plugdfmp2'.""")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument('--psiapi', action='store_true',
                        help="""Test Psi4 (PsiAPI) vs NumPy in threaded matrix multiply.""")
    group.add_argument('--psithon', action='store_true',
                        help="""Test Psi4 (PSIthon) in threaded SAPT calc.""")
    group.add_argument('--ldd', action='store_true',
                        help="""Run ldd to examine BLAS and OMP linking of psi4/core.so (or whatever supplied to --module).""")
    group.add_argument('--plugin-dfmp2', action='store_true',
                        help="""Test dfmp2 plugin template (PSIthon) threading.""")

    args, unknown = parser.parse_known_args()

    if args.psiapi:
        test_threaded_blas(args)
    elif args.psithon:
        test_psithon(args)
    elif args.ldd:
        print_math_ldd(args)
    elif args.plugin_dfmp2:
        test_plugin_dfmp2(args)
    else:
        test_threaded_blas(args)
        test_psithon(args)
        print_math_ldd(args)


"""
PFX="usr/local/psi4"
PLUG="plugdfmp2"
THD=8
# * build psi4 and test its threading
PYTHONPATH=stage/$PFX/lib/ python stage/$PFX/share/psi4/scripts/test_threading.py --passfail --ldd
PATH=stage/$PFX/bin/:$PATH PYTHONPATH=stage/$PFX/lib/ python stage/$PFX/share/psi4/scripts/test_threading.py --passfail -n$THD
# * build an OpenMP plugin and test its threading
stage/$PFX/bin/psi4 --plugin-name $PLUG --plugin-template dfmp2
cd $PLUG && `../stage/$PFX/bin/psi4 --plugin-compile` && make && cd ..
PYTHONPATH=stage/$PFX/lib/:. python stage/$PFX/share/psi4/scripts/test_threading.py --passfail --ldd --module="$PLUG/$PLUG.so"
PATH=stage/$PFX/bin/:$PATH PYTHONPATH=stage/$PFX/lib/:. python stage/$PFX/share/psi4/scripts/test_threading.py --passfail --plugin-dfmp2 --module="$PLUG" -n$THD
"""
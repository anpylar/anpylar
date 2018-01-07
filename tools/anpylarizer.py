#!/usr/bin/env python
# -*- coding: utf-8; py-indent-offset:4 -*-
###############################################################################
# Copyright 2018 The AnPyLar Team. All Rights Reserved.
# Use of this source code is governed by an MIT-style license that
# can be found in the LICENSE file at http://anpylar.com/mit-license
###############################################################################
import argparse
import os.path
import sys


def run(pargs=None, name=None):
    args, parser = parse_args(pargs=pargs, name=name)

    try:
        from anpylar.packaging import Bundler, Paketizer
    except ImportError:
        print('-' * 50)
        print('The package *anpylar* seems to be missing')
        print('Execute (and then try again): ')
        print('    pip install --upgrade anpylar')
        print('-' * 50)
        parser.print_help()
        sys.exit(1)

    # Get the working directories
    basedir = os.path.join(os.path.dirname(__file__), '..')
    datadir = os.path.join(basedir, 'data')

    # Prepare the paths
    br_js = os.path.join(datadir, 'brython.js')
    brstd_js = os.path.join(datadir, 'brython_stdlib.js')
    anpylar_vfs_js = os.path.join(datadir, 'anpylar.vfs.js')
    anpylar_auto_vfs_js = os.path.join(datadir, 'anpylar.auto_vfs.js')
    anpylar_d_auto_vfs_js = os.path.join(datadir, 'anpylar_d.auto_vfs.js')
    outfile = (os.path.join(basedir, 'anpylar.js'), False)
    outfile_debug = (os.path.join(basedir, 'anpylar_debug.js'), True)

    if args.paketize:
        anpylar_dir = os.path.join(basedir, 'anpylar')
        paket = Paketizer(anpylar_dir)
        paket.write_autoload(anpylar_auto_vfs_js)

        # Generate version where lineinfo makes sense
        anpylar_dir = os.path.join(basedir, 'anpylar')
        paket = Paketizer(anpylar_dir, minify=False)
        paket.write_autoload(anpylar_d_auto_vfs_js)

    for outf, dflag in (outfile, outfile_debug):
        # Configure the bundler paths / options
        bundler = Bundler()
        bundler.set_br_debug(dflag)
        bundler.set_brython(br_js)
        bundler.set_brython_stdlib(brstd_js)
        # choose version with lineinfo according to dflag
        if not dflag:
            bundler.set_anpylar_auto_vfs(anpylar_auto_vfs_js)
        else:
            bundler.set_anpylar_auto_vfs(anpylar_d_auto_vfs_js)

        bundler.do_anpylar_vfs()  # needed to keep the bundler generic

        if args.optimize:
            bundler.optimize_stdlib()

        bundler.write_bundle(outf)


def parse_args(pargs=None, name=None):
    parser = argparse.ArgumentParser(
        prog=name or os.path.basename(sys.argv[0]),
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description=('AnPyLar In-Package Bundle Creator')
    )

    parser.add_argument('--optimize', action='store_true',
                        help='Optimized the stdlib in the created anpylar.js')

    parser.add_argument('--paketize', action='store_true',
                        help='paketize anpylar to anpylar.auto_vfs.js')

    args = parser.parse_args(pargs)
    return args, parser


if __name__ == '__main__':
    run()

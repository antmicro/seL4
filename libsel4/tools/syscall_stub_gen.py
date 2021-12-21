#!/usr/bin/env python3
#
# Copyright 2020, Data61, CSIRO (ABN 41 687 119 230)
#
# SPDX-License-Identifier: BSD-2-Clause
#

#
# seL4 System Call Stub Generator
# ===============================
#
# 2009 David Greenaway
#
# This script generates system call stubs based on an XML specification of the
# objects that the kernel exports (and the methods those objects export).
#
# Previously, Magpie (an IDL compiler) was used to generate these stubs. As
# Magpie development progressed, support for a fixed ABI (i.e., the ABI
# implemented by the seL4 kernel) was lost, and support for generating
# alignment-safe code (required by platforms such as ARM) was also removed.
#
# This script is a stop-gap until these features can be restored in Magpie
# once again.
#
# The script has certain limitations:
#
#   * It must be told the size of all types. This includes complex types
#     such as structures.
#
#     We generate code that will cause compilation to fail if we get any
#     object's size wrong, which should help mitigate the number of bugs caused
#     because of this script becoming out of date compared to the source files.
#
#   * The script has only been tested on the actual seL4 API XML description.
#
#     No stress testing has taken place; there may be bugs if new and wonderful
#     XML method descriptions are added.
#

from argparse import ArgumentParser
import sys
from generator import WORD_SIZE_BITS_ARCH
from generator_c import Generator_C
from generator_rust import Generator_Rust

class GeneratorProvider:
    class GeneratorNotFoundException(Exception):
        pass

    generators = {'c': Generator_C, 'rust': Generator_Rust}

    @classmethod
    def get_generator(cls, name):
        try:
            return cls.generators[name]
        except KeyError as err:
            msg = f'Generator not found: {name}. Select one of {cls.get_generator_names()}'
            raise cls.GeneratorNotFoundException(msg) from err

    @classmethod
    def get_generator_names(cls):
        return list(cls.generators.keys())


def process_args():
    usage_str = """
    %(prog)s [OPTIONS] [FILES] """
    epilog_str = """

    """
    parser = ArgumentParser(description='seL4 System Call Stub Generator.',
                            usage=usage_str,
                            epilog=epilog_str)
    parser.add_argument("-o", "--output", dest="output", default="/dev/stdout",
                        help="Output file to write stub to. (default: %(default)s).")
    parser.add_argument("-b", "--buffer", dest="buffer", action="store_true", default=False,
                        help="Use IPC buffer exclusively, i.e. do not pass syscall arguments by registers. (default: %(default)s)")
    parser.add_argument("-a", "--arch", dest="arch", required=True, choices=WORD_SIZE_BITS_ARCH,
                        help="Architecture to generate stubs for.")
    parser.add_argument("--mcs", dest="mcs", action="store_true",
                        help="Generate MCS api.")

    wsizegroup = parser.add_mutually_exclusive_group()
    wsizegroup.add_argument("-w", "--word-size", dest="wsize",
                            help="Word size(in bits), for the platform.")
    wsizegroup.add_argument("-c", "--conf-file", dest="conf_file",
                            help="Config file for Kbuild, used to get Word size.")

    parser.add_argument("-l", "--lang", dest="lang", type=str.lower,
                        choices=GeneratorProvider.get_generator_names())
    parser.add_argument("files", metavar="FILES", nargs="+",
                        help="Input XML files.")

    return parser


def main():

    parser = process_args()
    args = parser.parse_args()

    if not (args.wsize or args.conf_file):
        parser.error("Require either -w/--word-size or -c/--conf-file argument.")
        sys.exit(2)

    # Get word size
    wordsize = -1

    if args.conf_file:
        try:
            with open(args.conf_file) as config:
                for line in config:
                    if line.startswith('CONFIG_WORD_SIZE'):
                        wordsize = int(line.split('=')[1].strip())
        except IndexError:
            print("Invalid word size in configuration file.")
            sys.exit(2)
    else:
        wordsize = int(args.wsize)

    if wordsize == -1:
        print("Invalid word size.")
        sys.exit(2)

    gen = GeneratorProvider.get_generator(args.lang)()
    gen.configure(args.arch, wordsize, args.files, args.buffer, args.mcs)
    gen.generate(args.output)


if __name__ == "__main__":
    sys.exit(main())

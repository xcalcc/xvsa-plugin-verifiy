#!/usr/bin/env python3
import os, sys, argparse, re

all_args = None

def transform_file(fn:str, outfp):
    if (outfp is None):
        outfp = sys.stdout
    ztvmode = 1
    classmode = 1
    ztvstart = re.compile("\[[0-9]*\]: (_ZTV.*) \[.*\]")
    ztvend = re.compile(" ENDBLOCK")
    ztvnormal = re.compile(" SYMOFF: (_ZN.*) \[[0-9,]*\].*")
    classname = re.compile("\[[0-9]*\]: (_ZN.*class\$E.*) \[.*\]")
    with open(fn, "r") as f:
        # Read list of lines
        out = [] # list to save lines
        while True:
            # Read next line
            line = f.readline()
            # If line is blank, then you struck the EOF
            if not line:
                break

            if classmode == 1:
                res = re.match(classname, line)
                if (res is not None):
                    outfp.write(": "+res.group(1).strip()+"\n")

            if (ztvmode == 1) :
                # If in ready mode, Find if it's a ZTV start.
                res = re.match(ztvstart, line)
                if (res is not None):
                    ztvmode = 2
                    # copy to result file
                    outfp.write(res.group(1).strip() + "\n")
                pass
            else:
                # If in ZTV mode, Find if it's a ZTV end
                res = re.match(ztvend, line)
                if (res is not None):
                    ztvmode = 1
                    # copy to result file
                    # outfp.write(res.group(1).strip() + "\n")
                else:
                    res = re.match(ztvnormal, line)
                    if res:
                        outfp.write(" " + res.group(1).strip() + "\n")
                pass
            pass
        pass
    pass


def parse_config():
    parser = argparse.ArgumentParser(description="file transformer to convert .W files to .W.ztv and .W.class files")
    # All Arguments
    parser.add_argument("-input", "-i", type=argparse.FileType('r'),
                        help="specify location for input file") 
    parser.add_argument("-output", "-o", type=argparse.FileType('w'),
                        required=False,
                        help="specify output location")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="increase output verbosity")
    parser.add_argument("-ztv", "--ztv", action="store_true",
                        help="output ztv contents")
    parser.add_argument("-class", "--class", action="store_true",
                        help="output class symbol names")
    args = parser.parse_args()
    all_args = args
    
    return args



if __name__ == "__main__":
    args = parse_config()
    transform_file(args.input.name, args.output)


#!/usr/bin/python3
#
#  Script to move a PCF to/from a strategy directory
#

import argparse
import io
import re
import sys
import os
import os.path
import subprocess
import tempfile
import shutil
import logging
from distutils.spawn import find_executable

actions = ("import", "export", "clean")
actions_help = '"import" from local installation, "export" to local installation'
repodir = os.path.realpath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "..")
)
basedir = os.path.join(repodir, "user")
placeholder = ".placeholder"

command_help = """
Copy Bernese files between the positionzpp pcf directories and
the local Bernese installation.  

The main actions are:
  import:  Import a configuration from the local installation to datum strategy
  export:  Export the configuration from a datum strategy to the local installation
  clean:   Clean all panel files (remove data specific to running a job)

These directories are located using the Bernese environment variables if they are
defined, otherwise the default LINZ Bernese installation directories are used.

Note that the input panel files in the OPT directories may be modified when the are
imported or exported to remove variable values where those values will be created by 
the Bernese Processing Engine when the PCF is run.

"""


def main():

    parser = argparse.ArgumentParser(
        description="Move a Bernese PCF and related files between the local Bernese installation and this repo",
        epilog=command_help,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    parser.add_argument("action", choices=actions, help=actions_help)
    parser.add_argument(
        "-u",
        "--user-dir",
        help="Bernese user directory, otherwise $U or $HOME/BERN52/GPSUSER",
    )
    parser.add_argument(
        "-o",
        "--overwrite",
        action="store_true",
        help="Force overwrite of existing files without prompting on export",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="More output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Less output")
    args = parser.parse_args()

    action = args.action
    force = args.overwrite

    logging.basicConfig(
        level=logging.DEBUG
        if args.verbose
        else logging.ERROR
        if args.quiet
        else logging.INFO
    )

    if not os.path.isdir(basedir):
        raise RuntimeError(
            f"Datum processing strategy directory not found at {basedir}"
        )

    userdir = getBerneseUserDir(args.user_dir)
    if not os.path.isdir(userdir) or not os.path.isdir(f"{userdir}/PCF"):
        raise RuntimeError("User directory {userdir} doesn't contain a PCF directory")

    pcfdir = os.path.join(basedir, "PCF")
    strpcf = None
    if os.path.isdir(pcfdir):
        pcfnames = [f[:-4] for f in os.listdir(pcfdir) if f.endswith(".PCF")]
        if len(pcfnames) > 1:
            raise RuntimeError(f"Strategy has more than one PCF: {', '.join(pcfnames)}")
        elif len(pcfnames) == 1:
            strpcf = pcfnames[0]

    if action == "clean":
        logging.info(f'"Cleaning" panel files')
        cleanAllPanels(basedir)

    # import action
    elif action == "import":
        logging.info(f"Importing PCF {strpcf}")
        importPcf(userdir, strpcf, basedir)

    elif action == "export":
        logging.info(f"Exporting PCF {strpcf}")
        exportPcf(basedir, strpcf, userdir, force=force)


def exportPcf(basedir: str, strpcf: str, userdir: str, force=False) -> bool:
    files = getPcfFiles(basedir, strpcf)
    with tempfile.TemporaryDirectory() as tempdir:
        copyPcfFiles(basedir, files, tempdir)
        if strpcf != strpcf:
            srcpcfname = os.path.join(tempdir, "PCF", strpcf + ".PCF")
            tgtpcfname = os.path.join(tempdir, "PCF", strpcf + ".PCF")
            os.rename(srcpcfname, tgtpcfname)
        result = copyFiles(tempdir, userdir, force=force, hidden=True)
    # If we have created new OPT directories then these will need menu files
    # for the PCF to run
    addMissingMenuFiles(userdir, files)
    return result


def importPcf(userdir: str, strpcf: str, strusrdir: str):
    files = getPcfFiles(userdir, strpcf)
    if not files:
        raise RuntimeError(f"Cannot find PCF files pcf {strpcf}")
    with tempfile.TemporaryDirectory() as tempdir:
        copyPcfFiles(userdir, files, tempdir)
        if strpcf != strpcf:
            srcpcfname = os.path.join(tempdir, "PCF", strpcf + ".PCF")
            tgtpcfname = os.path.join(tempdir, "PCF", strpcf + ".PCF")
            os.rename(srcpcfname, tgtpcfname)
        # Clear out files from target directory to avoid orphans.  Rely on git
        # to restore if necessary.
        if os.path.isdir(strusrdir):
            logging.debug("Removing existing strategy user files")
            shutil.rmtree(strusrdir)
        copyFiles(tempdir, strusrdir, force=True, hidden=True)


def copyFiles(
    srcdir: str,
    tgtdir: str,
    filenames: list = None,
    force=False,
    hidden=False,
    logcopy=True,
) -> bool:
    """
    Copy files from src to target.  Compile a list of changed files,
    and a list of all files to copy (changed and new)
    If there are any then check with user before copying.
    If OK or no conflicts, then copy all files
    """
    if filenames is None:
        filenames = fileTreeList(srcdir, hidden=hidden)
    updates, copyfiles = updatedFiles(srcdir, filenames, tgtdir)
    if updates and not force:
        print(f"The following files will be updated in {tgtdir}:")
        for filename in updates:
            print(f"    {filename}")
        while True:
            answer = input("Enter Y to proceed, N to cancel: ")
            answer = answer.strip().upper()
            if answer == "Y":
                break
            elif answer == "N" or answer == "":
                return False
    for filename in copyfiles:
        srcfile = os.path.join(srcdir, filename)
        tgtfile = os.path.join(tgtdir, filename)
        tgtfiledir = os.path.dirname(tgtfile)
        os.makedirs(tgtfiledir, exist_ok=True)
        if logcopy:
            logging.debug(
                f"{'Updating' if os.path.exists(tgtfile) else 'Installing'} {tgtfile}"
            )
        shutil.copyfile(srcfile, tgtfile)
    return True


def addMissingMenuFiles(userdir: str, files: str):
    """
    If exporting creates new options directories in the users
    bernese configuration then these need menu input files for
    the Bernese processing engine to use them.
    """
    pandir = os.path.join(userdir, "PAN")
    menupattern = re.compile(r"^MENU\w*\.INP$")
    menus = []
    for filename in os.listdir(pandir):
        if menupattern.match(filename):
            menus.append(filename)
    options = set()
    optpattern = re.compile(r"^OPT\/(?P<optdir>\w+)\/")
    for filename in files:
        match = optpattern.match(filename)
        if match:
            options.add(match.group("optdir"))
    for opt in options:
        for menu in menus:
            optmenu = os.path.join(userdir, "OPT", opt, menu)
            if not os.path.exists(optmenu):
                srcmenu = os.path.join(pandir, menu)
                logging.debug(f"Copying menu {menu} to {opt} options directory")
                shutil.copyfile(srcmenu, optmenu)


def fileTreeList(srcdir: str, hidden=False) -> list:
    """
    Return  a list of all files in srcdir or subdirectories as
    relative paths to srcdir
    """
    filelist = []
    for dirpath, dirnames, filenames in os.walk(srcdir):
        reldir = os.path.relpath(dirpath, srcdir)
        for filename in filenames:
            # Exclude hidden files
            if hidden or not filename.startswith("."):
                filelist.append(os.path.join(reldir, filename))
    filelist.sort()
    return filelist


def updatedFiles(srcdir: str, srcfilelist: list, tgtdir: str) -> list:
    """
    Return a list of files in srcdir which are different to corresponding files
    in tgtdir.
    """
    changedfiles = []
    copyfiles = []
    for filename in srcfilelist:
        srcfile = os.path.join(srcdir, filename)
        if not os.path.exists(srcfile):
            continue
        srcsize = os.path.getsize(srcfile)
        tgtfile = os.path.join(tgtdir, filename)
        if not os.path.exists(tgtfile):
            copyfiles.append(filename)
            continue
        tgtsize = os.path.getsize(tgtfile)
        # Special handling of Bernese INP panel files to avoid warning about
        # differences due to using a panel
        ispanel = filename.startswith("OPT/") and filename.endswith(".INP")
        if (srcsize != tgtsize) and not ispanel:
            changedfiles.append(filename)
            continue
        srcdata = open(srcfile, "rb").read()
        tgtdata = open(tgtfile, "rb").read()
        # If copying PCF input files then assume source has already been cleaned
        # when extracting files, so only need to update target.
        if ispanel:
            srcdata = srcdata.decode("utf8")
            tgtdata = cleanPanel(tgtdata.decode("utf8"))
        if srcdata != tgtdata:
            changedfiles.append(filename)
    copyfiles.extend(changedfiles)
    copyfiles.sort()
    return changedfiles, copyfiles


def getPcfScripts(pcffile: str) -> dict:
    """
    Parse a PCF file to extract the list of scripts use and the set of options
    directory which they take input from.

    Returns a dictionary of:
       {script:[opt1,opt2...], ...}
    """
    scripts = {}
    with open(pcffile) as ph:
        reading = False
        for l in ph:
            if l.startswith("PID"):
                if reading:
                    break
                reading = True
            if reading:
                match = re.match(r"^\d{3}\s(?P<script>\w+)\s+(?P<opt>\w+)(?:\s|$)", l)
                if match:
                    script = match.group("script")
                    opt = match.group("opt")
                    if script not in scripts:
                        scripts[script] = set()
                    scripts[script].add(opt)
    scripts = {s: list(scripts[s]) for s in scripts}
    return scripts


def getBerneseDir(name: str, argval: str, *candidates) -> str:
    berndir = argval
    if berndir is None:
        for candidate in candidates:
            try:
                candidate = re.sub(
                    r"\$\{(?P<envvar>\w+)\}",
                    lambda m: os.environ[m.group("envvar")],
                    candidate,
                )
                if os.path.isdir(candidate):
                    berndir = candidate
                    break
            except KeyError:
                continue
    if berndir is None:
        raise RuntimeError(f"Cannot find local bernese {name} directory")
    elif not os.path.isdir(berndir):
        raise RuntimeError(
            f"Bernese {name} directory name {berndir} is not a directory"
        )
    return berndir


def getBerneseUserDir(argval: str) -> str:
    return getBerneseDir("user", argval, "${U}", "${HOME}/BERN52/GPSUSER")


def getPcfFiles(userdir: str, pcfname: str, getMissingFiles=False):
    """
    Return a list of files used by a PCF relative to the user directory
    """
    pcffile = f"PCF/{pcfname}.PCF"
    srcpcf = os.path.join(userdir, pcffile)
    if not os.path.isfile(srcpcf):
        return []
    files = [pcffile]
    scripts = getPcfScripts(srcpcf)
    options = set()
    usedoptions = set()
    missingfiles = []
    for script in scripts:
        scriptfile = f"SCRIPT/{script}"
        srcscript = os.path.join(userdir, scriptfile)
        if not os.path.isfile(srcscript):
            missingfiles.append(scriptfile)
            continue
        files.append(scriptfile)
        programs = getScriptPrograms(srcscript)
        for option in scripts[script]:
            options.add(option)
            if len(programs) == 0:
                continue
            usedoptions.add(option)
            for program in programs:
                inpfile = f"OPT/{option}/{program}.INP"
                srcinp = f"{userdir}/{inpfile}"
                if not os.path.isfile(srcinp):
                    missingfiles.append(inpfile)
                    continue
                files.append(inpfile)
    if getMissingFiles:
        return missingfiles
    if missingfiles:
        raise RuntimeError(f"PCF {pcfname} is missing files: {', '.join(missingfiles)}")
    for option in options - usedoptions:
        files.append(f"OPT/{option}/{placeholder}")
    files.sort()
    return files


def getScriptPrograms(scriptfile: str) -> list:
    """
    Parse a script file to identify the Bernese programs that are used in the
    script, and hence the input panels that the script uses.

    Assumes that the programs are called with a specific syntax of:

      my $PGMNAM = "HELMR1";
      $bpe->RUN_PGMS($PGMNAM);

    The variable name (PGMNAM), white space, and choice of single or double quotes is not
    assumed.

    Returns a list of strings being the program names.
    """
    logging.debug(f"Processing script file {scriptfile}")
    programs = set()
    vars = {}
    with open(scriptfile) as sh:
        for l in sh:
            l = re.sub(r"\#.*", "", l)
            match = re.match(
                r"""^\s*(?:my\s+)?\$(?P<varname>\w+)\s*\=\s*(?P<quote>['"])(?P<value>\w+)(?P=quote)\s*\;\s*$""",
                l,
            )
            if match:
                vars[match.group("varname")] = match.group("value")
                continue
            match = re.search(r"\$bpe\-\>RUN_PGMS\(\s*\$(?P<varname>\w+)\s*\)", l)
            if match:
                varname = match.group("varname")
                if varname not in vars:
                    raise RuntimeError(
                        f"Can't handle {l.strip()} in {scriptfile} - {varname} not defined"
                    )
                programs.add(vars[varname])
    return list(programs)


def cleanPanel(panel: str) -> str:
    """
    Reset all input panel variables that will be overwritten by the BPE when the
    PCF is run.  This avoids unnecessary and confusing updates where a script has
    been run locally and changes the values.
    """
    with io.StringIO(panel) as pin, io.StringIO() as pout:
        while True:
            l = pin.readline()
            if not l:
                break
            if l.startswith("# BEGIN_PANEL "):
                pout.write(l)
                pout.write(pin.read())
                break
            match = re.match(
                r"^(?P<var>\w+)\s+(?P<count>\d+)\s*(?:(?P<value>\S.*?)\s*)?$", l
            )
            if not match:
                pout.write(l)
                continue
            varname = match.group("var")
            varcount = int(match.group("count"))
            value = match.group("value") or ""
            cleanline = f"{varname} 0\n"
            # Remove values referenced to a specific campaign - they must be artefacts
            if re.search(r"\{P\}\/\w+\/", value):
                l = cleanline
            vardef = []
            while not re.match(r"^\s*$", l):
                vardef.append(l)
                l = pin.readline()
                if not l:
                    break
            # If the variable definition has a default value
            # (last line of definition is ' # ....', then clear
            # the defined value as that will be overwritten by BPE)
            if re.match(r"^\s+\#\s+\S", vardef[-1]):
                vardef[0] = cleanline
                if varcount > 1:
                    del vardef[1 : 1 + varcount]
            for vl in vardef:
                pout.write(vl)
            pout.write(l)
        panel = pout.getvalue()
    return panel


def cleanPanelFile(filename: str):
    """
    Overwrite a panel file with a cleaned version
    """
    panel = open(filename).read()
    panel = cleanPanel(panel)
    open(filename, "w").write(panel)


def cleanAllPanels(strusrdir: str):
    optdir = f"{strusrdir}/OPT"
    for optname in os.listdir(optdir):
        optsubdir = f"{optdir}/{optname}"
        if not os.path.isdir(optsubdir):
            continue
        for inpname in os.listdir(optsubdir):
            if not inpname.endswith(".INP"):
                continue
            inpfile = f"{optsubdir}/{inpname}"
            if not os.path.isfile(inpfile):
                continue
            logging.debug(f"Cleaning panel {optname}/{inpname}")
            cleanPanelFile(inpfile)


def copyPcfFiles(srcdir: str, filelist: list, tgtdir: str, ignoreMissing: bool = False):
    for filename in filelist:
        srcfile = os.path.join(srcdir, filename)
        if os.path.exists(srcfile):
            content = open(srcfile).read()
        elif os.path.basename(filename) == placeholder:
            content = ""
        elif ignoreMissing:
            continue
        else:
            raise RuntimeError(f"Cannot find input file {srcfile}")
        if srcfile.endswith(".INP"):
            content = cleanPanel(content)

        tgtfile = os.path.join(tgtdir, filename)
        tgtfiledir = os.path.dirname(tgtfile)
        os.makedirs(tgtfiledir, exist_ok=True)
        open(tgtfile, "w").write(content)


if __name__ == "__main__":
    main()
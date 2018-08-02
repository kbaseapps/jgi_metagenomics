from BBTools.BBToolsClient import BBTools
from DataFileUtil.DataFileUtilClient import DataFileUtil
from jgi_mg_assembly.utils.util import mkdir
import os
from time import time


class RQCFilterRunner(object):
    """
    Acts as a runner for RQCFilter.
    This has two functions.
    run: does the job of invoking BBTools to run RQCFilter. This calls out to the
         KBase BBTools module and runs the app there, returning the results (see
         the run docstring for details).
    run_skip: does a "fake" run of RQCFilter. This returns the same result structure
              but does not run RQCFilter. Instead, it just compresses the given
              reads file (as the results of RQCFilter are done) and creates an
              empty log file.
              This way if the user (or a testing developer) wants to skip that step,
              the rest of the pipeline doesn't fork.
    """

    def __init__(self, callback_url, scratch_dir, options):
        self.callback_url = callback_url
        self.scratch_dir = scratch_dir
        self.skip = options.get("skip_rqcfilter")
        self.debug = options.get("debug")

    def run(self, reads_file):
        """
        Runs RQCFilter.
        This just calls out to BBTools.run_RQCFilter_local and returns the result.
        reads_file: string, the path to the FASTQ file to be filtered.
        result = dictionary with three keys -
            output_directory = path to the output directory
            filtered_fastq_file = as it says, gzipped
            run_log = path to the stderr log from RQCFilter
        """
        if (self.skip):
            return self.run_skip(reads_file)

        print("Running RQCFilter remotely using the KBase-wrapped BBTools module...")
        bbtools = BBTools(self.callback_url, service_ver='beta')
        result = bbtools.run_RQCFilter_local({
            "reads_file": reads_file
        }, {
            "rna": 0,
            "trimfragadapter": 1,
            "qtrim": "r",
            "trimq": 0,
            "maxns": 3,
            "minavgquality": 3,
            "minlength": 51,
            "mlf": 0.333,
            "phix": 1,
            "removehuman": 1,
            "removedog": 1,
            "removecat": 1,
            "removemouse": 1,
            "khist": 1,
            "removemicrobes": 1,
            "clumpify": 1
        })
        print("Done running RQCFilter")
        return result

    def run_skip(self, reads_file):
        """
        Doesn't run RQCFilter, but a dummy skip version. It returns the same
        result structure, so it doesn't derail the other pipeline steps. However, the
        "filtered_fastq_file" is the unchanged fastq file, other than gzipping it.
        run_log is just an empty (but existing!) file.
        """
        print("NOT running RQCFilter, just dummying up some results.")
        # make the dummy output dir
        outdir = os.path.join(self.scratch_dir, "dummy_rqcfilter_output_{}".format(int(time() * 1000)))
        mkdir(outdir)
        # mock up a log file
        dummy_log = os.path.join(outdir, "dummy_rqcfilter_log.txt")
        open(dummy_log, 'w').close()
        # just compress the reads and move them into that output dir (probably don't need to
        # move them, but let's be consistent)
        dfu = DataFileUtil(self.callback_url)
        compressed_reads = dfu.pack_file({
            "file_path": reads_file,
            "pack": "gzip"
        })["file_path"]
        base_name = os.path.basename(compressed_reads)
        not_filtered_reads = os.path.join(outdir, base_name)
        os.rename(compressed_reads, not_filtered_reads)
        return {
            "output_directory": outdir,
            "filtered_fastq_file": not_filtered_reads,
            "run_log": dummy_log
        }
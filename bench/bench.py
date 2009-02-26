import os
import sys
import subprocess

def main():
    assert len(sys.argv) > 1, "bench name required"
    bench = sys.argv[1]

    for url, fname in (("http://localhost:8085/ubuntu/breezy-autotest/+queue",
                        "breezy-autotest-queue.txt"),
                       ("http://localhost:8085/~sabdfl/+related-software",
                        "sabdfl-related-software.txt"),
#                        ("http://localhost:8085/~cprov/+archive",
#                         "cprov-archive.txt"),
                       ("http://localhost:8085/bugs/bugtrackers",
                        "bugs-bugtrackers.txt"),
                       ("http://localhost:8085/ubuntu/+cve",
                        "ubuntu-cve.txt"),
                       ("http://localhost:8085/ubuntu/+upstreamreport",
                        "ubuntu-upstreamreport.txt")):

        # Warm up cache
        print "Warming up", url
        curl = subprocess.Popen(["curl", url], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        curl.wait()
        print "\n".join(curl.stdout.read().splitlines()[-3:])

        # Benchmark, and write out output
        print "Benchmarking", url
        ab = subprocess.Popen(["ab", "-n", "100", "-c", "10", url],
                              stdout=subprocess.PIPE)
        ab.wait()
        out = open(os.path.abspath(os.path.join(bench, fname)), "w")
        out.write(ab.stdout.read())
        out.close()

if __name__ == "__main__":
    main()

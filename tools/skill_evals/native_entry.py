"""Run unmodified upstream hill climbing with strict per-trial error recording."""
from strict_runtime import install
install()
from scripts.run_loop import main
if __name__=='__main__':main()

## <a name="main_help"></a> python3 -m gcclangrawparser.main --help
```
usage: python3 -m gcclangrawparser.main [-h] [-la] --rawfile RAWFILE
                                        [--reducepaths REDUCEPATHS]
                                        [--entrygraph [ENTRYGRAPH]]
                                        [--usevizjs [USEVIZJS]]
                                        [--includeinternals [INCLUDEINTERNALS]]
                                        [-j JOBS]
                                        [--outtypefields OUTTYPEFIELDS]
                                        [--outtreetxt OUTTREETXT]
                                        [--outbiggraph OUTBIGGRAPH]
                                        [--outhtmldir OUTHTMLDIR]

parse gcc/g++ raw internal tree data

options:
  -h, --help            show this help message and exit
  -la, --logall         Log all messages (default: False)
  --rawfile RAWFILE     Path to raw file to analyze (default: )
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths (default: )
  --entrygraph [ENTRYGRAPH]
                        Should generate graph for each entry? (default: True)
  --usevizjs [USEVIZJS]
                        Use viz.js standalone for graph rendering. (default:
                        True)
  --includeinternals [INCLUDEINTERNALS]
                        Should include C++ internals? (default: False)
  -j JOBS, --jobs JOBS  Number to subprocesses to execute. Auto means to spawn
                        job per CPU core. (default: auto)
  --outtypefields OUTTYPEFIELDS
                        Output path to types and fields (default: )
  --outtreetxt OUTTREETXT
                        Output path to tree print (default: )
  --outbiggraph OUTBIGGRAPH
                        Output path to big graph (default: )
  --outhtmldir OUTHTMLDIR
                        Output directory for HTML representation (default: )
```

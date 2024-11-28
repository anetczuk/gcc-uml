## <a name="main_help"></a> python3 -m gcclangrawparser.main --help
```
usage: python3 -m gcclangrawparser.main [-h] [-la] [--listtools]
                                        {tools,printhtml,inheritgraph} ...

parse gcc/g++ raw internal tree data

options:
  -h, --help            show this help message and exit
  -la, --logall         Log all messages (default: False)
  --listtools           List tools (default: False)

subcommands:
  use one of tools

  {tools,printhtml,inheritgraph}
                        one of tools
    tools               various tools
    printhtml           generate static HTML for lang file
    inheritgraph        generate inheritance graph
```



## <a name="tools_help"></a> python3 -m gcclangrawparser.main tools --help
```
usage: python3 -m gcclangrawparser.main tools [-h] --rawfile RAWFILE
                                              [--reducepaths REDUCEPATHS]
                                              [-ii [INCLUDEINTERNALS]]
                                              [--outtypefields OUTTYPEFIELDS]
                                              [--outtreetxt OUTTREETXT]
                                              [--outbiggraph OUTBIGGRAPH]

various tools

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to raw file to analyze (default: )
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths (default: )
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include C++ internals? (default: False)
  --outtypefields OUTTYPEFIELDS
                        Output path to types and fields (default: )
  --outtreetxt OUTTREETXT
                        Output path to tree print (default: )
  --outbiggraph OUTBIGGRAPH
                        Output path to big graph (default: )
```



## <a name="printhtml_help"></a> python3 -m gcclangrawparser.main printhtml --help
```
usage: python3 -m gcclangrawparser.main printhtml [-h] --rawfile RAWFILE
                                                  [-j JOBS]
                                                  [--reducepaths REDUCEPATHS]
                                                  [--genentrygraphs [GENENTRYGRAPHS]]
                                                  [--usevizjs [USEVIZJS]]
                                                  [-ii [INCLUDEINTERNALS]]
                                                  --outhtmldir OUTHTMLDIR

generate static HTML for lang file

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to raw file to analyze (default: )
  -j JOBS, --jobs JOBS  Number to subprocesses to execute. Auto means to spawn
                        job per CPU core. (default: auto)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths (default: )
  --genentrygraphs [GENENTRYGRAPHS]
                        Should generate graph for each entry? (default: True)
  --usevizjs [USEVIZJS]
                        Use viz.js standalone for graph rendering. (default:
                        True)
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include C++ internals? (default: False)
  --outhtmldir OUTHTMLDIR
                        Output directory for HTML representation (default: )
```



## <a name="inheritgraph_help"></a> python3 -m gcclangrawparser.main inheritgraph --help
```
usage: python3 -m gcclangrawparser.main inheritgraph [-h] --rawfile RAWFILE
                                                     [--reducepaths REDUCEPATHS]
                                                     --outpath OUTPATH

generate inheritance graph

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to raw file to analyze (default: )
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths (default: )
  --outpath OUTPATH     Output directory for HTML representation (default: )
```

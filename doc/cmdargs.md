## <a name="main_help"></a> python3 -m gccuml.main --help
```
usage: python3 -m gccuml.main [-h] [-la] [--listtools]
                              {printhtml,inheritgraph,memlayout,ctrlflowgraph,tools}
                              ...

generate UML-like diagrams based on gcc/g++ internal tree

options:
  -h, --help            show this help message and exit
  -la, --logall         Log all messages (default: False)
  --listtools           List tools (default: False)

subcommands:
  use one of tools

  {printhtml,inheritgraph,memlayout,ctrlflowgraph,tools}
                        one of tools
    printhtml           generate static HTML for internal tree file
    inheritgraph        generate inheritance graph
    memlayout           generate memory layout diagram
    ctrlflowgraph       generate control flow diagram
    tools               various tools
```



## <a name="printhtml_help"></a> python3 -m gccuml.main printhtml --help
```
usage: python3 -m gccuml.main printhtml [-h] --rawfile RAWFILE [-j JOBS]
                                        [--progressbar [PROGRESSBAR]]
                                        [--reducepaths REDUCEPATHS]
                                        [--notransform [NOTRANSFORM]]
                                        [--genentrygraphs [GENENTRYGRAPHS]]
                                        [--usevizjs [USEVIZJS]]
                                        [-ii [INCLUDEINTERNALS]] --outhtmldir
                                        OUTHTMLDIR

generate static HTML for internal tree file

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to internal tree file (.003l.raw) to analyze
                        (default: None)
  -j JOBS, --jobs JOBS  Number to subprocesses to execute. Auto means to spawn
                        job per CPU core. (default: auto)
  --progressbar [PROGRESSBAR]
                        Show progress bar (default: True)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths inside tree (default:
                        None)
  --notransform [NOTRANSFORM]
                        Should prevent transforming internal tree before
                        printing? (default: False)
  --genentrygraphs [GENENTRYGRAPHS]
                        Should graph be generated for each entry? (default:
                        True)
  --usevizjs [USEVIZJS]
                        Use viz.js standalone for graph rendering. (default:
                        True)
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include compiler internals? (default: False)
  --outhtmldir OUTHTMLDIR
                        Output directory of HTML representation (default:
                        None)
```



## <a name="inheritgraph_help"></a> python3 -m gccuml.main inheritgraph --help
```
usage: python3 -m gccuml.main inheritgraph [-h] --rawfile RAWFILE
                                           [--reducepaths REDUCEPATHS]
                                           --outpath OUTPATH

generate inheritance graph

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to internal tree file (.003l.raw) to analyze
                        (default: None)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths inside tree (default:
                        None)
  --outpath OUTPATH     Output path of PlantUML representation (default: None)
```



## <a name="memlayout_help"></a> python3 -m gccuml.main memlayout --help
```
usage: python3 -m gccuml.main memlayout [-h] --rawfile RAWFILE
                                        [-ii [INCLUDEINTERNALS]]
                                        [--reducepaths REDUCEPATHS]
                                        [--graphnote GRAPHNOTE] --outpath
                                        OUTPATH

generate memory layout diagram

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to raw file to analyze (default: None)
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include compiler internals? (default: False)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths inside tree (default:
                        None)
  --graphnote GRAPHNOTE
                        Note to put on graph (default: None)
  --outpath OUTPATH     Output path of DOT representation (default: None)
```



## <a name="ctrlflowgraph_help"></a> python3 -m gccuml.main ctrlflowgraph --help
```
usage: python3 -m gccuml.main ctrlflowgraph [-h] --rawfile RAWFILE
                                            [-ii [INCLUDEINTERNALS]]
                                            [--reducepaths REDUCEPATHS]
                                            --outpath OUTPATH

generate control flow diagram

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to internal tree file (.003l.raw) to analyze
                        (default: None)
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include compiler internals? (default: False)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths inside tree (default:
                        None)
  --outpath OUTPATH     Output path for DOT representation (default: None)
```



## <a name="tools_help"></a> python3 -m gccuml.main tools --help
```
usage: python3 -m gccuml.main tools [-h] --rawfile RAWFILE
                                    [--reducepaths REDUCEPATHS]
                                    [-ii [INCLUDEINTERNALS]]
                                    [--outtypefields OUTTYPEFIELDS]
                                    [--outtreetxt OUTTREETXT]
                                    [--outbiggraph OUTBIGGRAPH]

various tools

options:
  -h, --help            show this help message and exit
  --rawfile RAWFILE     Path to internal tree file (.003l.raw)e to analyze
                        (default: None)
  --reducepaths REDUCEPATHS
                        Prefix to remove from paths inside tree (default:
                        None)
  -ii [INCLUDEINTERNALS], --includeinternals [INCLUDEINTERNALS]
                        Should include compiler internals? (default: False)
  --outtypefields OUTTYPEFIELDS
                        Output path to types and fields (default: None)
  --outtreetxt OUTTREETXT
                        Output path to tree print (default: None)
  --outbiggraph OUTBIGGRAPH
                        Output path to big graph (default: None)
```

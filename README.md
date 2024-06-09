# MicroRacer 
This repository contains the source code for MicroRacer.

## Project Structure
```
.
├── auto-trace-query            # Scripts for automatic export of system traces
├── data                        # Directory for raw data files
├── output                      # Directory for output results
├── train-ticket-workload       # TrainTicket workload
├── utils                       # Utility methods
├── ./reqflow_analyze.py        # Generation of conflicting request pairs
├── ./reqflow_construct.py      # Request flow construction
├── ./interleaving_testing.py   # Interleaving testing
├── ./main.py                   # Main program
├── ./object.py                 # Class definitions for request flow construction
├── ./trace_preprocess.py       # Preprocessing of trace data
└── ./requirements.txt
```

## Reproduction Steps

This repository provides the trace files collected from TrainTicket (in five versions of fault reproduction) generated by the APM tool SkyWalking. You can follow the steps to construct request flows, generate potential conflict request pairs, and perform early validation and automatic interleaving testing.

1. Set up the environment: `pip install -r requirements.txt`

2. Construct request flows and generate potential conflicting request pairs:
    - Set the `trace_dir` and `output_dir` paths in the `./main.py` file (located at the bottom of the file) to the paths of the raw Trace files and the output results, respectively.
    - Run `python main.py` to construct request flows and generate potential conflicting request pairs.
    - You can find the JSON files starting with `candidatePairs_` in the output directory, which will be used for subsequent automatic interleaving testing (case 4 does not have this file because the pruning result is such that the problematic request pairs are reported in early validation).
    - Optional: Print debug logs if the environment variable DEBUG=1.

3. Deploy TrainTicket (see Train-Ticket-Benchmark/README.md)

4. Perform automatic interleaving testing:
    - Edit `db_helper.py` to set up your database connection details:

        ```python
        DB_HOST = 'localhost'
        DB_USER = 'root'
        DB_PASS = 'root'
        DB_NAME = 'your_database_name'
        ```

    - Configure the paths and other variables in `interleaving_testing.py`:

        ```python
        json_file_path = "candidatePairs文件路径"
        backup_dir = "path_to_backup_directory"
        restore_dir = "path_to_restore_directory"
        ```

       The testing results, including logs and any detected inconsistencies, will be saved in the specified `backup_dir` and `response_log_path`.

    - **Backup Database**: Run `db_helper.py` to create a backup of your current database state.

        ```bash
        python db_helper.py
        ```

    - **Interleaving Testing**: Execute `interleaving_testing.py` to run tests on the specified request pairs.

        ```bash
        python interleaving_testing.py
        ```
        The system will read from a JSON file containing the pairs of requests to be tested. It will send requests to the specified services, perform database backups and restorations in between, and log the responses and service logs for comparison.

5. Output
    - The testing results, including logs and any detected inconsistencies, will be saved in the specified `backup_dir` and `response_log_path`.
